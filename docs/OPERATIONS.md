# Store operations

## Product workflow

Review title, bilingual description, variant price, publication channels and shipping requirements in Shopify Admin. A product marked ACTIVE is not proof that a particular sales channel publishes it. The app links to Shopify's editor.

## Secure delivery

Use the version map in `products/README.md`. Attach the intended ZIP using the store's digital-delivery application, then verify the saved filename and size. Test delivery separately from catalog visibility. Do not upload paid customer ZIPs as public theme or public CDN assets.

## Payments

The existing workflow is manual Whish confirmation. Independently verify the transfer, match order and amount, and only then record payment. Telegram's mark-paid command does not contact Whish or validate a receipt. Payment instructions, enabled methods, checkout and delivery must be checked in the actual store before claiming readiness.

## Telegram

Source is in `integrations/telegram/`, including the Shopify configuration wizard and doctor. Configure credentials privately, verify the configured bot identity and owner allowlist, and establish whether a webhook or poller already owns that bot before starting anything.

## Historical evidence

Files under `docs/history/` and `catalog/history/` are dated records. Earlier prices, publication statements and activation results may be stale. Importing them does not re-run their checks.

## العربية

هذا المستودع يجمع التطبيق وملفات المنتجات وأدلة التشغيل. يجب ربط التطبيق وتثبيته داخل Shopify قبل عرض البيانات الحية. تأكد من الدفع في Whish قبل تأكيد الطلب، واربط ملفات المنتجات بالتسليم الرقمي الآمن. تقارير التشغيل القديمة لا تثبت حالة المتجر الحالية.
