"""Owner-only store commands. AI responses cannot invoke these operations."""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import html
import json
import re
import secrets
import time

from telegram import InlineKeyboardButton as Button, InlineKeyboardMarkup as Keyboard
from .shopify_api import ShopifyClient, ShopifyError
from .shopify_config import SHOP_DOMAIN
from .ui import choose

from .shopify_commands import SHOP_COMMANDS, SHOP_NAMES

ADMIN = f"https://{SHOP_DOMAIN}/admin"
KITS = {
    "basic": ("JUST AI Sales Kit BASIC", "15428288446740", "digital-product"),
    "pro": ("JUST AI Sales Kit PRO", "15431893352724", "just-ai-sales-kit-pro"),
    "sprint": ("JUST AI 7-Day Content Sprint", "15432147599636", "just-ai-7-day-content-sprint-kit-english-arabic"),
}
ERRORS = {
    "not_configured": ("Shopify is not connected on this host. Run configure_shopify.py locally; never send tokens in Telegram.", "Shopify غير متصل على هذا الجهاز. شغّل configure_shopify.py محليًا ولا ترسل المفاتيح عبر Telegram."),
    "wrong_shop": ("Store identity mismatch. No store action was authorized.", "هوية المتجر غير مطابقة. لم يُسمح بأي إجراء."),
    "authentication": ("Shopify authentication failed. Check the local app credentials.", "تعذر تسجيل الدخول إلى Shopify. راجع بيانات التطبيق على الجهاز."),
    "access_denied": ("Shopify denied access. Check the app installation and scopes locally.", "رفض Shopify الوصول. راجع تثبيت التطبيق وصلاحياته."),
    "missing_scope": ("This app lacks the required product/order permission. Update its Shopify scopes.", "صلاحيات التطبيق لا تكفي لهذا الإجراء. حدّث صلاحياته في Shopify."),
    "unavailable": ("Shopify is temporarily unavailable. No change was submitted.", "Shopify غير متاح حاليًا. لم يُرسل أي تعديل."),
    "query_failed": ("Could not read Shopify data. Check app permissions and API version.", "تعذرت قراءة البيانات. راجع صلاحيات التطبيق وإصدار API."),
    "rejected": ("Shopify rejected the change. Check the record in Admin before preparing a new command.", "رفض Shopify التعديل. راجع السجل في الإدارة قبل طلب تعديل جديد."),
    "outcome_unknown": ("The result is uncertain. Do not repeat the change. Check Shopify Admin, then review /shoplog and /shopack. Further changes to this record are blocked until reviewed.", "نتيجة العملية غير محسومة. لا تكررها. راجع إدارة Shopify ثم /shoplog و/shopack. حُظرت التعديلات على هذا السجل لحين المراجعة."),
}


def entity_id(text, kind):
    if re.fullmatch(r"[1-9][0-9]{0,19}", text):
        return f"gid://shopify/{kind}/{text}"
    if re.fullmatch(r"gid://shopify/" + re.escape(kind) + r"/[1-9][0-9]{0,19}", text):
        return text
    raise ValueError("Use the numeric Shopify ID or its complete gid. /order also accepts #1001.")


def short_id(value):
    return value.rsplit("/", 1)[-1]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def money(value):
    amount = value["shopMoney"]
    return f"{amount['amount']} {amount['currencyCode']}"


def plain(value, limit=200):
    # API text is displayed as text, never parsed as Telegram markup or commands.
    return str(value or "—")[:limit]


@dataclass
class Pending:
    owner: int
    chat: int
    expires: float
    action: str
    resource: str
    kind: str
    before: str
    variables: dict
    expected: dict


