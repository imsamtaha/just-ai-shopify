from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .catalog import COMMANDS, SKILLS, SKINS


def is_ar(prefs, update):
    return prefs["language"] == "ar" or (prefs["language"] == "auto" and
        (getattr(update.effective_user, "language_code", "") or "").startswith("ar"))


def choose(ar, en, arabic):
    return arabic if ar else en


def menu(ar):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(choose(ar, "Shop control", "إدارة المتجر"), callback_data="menu:shop")],
        [InlineKeyboardButton("ATLAS Intelligence", callback_data="menu:atlas"),
         InlineKeyboardButton(choose(ar, "Training", "التدريب"), callback_data="menu:training")],
        [InlineKeyboardButton(choose(ar, "Sessions", "الجلسات"), callback_data="menu:sessions"),
         InlineKeyboardButton(choose(ar, "Strategies", "الاستراتيجيات"), callback_data="menu:strategies")],
        [InlineKeyboardButton(choose(ar, "Skills", "المهارات"), callback_data="menu:skills"),
         InlineKeyboardButton(choose(ar, "Style", "الأسلوب"), callback_data="menu:skin")],
        [InlineKeyboardButton(choose(ar, "Notes", "ملاحظات"), callback_data="menu:notes"),
         InlineKeyboardButton(choose(ar, "Tasks", "مهام"), callback_data="menu:tasks")],
        [InlineKeyboardButton(choose(ar, "Language", "اللغة"), callback_data="menu:language"),
         InlineKeyboardButton(choose(ar, "Status", "الحالة"), callback_data="menu:status")],
        [InlineKeyboardButton(choose(ar, "Help", "المساعدة"), callback_data="menu:help")],
    ])


def options(field, ar):
    if field == "mode":
        entries = [(name, value[1 if ar else 0]) for name, value in SKILLS.items()]
    elif field == "skin":
        entries = [(name, name) for name in SKINS]
    else:
        entries = [("auto", "Auto / تلقائي"), ("en", "English"), ("ar", "العربية")]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"set:{field}:{name}")] for name, label in entries
    ])


def help_text(ar):
    lines = ["JUST AI — " + choose(ar, "Command guide", "دليل الأوامر")]
    lines += [f"/{cmd} — {arabic if ar else en}" for cmd, en, arabic in COMMANDS]
    lines += ["", choose(ar, "Examples:", "أمثلة:"),
              "/mode coding", "/skin minimal", "/language ar",
              "/prompt " + choose(ar, "Plan a product launch", "خطة إطلاق منتج"),
              "/note " + choose(ar, "Customer prefers Arabic", "العميل يفضل العربية"),
              "/task " + choose(ar, "Prepare the proposal", "جهز العرض"), "/done 1",
              "/notes 2", "/tasks 2", "/note_delete 1"]
    return "\n".join(lines)


def chunks(text, limit=3500):
    # Count UTF-16 units, keeping supplementary emoji together.
    buffer, units = [], 0
    for char in text:
        cost = 2 if ord(char) > 0xFFFF else 1
        if units + cost > limit:
            yield "".join(buffer)
            buffer, units = [], 0
        buffer.append(char)
        units += cost
    if buffer:
        yield "".join(buffer)
