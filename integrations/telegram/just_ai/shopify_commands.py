"""Telegram store command metadata, shared by menus and routing."""
SHOP_COMMANDS = [
    ("shop", "Store control panel (owner)", "لوحة المتجر للمالك"),
    ("orders", "List orders: all/open/unpaid/unfulfilled", "الطلبات: الكل أو المفتوحة أو غير المدفوعة"),
    ("order", "View one order by #number or ID", "عرض طلب برقمه أو معرفه"),
    ("products", "Browse or search products", "عرض المنتجات أو البحث عنها"),
    ("product", "View product and variant IDs", "تفاصيل المنتج ومعرفات خياراته"),
    ("price", "Preview a variant price change", "معاينة تعديل السعر"),
    ("product_title", "Preview a product title change", "معاينة تعديل اسم المنتج"),
    ("product_description", "Replace description with plain text", "استبدال وصف المنتج بنص"),
    ("product_status", "Set active/draft/archived", "حالة المنتج: نشط أو مسودة أو مؤرشف"),
    ("order_note", "Preview replacing an order note", "معاينة تعديل ملاحظة طلب"),
    ("mark_paid", "Record a verified Whish payment", "تسجيل دفعة Whish بعد التحقق منها"),
    ("archive_order", "Archive an order", "أرشفة طلب"),
    ("reopen_order", "Reopen an archived order", "إعادة فتح طلب مؤرشف"),
    ("kits", "Kit photos, videos and product links", "صور وفيديوهات وروابط الحزم"),
    ("shopadmin", "Open Shopify administration", "فتح إدارة Shopify"),
    ("shoplog", "Recent store command results", "سجل أوامر المتجر"),
    ("shopack", "Review an uncertain operation", "مراجعة عملية غير محسومة"),
]
SHOP_NAMES = frozenset(x[0] for x in SHOP_COMMANDS)
