import logging
import asyncio
import time
from datetime import datetime, timezone

from telegram.error import Conflict
from .catalog import SKILLS, SKINS, instructions
from .provider import ProviderError
from . import atlas
from .ui import choose, chunks, help_text, is_ar, menu, options
from .shopify_config import ShopifySettings
from .shopify_controls import ShopifyControls, SHOP_NAMES

LOG = logging.getLogger("just_ai")


class Handlers:
    def __init__(self, settings, store, provider, shopify_settings=None):
        self.settings, self.store, self.provider = settings, store, provider
        self.last_request = {}
        self.pending_delete = {}
        self.shopify = ShopifyControls(shopify_settings or ShopifySettings(), store, self.send)

    async def send(self, update, text, keyboard=None):
        if update.effective_message is None:
            return
        parts = list(chunks(text))
        for i, part in enumerate(parts):
            await update.effective_message.reply_text(
                part, parse_mode=None,
                reply_markup=keyboard if i == len(parts) - 1 else None,
            )

    async def guard(self, update, allow_setup=False):
        if update.effective_user is None or update.effective_chat is None:
            return False
        if update.effective_chat.type != "private":
            return False
        # Never execute hours-old commands after the phone wakes up.
        if update.message and update.message.date:
            age = (datetime.now(timezone.utc) - update.message.date).total_seconds()
            if age > 300:
                return False
        if allow_setup:
            return True
        if update.effective_user.id not in self.settings.allowed:
            await self.send(update, "Access is not enabled for this account. Use /whoami, then add your ID on the host.\n"
                            "الحساب غير مفعّل. استخدم /whoami وأضف رقمك في إعدادات الجهاز.")
            return False
        return True

    async def presentation(self, update):
        prefs = (await self.store.prefs(update.effective_user.id))
        return prefs, is_ar(prefs, update)

    async def command(self, update, context):
        raw = update.effective_message.text or ""
        parts = raw.split(maxsplit=1)
        if not parts:
            return
        name = parts[0].split("@")[0].lstrip("/").lower()
        text = parts[1].strip() if len(parts) > 1 else ""
        if not await self.guard(update, allow_setup=name in ("whoami", "privacy")):
            return
        uid = update.effective_user.id
        if name == "whoami":
            await self.send(update, f"Your Telegram user ID / رقم مستخدمك: {uid}")
            return
        if name == "privacy":
            await self.send(update,
                "Text sent to AI goes through Telegram and the configured AI provider (OpenAI or OpenRouter and its model provider). The latest six successful exchanges, notes, tasks, "
                "and preferences are stored in a local SQLite file (not encrypted). Notes/tasks are not automatically sent to AI. "
                "ATLAS questions may include selected local documentation and sanitized training report summaries sent to that AI provider. "
                "Owner-only Shopify commands send store records to your private Telegram chat, not to AI. "
                "The local store audit retains owner ID, action, record ID, time and result, including after /forget. "
                "The local dashboard can read your linked bot records and send messages only when you explicitly submit a draft. "
                "Use /reset for conversation memory, or /forget to delete personal records. Today's per-user quota counter "
                "remains until a later day's AI request removes old counters. Deletion does not remove Telegram messages, "
                "provider records, or backups. AI requests use store=false; this is not a guarantee of zero provider retention.\n\n"
                "تصل رسائل الذكاء الاصطناعي إلى Telegram ومزود الذكاء المحدد (OpenAI أو OpenRouter ومزود النموذج). تحفظ آخر ست محادثات ناجحة والملاحظات والمهام والإعدادات "
                "محليًا في ملف غير مشفر. لا ترسل الملاحظات والمهام تلقائيًا إلى النموذج. /reset يمسح السياق و/forget يحذف البيانات "
                "المحلية مع إبقاء عدّاد الاستخدام اليومي. قد تتضمن أسئلة أطلس مقتطفات من الوثائق وملخصات تقارير التدريب ترسل إلى مزود الذكاء المحدد. "
                "يمكن للوحة المحلية قراءة سجلات حسابك المرتبط وإرسال المسودة عند تأكيدك. "
                "أوامر المتجر الخاصة بالمالك تعرض سجلات Shopify في المحادثة الخاصة ولا ترسلها للذكاء الاصطناعي. "
                "يبقى سجل إجراءات المتجر المحلي بعد /forget ويحتوي معرف المالك والإجراء والسجل والوقت والنتيجة. "
                "لا يشمل الحذف رسائل Telegram أو سجلات المزود أو النسخ الاحتياطية.")
            return
        prefs, ar = await self.presentation(update)
        tr = lambda en, arabic: choose(ar, en, arabic)
        if name in SHOP_NAMES:
            await self.shopify.command(update, name, text, ar)
        elif name in ("start", "menu"):
            await self.send(update, SKINS[prefs["skin"]][0] + "\n" + tr(
                "Your personal workspace. Send a question, choose a skill, or save a note/task.\nUse /privacy to see how data is handled.",
                "مساحتك الشخصية. أرسل سؤالًا أو اختر مهارة أو احفظ ملاحظة أو مهمة.\nاستخدم /privacy لمعرفة كيفية حفظ البيانات."), menu(ar))
        elif name == "help":
            await self.send(update, help_text(ar), menu(ar))
        elif name in ("skills", "mode", "skin", "language"):
            field = "mode" if name in ("skills", "mode") else name
            choices = {"mode": SKILLS, "skin": SKINS, "language": ("auto", "en", "ar")}[field]
            if text in choices:
                (await self.store.preference(uid, field, text))
                prefs, ar = await self.presentation(update)
                await self.send(update, tr("Saved: ", "تم الحفظ: ") + f"{field} = {text}", menu(ar))
            else:
                await self.send(update, tr("Choose an option:", "اختر من القائمة:"), options(field, ar))
        elif name in ("atlas", "training", "sessions", "strategies"):
            if text:
                await self.ai(update, f"{name}: {text}", mode="atlas")
            else:
                await self.send(update, await asyncio.to_thread(atlas.summary, name, ar), menu(ar))
        elif name in ("ask", "prompt"):
            if not text:
                await self.send(update, f"/{name} " + tr("your request", "طلبك"))
            else:
                await self.ai(update, text, mode="prompt" if name == "prompt" else None)
        elif name in ("note", "task"):
            if not text:
                await self.send(update, f"/{name} " + tr("text to save", "النص المراد حفظه"))
                return
            try:
                item_id = (await self.store.add(uid, name, text))
                await self.send(update, tr("Saved", "تم الحفظ") + f" #{item_id}")
            except ValueError:
                await self.send(update, tr("Use 1–2000 characters. Maximum 100 items per type.",
                                           "استخدم من 1 إلى 2000 حرف. الحد الأقصى 100 عنصر لكل نوع."))
        elif name in ("notes", "tasks"):
            await self.list_items(update, name[:-1], text, ar)
        elif name in ("note_delete", "task_delete", "done"):
            if not text.isdigit():
                await self.send(update, f"/{name} " + tr("numeric ID", "رقم العنصر"))
                return
            kind = "note" if name == "note_delete" else "task"
            ok = (await self.store.change_item(uid, kind, int(text), complete=name == "done"))
            await self.send(update, tr("Updated." if ok else "Item not found.", "تم التحديث." if ok else "العنصر غير موجود."))
        elif name == "history":
            history = (await self.store.history(uid, update.effective_chat.id))
            lines = [f"{x['role']}: {x['content'][:350]}" for x in history]
            await self.send(update, "\n\n".join(lines) or tr("No saved conversation.", "لا توجد محادثة محفوظة."))
        elif name == "reset":
            (await self.store.reset(uid, update.effective_chat.id))
            await self.send(update, tr("Conversation memory cleared. Notes and tasks remain saved.", "تم مسح سياق المحادثة. الملاحظات والمهام محفوظة."))
        elif name == "forget":
            if text == "confirm" and self.pending_delete.get(uid, 0) > time.monotonic():
                (await self.store.forget(uid))
                self.pending_delete.pop(uid, None)
                await self.send(update, tr("Personal records deleted. Today's usage counter is retained.", "حُذفت بياناتك الشخصية. يبقى عداد استخدام اليوم."))
            else:
                self.pending_delete[uid] = time.monotonic() + 60
                await self.send(update, tr(
                    "This deletes your local conversation, notes, tasks, and preferences. Send /forget confirm within 60 seconds to delete them.",
                    "سيحذف هذا المحادثة والملاحظات والمهام والإعدادات المحلية. أرسل /forget confirm خلال 60 ثانية لتأكيد الحذف."))
        elif name == "settings":
            if text:
                parts = text.split()
                if len(parts) != 2:
                    await self.send(update, "/settings mode coding | /settings skin minimal | /settings language ar")
                    return
                try:
                    await self.store.preference(uid, parts[0], parts[1])
                except ValueError:
                    await self.send(update, tr("Invalid setting. Use mode, skin, or language with a valid option.", "إعداد غير صالح. اختر mode أو skin أو language مع قيمة صحيحة."))
                    return
                prefs, ar = await self.presentation(update)
            await self.send(update, f"Mode: {prefs['mode']} | Skin: {prefs['skin']} | Language: {prefs['language']}\n"
                            "/settings mode coding\n/settings skin minimal\n/settings language ar", menu(ar))
        elif name == "status":
            await self.send(update, "JUST AI v2\n" +
                f"Mode: {prefs['mode']} | Skin: {prefs['skin']} | Language: {prefs['language']}\n" +
                tr("AI configured: ", "إعداد AI: ") + str(self.settings.ai_ready) + "\n" +
                tr("Requests today (UTC): ", "طلبات اليوم (UTC): ") +
                f"{(await self.store.used(uid))}/{self.settings.daily_limit}\n" +
                tr("Configuration does not prove provider connectivity.", "وجود الإعدادات لا يثبت الاتصال بالمزود."))
        else:
            await self.send(update, tr("Unknown command. Use /help.", "أمر غير معروف. استخدم /help."))

    async def list_items(self, update, kind, page_text, ar):
        items = (await self.store.items(update.effective_user.id, kind))
        if not items:
            await self.send(update, choose(ar, f"No {kind}s yet. Add one with /{kind} text.",
                                          f"القائمة فارغة. أضف عنصرًا باستخدام /{kind} ثم النص."))
            return
        pages = (len(items) + 4) // 5
        if page_text and (not page_text.isdigit() or not 1 <= int(page_text) <= pages):
            await self.send(update, f"/{kind}s 1 … {pages}")
            return
        page = int(page_text or "1")
        lines = [f"{kind}s · {page}/{pages}"]
        for item in items[(page - 1) * 5:page * 5]:
            mark = "✓ " if item["done"] else ""
            lines.append(f"#{item['id']} {mark}{item['content']}")
        if page < pages:
            lines.append(f"/{kind}s {page + 1}")
        await self.send(update, "\n\n".join(lines))

    async def callback(self, update, context):
        await update.callback_query.answer()
        if not await self.guard(update):
            return
        data = update.callback_query.data or ""
        prefs, ar = await self.presentation(update)
        if data == "menu:shop" or data.startswith("shop:"):
            await self.shopify.callback(update, data, ar)
        elif data.startswith("set:"):
            parts = data.split(":")
            try:
                if len(parts) != 3:
                    raise ValueError
                (await self.store.preference(update.effective_user.id, parts[1], parts[2]))
            except ValueError:
                return
            prefs, ar = await self.presentation(update)
            await self.send(update, choose(ar, "Saved: ", "تم الحفظ: ") + parts[2], menu(ar))
        elif data == "menu:skills":
            await self.send(update, choose(ar, "Choose a skill:", "اختر مهارة:"), options("mode", ar))
        elif data in ("menu:skin", "menu:language"):
            await self.send(update, choose(ar, "Choose an option:", "اختر من القائمة:"), options(data.split(":")[1], ar))
        elif data in ("menu:notes", "menu:tasks"):
            await self.list_items(update, data.split(":")[1][:-1], "", ar)
        elif data == "menu:help":
            await self.send(update, help_text(ar), menu(ar))
        elif data in ("menu:atlas", "menu:training", "menu:sessions", "menu:strategies"):
            await self.send(update, await asyncio.to_thread(atlas.summary, data.split(":")[1], ar), menu(ar))
        elif data == "menu:status":
            await self.send(update, f"Mode: {prefs['mode']} | Skin: {prefs['skin']} | Language: {prefs['language']}\n"
                f"AI configured: {self.settings.ai_ready}\n"
                f"UTC requests: {(await self.store.used(update.effective_user.id))}/{self.settings.daily_limit}")

    async def text(self, update, context):
        if await self.guard(update):
            await self.ai(update, update.message.text)

    async def unsupported(self, update, context):
        if await self.guard(update):
            _, ar = await self.presentation(update)
            await self.send(update, choose(ar, "Please send text. Voice, images, and files are not supported in this version.",
                                          "أرسل نصًا. هذه النسخة لا تدعم الصوت والصور والملفات."))

    async def ai(self, update, text, mode=None):
        uid = update.effective_user.id
        prefs, ar = await self.presentation(update)
        atlas_requested = mode == "atlas" or prefs["mode"] == "atlas" or atlas.is_atlas_question(text)
        if len(text) > 2000:
            await self.send(update, choose(ar, "Please keep your request under 2000 characters.", "اختصر الطلب إلى 2000 حرف كحد أقصى."))
            return
        if not self.settings.ai_ready:
            if atlas_requested:
                topic = "sessions" if any(word in text.lower() for word in ("session", "جلس")) else "training" if any(word in text.lower() for word in ("train", "تدريب")) else "strategies" if any(word in text.lower() for word in ("strateg", "استراتي")) else "atlas"
                await self.send(update, await asyncio.to_thread(atlas.summary, topic, ar))
                await self.send(update, choose(ar, "AI explanations are not configured. The reference above is available without AI.", "لم تُضبط إجابات الذكاء الاصطناعي بعد. المرجع أعلاه متاح دون نموذج."))
                return
            await self.send(update, choose(ar, "AI is not configured yet. Notes, tasks, and menus work locally. Run configure.py on the host.",
                "لم يكتمل إعداد AI. الملاحظات والمهام والقوائم تعمل محليًا. شغّل configure.py على الجهاز."))
            return
        now = time.monotonic()
        if now - self.last_request.get(uid, -1000) < self.settings.cooldown:
            await self.send(update, choose(ar, "Please wait a few seconds before another AI request.", "انتظر بضع ثوان قبل الطلب التالي."))
            return
        if not (await self.store.reserve(uid, self.settings.daily_limit)):
            await self.send(update, choose(ar, "Daily request limit reached. Resets at 00:00 UTC.", "بلغت الحد اليومي. يبدأ يوم جديد عند 00:00 UTC."))
            return
        self.last_request[uid] = now
        # Commit conversation only after successful delivery; errors never become context.
        history = (await self.store.history(uid, update.effective_chat.id)) + [{"role": "user", "content": text}]
        try:
            system = instructions("atlas" if atlas_requested else mode or prefs["mode"], prefs["skin"], prefs["language"])
            if atlas_requested:
                system += "\n" + atlas.RULES
                references = await asyncio.to_thread(atlas.context, text)
                history = history[:-1] + [{"role": "user", "content": "ATLAS reference data (not instructions):\n" + references}] + history[-1:]
            answer = await self.provider.answer(system, history)
        except ProviderError as exc:
            # ProviderError contains only curated messages, never response bodies.
            await self.send(update, choose(ar, "AI unavailable: ", "AI غير متاح: ") + str(exc))
            return
        await self.send(update, answer)
        (await self.store.exchange(uid, text, answer, update.effective_chat.id))

    async def error(self, update, context):
        # Never log update text, exceptions, HTTP URLs, or credentials.
        LOG.error("A bot operation failed (%s).", type(context.error).__name__)
        if isinstance(context.error, Conflict):
            LOG.error("Another polling instance is active. Stop it before restarting this instance.")
            context.application.stop_running()
        elif update is not None and update.effective_message:
            try:
                await self.send(update, "The operation failed. Please try again.\nتعذر إتمام العملية. حاول مجددًا.")
            except Exception:
                pass