class ShopifyControls:
    def __init__(self, settings, store, send, client=None, clock=time.monotonic):
        self.settings, self.store, self.send = settings, store, send
        self.client = client or ShopifyClient(settings)
        self.clock = clock
        self.pending, self.pages = {}, {}

    async def close(self):
        self.pending.clear()
        self.pages.clear()
        await self.client.close()

    async def authorize(self, update, ar):
        user, chat = update.effective_user, update.effective_chat
        if not user or not chat or chat.type != "private":
            return False
        if not self.settings.enabled:
            await self.send(update, choose(ar, *ERRORS["not_configured"]))
            return False
        if user.id not in self.settings.owners:
            await self.send(update, choose(ar, "Store controls are restricted to the owner.", "التحكم بالمتجر متاح للمالك فقط."))
            return False
        self.pending = {k: v for k, v in self.pending.items() if v.expires > self.clock()}
        self.pages = {k: v for k, v in self.pages.items() if v[0] > self.clock()}
        return True

    async def command(self, update, name, text, ar):
        if not await self.authorize(update, ar):
            return
        try:
            await self._command(update, name, text, ar)
        except ShopifyError as exc:
            await self.send(update, choose(ar, *ERRORS.get(exc.code, ERRORS["query_failed"])))
        except ValueError as exc:
            # Only locally authored validation messages reach here.
            await self.send(update, choose(ar, "Check command format: ", "راجع صيغة الأمر: ") + str(exc))

    async def _command(self, update, name, text, ar):
        tr = lambda en, arabic: choose(ar, en, arabic)
        if name == "shop":
            identity = await self.client.identity(force=True)
            await self.send(update, f"JUST AI · {SHOP_DOMAIN}\n{identity['currencyCode']}\n\n" + tr(
                "Orders, products and payment records — controlled by your Telegram owner account.\nEach change requires a confirmation valid for 2 minutes.\n\n/products\n/orders unpaid\n/order #1001\n/product basic\n/price VARIANT_ID 29.00\n/product_title basic New title\n/product_status basic draft\n/order_note #1001 Note\n/mark_paid #1001\n/shoplog\n\nUse /shopadmin for refunds, cancellations, delivery, media uploads, payment settings and themes.",
                "إدارة الطلبات والمنتجات وسجلات الدفع من حساب المالك.\nكل تعديل يحتاج تأكيدًا خلال دقيقتين.\n\n/products\n/orders unpaid\n/order #1001\n/product basic\n/price VARIANT_ID 29.00\n/product_title basic اسم جديد\n/product_status basic draft\n/order_note #1001 ملاحظة\n/mark_paid #1001\n/shoplog\n\nاستخدم /shopadmin للاسترداد والإلغاء والتسليم ورفع الوسائط وإعدادات الدفع والقالب."), self.menu(ar))
        elif name == "shopadmin":
            await self.send(update, tr("Open the requested section in Shopify:", "افتح القسم المطلوب في Shopify:"), Keyboard([
                [Button(tr("Orders", "الطلبات"), url=ADMIN + "/orders"), Button(tr("Products / media", "المنتجات والوسائط"), url=ADMIN + "/products")],
                [Button(tr("Whish / payment settings", "Whish وإعدادات الدفع"), url=ADMIN + "/settings/payments")],
                [Button(tr("Themes", "القوالب"), url=ADMIN + "/themes"), Button(tr("Digital downloads", "التنزيلات الرقمية"), url=ADMIN + "/apps")],
            ]))
        elif name == "kits":
            await self.kits(update, text, ar)
        elif name == "orders":
            if text not in ("", "all", "open", "unpaid", "unfulfilled"):
                raise ValueError("/orders all | open | unpaid | unfulfilled")
            query = {"open": "status:open", "unpaid": "financial_status:pending OR financial_status:partially_paid", "unfulfilled": "fulfillment_status:unfulfilled"}.get(text, "")
            await self.page(update, "orders", query, None, ar)
        elif name == "products":
            if len(text) > 100:
                raise ValueError("/products search (maximum 100 characters)")
            # Quote user input as a literal search phrase; never interpolate GraphQL.
            await self.page(update, "products", json.dumps(text, ensure_ascii=False) if text else "", None, ar)
        elif name == "order":
            await self.show_order(update, await self.get_order(text), ar)
        elif name == "product":
            item = await self.get_entity("product", self.product_id(text))
            lines = [item["title"], f"ID: {short_id(item['id'])} · {item['status']}"]
            shop = await self.client.identity()
            lines += [f"{v['title']} · {v['price']} {shop['currencyCode']}\n/price {short_id(v['id'])} AMOUNT" for v in item["variants"]["nodes"]]
            if item["variants"]["pageInfo"]["hasNextPage"]:
                lines.append(tr("Showing the first 20 variants; see Admin for the rest.", "تظهر أول 20 نسخة. راجع الإدارة للبقية."))
            await self.send(update, "\n\n".join(lines), Keyboard([[Button(tr("Open product", "فتح المنتج"), url=ADMIN + "/products/" + short_id(item["id"]))]]))
        elif name == "shoplog":
            rows = await self.store.shop_history()
            lines = [f"#{r['id']} · {r['created']} UTC · {r['action']}\n{short_id(r['resource'])} · {r['status']}" for r in rows]
            await self.send(update, "\n\n".join(lines) or tr("No store changes recorded.", "لا توجد تعديلات مسجلة."))
        elif name == "shopack":
            if not text.isdigit() or len(text) > 10:
                raise ValueError("/shopack AUDIT_ID (see /shoplog)")
            row = await self.store.shop_entry(int(text))
            if not row or row["status"] not in ("started", "unknown", "verification_failed"):
                raise ValueError("No unresolved entry with this audit ID.")
            await self.preview(update, ar, "_ack", row["resource"], "audit", row, {"audit_id": row["id"]}, {}, tr(
                f"Review audit #{row['id']}: {row['action']} on {short_id(row['resource'])}.\nCheck the actual result in Shopify Admin first. Confirming only unlocks future changes; it does not retry or reverse this operation.",
                f"راجع السجل #{row['id']}: {row['action']} على {short_id(row['resource'])}.\nتحقق أولًا من النتيجة في إدارة Shopify. التأكيد يرفع حظر التعديلات فقط ولا يكرر العملية أو يعكسها."))
        else:
            await self.prepare(update, name, text, ar)

    def menu(self, ar):
        tr = lambda en, arabic: choose(ar, en, arabic)
        return Keyboard([
            [Button(tr("Orders", "الطلبات"), callback_data="shop:orders"), Button(tr("Unpaid", "غير المدفوعة"), callback_data="shop:unpaid")],
            [Button(tr("Products", "المنتجات"), callback_data="shop:products"), Button(tr("Kit previews", "معاينات الحزم"), callback_data="shop:kits")],
            [Button(tr("Change history", "سجل التعديلات"), callback_data="shop:log"), Button(tr("Shopify Admin", "إدارة Shopify"), callback_data="shop:admin")],
        ])

    async def kits(self, update, key, ar):
        if not key:
            await self.send(update, choose(ar, "Choose a kit. Photos contain no prices; product pages include English/Arabic descriptions and videos.", "اختر حزمة. الصور دون أسعار، وصفحات المنتجات تتضمن وصفًا بالعربية والإنجليزية وفيديو."),
                Keyboard([[Button(value[0], callback_data="shop:kit:" + key)] for key, value in KITS.items()]))
            return
        if key not in KITS:
            raise ValueError("/kits basic | pro | sprint")
        title, _, handle = KITS[key]
        sample = "content-sprint" if key == "sprint" else key
        photo = f"https://cdn.shopify.com/s/files/1/1035/9717/9156/files/just-ai-{sample}-product-sample.jpg"
        note = choose(ar, "BASIC video shows actual template excerpts." if key == "basic" else "This video is a product overview; illustrative samples are labelled.",
                      "يعرض فيديو BASIC مقتطفات من القوالب الفعلية." if key == "basic" else "الفيديو نظرة عامة على المنتج، والنماذج التوضيحية موضحة فيه.")
        await update.effective_message.reply_photo(photo=photo, caption=title + "\n" + note,
            reply_markup=Keyboard([[Button(choose(ar, "Description + video", "الوصف والفيديو"), url=f"https://{SHOP_DOMAIN}/products/{handle}")]]))

    def product_id(self, text):
        return entity_id(KITS[text][1] if text in KITS else text, "Product")

    async def get_entity(self, kind, resource):
        data = await self.client.query(kind, {"id": resource})
        item = data.get("node" if kind == "variant" else kind)
        if not isinstance(item, dict) or item.get("id") != resource:
            raise ValueError("Record not found or not accessible to this app.")
        return item

    async def get_order(self, text):
        if re.fullmatch(r"#[1-9][0-9]{0,19}", text):
            data = await self.client.query("orders", {"query": 'name:"' + text + '"', "after": None})
            items = [i for i in data["orders"]["nodes"] if i["name"] == text]
            if len(items) != 1:
                raise ValueError("Order not found or ambiguous. Use its numeric Shopify ID.")
            resource = items[0]["id"]
        else:
            resource = entity_id(text, "Order")
        return await self.get_entity("order", resource)

    async def show_order(self, update, item, ar):
        lines = [f"{item['name']} · ID {short_id(item['id'])}",
            f"{item['displayFinancialStatus']} / {item['displayFulfillmentStatus']}",
            choose(ar, "Total: ", "الإجمالي: ") + money(item["totalPriceSet"]),
            choose(ar, "Outstanding: ", "المتبقي: ") + money(item["totalOutstandingSet"]),
            choose(ar, "Gateway: ", "الدفع: ") + ", ".join(item["paymentGatewayNames"]),
            choose(ar, "Archived: ", "مؤرشف: ") + str(item["closed"]),
            choose(ar, "Note: ", "ملاحظة: ") + plain(item["note"], 1000)]
        lines += [f"{line['quantity']} × {plain(line['name'])}" for line in item["lineItems"]["nodes"]]
        if item["lineItems"]["pageInfo"]["hasNextPage"]:
            lines.append(choose(ar, "First 20 line items shown.", "تظهر أول 20 سلعة."))
        if item["test"]:
            lines.insert(0, "TEST ORDER / طلب تجريبي")
        if item["cancelledAt"]:
            lines.insert(0, "CANCELLED / ملغى")
        await self.send(update, "\n".join(lines), Keyboard([[Button(choose(ar, "Open order", "فتح الطلب"), url=ADMIN + "/orders/" + short_id(item["id"]))]]))

    async def page(self, update, kind, query, after, ar):
        result = (await self.client.query(kind, {"query": query, "after": after}))[kind]
        lines = []
        for item in result["nodes"]:
            if kind == "orders":
                lines.append(f"{item['name']} · {item['displayFinancialStatus']} · {money(item['totalPriceSet'])}\n/order {short_id(item['id'])}")
            else:
                lines.append(f"{plain(item['title'])} · {item['status']}\n/product {short_id(item['id'])}")
        keyboard = None
        if result["pageInfo"]["hasNextPage"]:
            token = secrets.token_urlsafe(12)
            self.pages[token] = (self.clock() + 600, update.effective_user.id, update.effective_chat.id, kind, query, result["pageInfo"]["endCursor"])
            while len(self.pages) > 128:
                self.pages.pop(next(iter(self.pages)))
            keyboard = Keyboard([[Button(choose(ar, "Next page", "الصفحة التالية"), callback_data="shop:page:" + token)]])
        await self.send(update, "\n\n".join(lines) or choose(ar, "No matching records. The app may have access only to recent orders.", "لا توجد نتائج. قد تكون صلاحيات التطبيق مقتصرة على الطلبات الحديثة."), keyboard)

    async def prepare(self, update, name, text, ar):
        parts = text.split(maxsplit=1)
        reference = parts[0] if parts else ""
        value = parts[1].strip() if len(parts) == 2 else ""
        tr = lambda en, arabic: choose(ar, en, arabic)
        if name == "price":
            if not re.fullmatch(r"(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,2})?", value) or Decimal(value) <= 0:
                raise ValueError("/price VARIANT_ID 29.00 (0.01–999999.99)")
            item = await self.get_entity("variant", entity_id(reference, "ProductVariant"))
            shop = await self.client.identity()
            if shop["currencyCode"] != "USD":
                raise ValueError("Price changes require the store's expected USD currency.")
            amount = format(Decimal(value), ".2f")
            await self.preview(update, ar, "price", item["id"], "variant", item,
                {"productId": item["product"]["id"], "variants": [{"id": item["id"], "price": amount}]}, {"price": amount},
                f"{item['product']['title']} · {item['title']}\n{item['price']} USD → {amount} USD")
        elif name in ("product_title", "product_description", "product_status"):
            field = {"product_title": "title", "product_description": "descriptionHtml", "product_status": "status"}[name]
            if not value or len(value) > (2000 if field == "descriptionHtml" else 255):
                raise ValueError(f"/{name} PRODUCT_ID text (or basic/pro/sprint)")
            if field == "status":
                value = value.upper()
                if value not in ("ACTIVE", "DRAFT", "ARCHIVED"):
                    raise ValueError("/product_status PRODUCT_ID active | draft | archived")
            item = await self.get_entity("product", self.product_id(reference))
            new_value = "<p>" + html.escape(value).replace("\n", "<br>") + "</p>" if field == "descriptionHtml" else value
            preview = f"{item['title']} · {field}\n" + tr("Before: ", "قبل: ") + plain(item[field], 700) + "\n\n" + tr("After: ", "بعد: ") + value
            if field == "descriptionHtml":
                preview += "\n\n" + tr("This replaces the entire description, including any embedded video. Use Admin to preserve rich formatting.", "يستبدل هذا الوصف بالكامل بما فيه الفيديو المضمّن. استخدم الإدارة للحفاظ على التنسيق والوسائط.")
            if field == "status":
                preview += "\n\n" + tr("DRAFT/ARCHIVED removes availability; ACTIVE does not add new sales-channel publications.", "المسودة أو الأرشفة توقف إتاحة المنتج؛ ACTIVE لا يضيف نشرًا جديدًا على قنوات البيع.")
            await self.preview(update, ar, "product_update", item["id"], "product", item, {"product": {"id": item["id"], field: new_value}}, {field: new_value}, preview)
        elif name in ("order_note", "mark_paid", "archive_order", "reopen_order"):
            if name == "order_note" and (not value or len(value) > 2000):
                raise ValueError("/order_note #1001 New note (1–2000 characters)")
            if name != "order_note" and value:
                raise ValueError(f"/{name} #1001")
            item = await self.get_order(reference)
            expected = {}
            payload = {"id": item["id"]}
            preview = f"{item['name']} · {name}\n{money(item['totalPriceSet'])}\n{item['displayFinancialStatus']} / {item['displayFulfillmentStatus']}"
            if name == "mark_paid":
                if item["cancelledAt"] or not item["canMarkAsPaid"] or Decimal(item["totalOutstandingSet"]["shopMoney"]["amount"]) <= 0:
                    raise ValueError("This order is not eligible to be marked paid.")
                if not item["paymentGatewayNames"] or not all("whish" in g.lower() for g in item["paymentGatewayNames"]):
                    raise ValueError("/mark_paid is limited to Whish orders. Use Admin for other payment methods.")
                expected = {"paid": True}
                preview += "\n\n" + tr("Outstanding: ", "المتبقي: ") + money(item["totalOutstandingSet"]) + "\n" + tr(
                    "Confirm only after independently verifying the exact funds received in Whish. A receipt image is not verification. This records payment; it does not collect money. Shopify delivery automations may run after payment is recorded.",
                    "أكد فقط بعد التحقق بنفسك من وصول المبلغ الصحيح في Whish. صورة الإيصال ليست تحققًا. يسجل هذا الدفع ولا يحوّل أموالًا. قد تعمل أتمتة التسليم في Shopify بعد تسجيل الدفع.")
            elif name == "order_note":
                payload["note"], expected = value, {"note": value}
                preview += "\n\n" + tr("Before: ", "قبل: ") + plain(item["note"], 700) + "\n" + tr("After: ", "بعد: ") + value
            else:
                closed = name == "archive_order"
                if item["closed"] == closed or (not closed and item["cancelledAt"]):
                    raise ValueError("Order already has this state, or is cancelled.")
                expected = {"closed": closed}
                preview += "\n" + tr("Changes archive state only; it does not cancel, refund or fulfill.", "يغير الأرشفة فقط ولا يلغي الطلب أو يرد الأموال أو يسلّم المنتج.")
            await self.preview(update, ar, name, item["id"], "order", item, {"input": payload}, expected, preview)
        else:
            raise ValueError("Use /shop for supported commands.")

    async def preview(self, update, ar, action, resource, kind, before, variables, expected, text):
        if action != "_ack" and await self.store.shop_unresolved(resource):
            raise ShopifyError("outcome_unknown")
        uid, chat = update.effective_user.id, update.effective_chat.id
        self.pending = {k: v for k, v in self.pending.items() if v.owner != uid}
        token = secrets.token_urlsafe(16)
        self.pending[token] = Pending(uid, chat, self.clock() + 120, action, resource, kind, fingerprint(before), variables, expected)
        try:
            await self.send(update, choose(ar, "REVIEW CHANGE\n", "راجع التعديل\n") + text + "\n\n" + choose(ar, "Confirm within 2 minutes. A newer preview replaces this one.", "أكد خلال دقيقتين. أي معاينة جديدة تلغي هذه المعاينة."), Keyboard([[
                Button(choose(ar, "Confirm", "تأكيد"), callback_data="shop:yes:" + token),
                Button(choose(ar, "Cancel", "إلغاء"), callback_data="shop:no:" + token),
            ]]))
        except Exception:
            self.pending.pop(token, None)
            raise

    async def callback(self, update, data, ar):
        if not await self.authorize(update, ar):
            return
        try:
            if data.startswith(("shop:yes:", "shop:no:")):
                token = data.split(":", 2)[2]
                pending = self.pending.get(token)
                if not pending or (pending.owner, pending.chat) != (update.effective_user.id, update.effective_chat.id):
                    await self.send(update, choose(ar, "This confirmation expired or belongs to another account. Prepare a fresh command.", "انتهت صلاحية التأكيد أو يخص حسابًا آخر. أرسل أمرًا جديدًا."))
                    return
                # Consume before any I/O: duplicate callbacks cannot submit twice.
                self.pending.pop(token)
                if data.startswith("shop:no:"):
                    await self.send(update, choose(ar, "Cancelled. No change submitted.", "أُلغي التأكيد. لم يُرسل تعديل."))
                    return
                await self.confirm(update, pending, ar)
            elif data.startswith("shop:page:"):
                item = self.pages.get(data.split(":", 2)[2])
                if item and item[1:3] == (update.effective_user.id, update.effective_chat.id):
                    await self.page(update, *item[3:], ar)
                else:
                    await self.send(update, choose(ar, "Page expired. Use /orders or /products again.", "انتهت صلاحية الصفحة. استخدم /orders أو /products."))
            elif data.startswith("shop:kit:"):
                await self.kits(update, data.split(":", 2)[2], ar)
            else:
                route = {"menu:shop": ("shop", ""), "shop:orders": ("orders", ""), "shop:unpaid": ("orders", "unpaid"), "shop:products": ("products", ""), "shop:kits": ("kits", ""), "shop:log": ("shoplog", ""), "shop:admin": ("shopadmin", "")}.get(data)
                if route:
                    await self._command(update, *route, ar)
        except ShopifyError as exc:
            await self.send(update, choose(ar, *ERRORS.get(exc.code, ERRORS["query_failed"])))
        except ValueError as exc:
            await self.send(update, str(exc))

    async def confirm(self, update, pending, ar):
        if pending.action == "_ack":
            row = await self.store.shop_entry(pending.variables["audit_id"])
            if not row or fingerprint(row) != pending.before:
                raise ValueError("Audit entry changed. Prepare /shopack again.")
            await self.store.shop_finish(row["id"], "reviewed")
            await self.send(update, choose(ar, "Review recorded. The Shopify operation was not repeated.", "سُجلت المراجعة. لم تُكرر عملية Shopify."))
            return
        if await self.store.shop_unresolved(pending.resource):
            raise ShopifyError("outcome_unknown")
        current = await self.get_entity(pending.kind, pending.resource)
        if fingerprint(current) != pending.before:
            await self.send(update, choose(ar, "The record changed after the preview. No change submitted; prepare a fresh command.", "تغير السجل بعد المعاينة. لم يُرسل تعديل؛ أعد الأمر للمراجعة."))
            return
        # Durable intent prevents silent retries after a crash or ambiguous response.
        audit_id = await self.store.shop_start(pending.owner, pending.action, pending.resource)
        try:
            await self.client.mutate(pending.action, pending.variables)
        except ShopifyError as exc:
            await self.store.shop_finish(audit_id, "unknown" if exc.code == "outcome_unknown" else "rejected")
            raise
        except Exception:
            await self.store.shop_finish(audit_id, "unknown")
            raise ShopifyError("outcome_unknown") from None
        try:
            result = await self.get_entity(pending.kind, pending.resource)
            for field, value in pending.expected.items():
                if field == "paid":
                    matches = not result["canMarkAsPaid"] and Decimal(result["totalOutstandingSet"]["shopMoney"]["amount"]) == 0
                elif field == "price":
                    matches = Decimal(result["price"]) == Decimal(value)
                else:
                    matches = result.get(field) == value
                if not matches:
                    raise ShopifyError("outcome_unknown")
        except Exception:
            await self.store.shop_finish(audit_id, "verification_failed")
            raise ShopifyError("outcome_unknown") from None
        await self.store.shop_finish(audit_id, "verified")
        await self.send(update, choose(ar, f"Saved and verified in Shopify. Audit #{audit_id} · /shoplog", f"حُفظ التعديل وتحققت قراءته من Shopify. السجل #{audit_id} · /shoplog"))
