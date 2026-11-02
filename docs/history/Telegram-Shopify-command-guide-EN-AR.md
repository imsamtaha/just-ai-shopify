> **Live deployment update — 29 October 2026:** @JustAI_chatbot runs on Google Cloud Run. `/shop` now works there with kit-preview and Shopify Admin links. Private order/payment API changes are not connected yet. The guide below describes the separate Windows package; do not start a second polling process for this cloud bot. See [the live deployment report](Cloud-Telegram-shop-fix.md).

# JUST AI store controls from Telegram

The existing JUST AI bot now includes an optional Arabic/English Shopify control panel for `just-ai-store.myshopify.com`. The local implementation is ready for credential setup; it is not a verified live Telegram deployment. It uses the existing bot process, private chats and SQLite database. OpenAI is not required for store commands, and store data is not sent to AI by these commands.

## Activate on this Windows computer

1. Open `activate-shopify-windows.cmd` in the bot folder. It runs secure configuration, checks Telegram identity/webhook and Shopify identity/scopes, then starts the bot only if checks pass.
2. Enter the token for your existing bot in the hidden terminal prompt. The saved expected username is `JustAI_chatbot`; change it if you use a different bot. Never send a token, client secret or password in chat.
3. Enter your personal numeric Telegram ID. If you do not know it, first run `activate-windows.cmd` in setup mode, send `/whoami` to the bot, stop that process with Ctrl+C and use the returned ID. Usernames are not used as owner authorization.
4. Install your own Shopify app in this store. Request `read_products`, `write_products`, `read_orders` and `write_orders`; do not add theme or payment-account permissions for these commands. Orders older than Shopify's standard access window require the separate approved `read_all_orders` scope.
5. Enter either an existing Admin API access token, or a client ID and client secret for an app/store in your own Shopify organization. The app's client-credentials access token is refreshed in memory. The connected Shopify app in ChatGPT does not supply credentials to this local bot.
6. After successful activation, send `/shop` in your private bot conversation. Keep the host awake and the bot terminal running. This setup does not install a background service or cloud host. Do not run a second poller for the same bot; existing webhooks require deployment review before switching.

Both configuration wizards save credentials only in this package's `.env` with Windows permissions limited to the current user and SYSTEM. Secret values are not printed or placed in shell command history. Portable ZIPs exclude `.env`, local databases and the Python environment. `SHOPIFY_ENABLED=false` leaves the optional integration disabled.

For later checks:

```powershell
.\.venv\Scripts\python.exe shopify_doctor.py --live
.\.venv\Scripts\python.exe doctor.py --live
.\.venv\Scripts\python.exe activate.py
```

The two doctor commands verify identity/access without sending Telegram messages or changing Shopify orders/products. Running `activate.py` then starts polling and registers the command menu.

## Command guide

Commands remain Latin so Telegram can register them. `/language ar` switches menus and explanations to Arabic; `/language en` selects English.

| Command | What it does | بالعربية |
| --- | --- | --- |
| `/shop` | Live store status and control buttons | حالة المتجر وأزرار التحكم |
| `/orders` | Latest accessible orders, 10 per page | آخر الطلبات، 10 في الصفحة |
| `/orders unpaid` | Pending or partially paid orders | الطلبات غير المدفوعة بالكامل |
| `/orders open` / `/orders unfulfilled` | Filter by order or delivery state | تصفية الطلبات حسب الحالة |
| `/order #1001` | Payment/delivery state, totals, items and note | تفاصيل الطلب والدفع والتسليم |
| `/products` / `/products search` | Browse/search products | عرض المنتجات أو البحث عنها |
| `/product basic` | Product and variant IDs/prices | معلومات الحزمة ومعرفات خياراتها |
| `/price VARIANT_ID 29.00` | Preview a USD variant price change | معاينة تعديل السعر بالدولار |
| `/product_title basic New title` | Preview a product title change | معاينة تعديل اسم المنتج |
| `/product_description basic New copy` | Replace the complete description with escaped plain text; removes existing embedded media | استبدال الوصف بالكامل؛ يزيل الوسائط المضمّنة |
| `/product_status basic draft` | Set `active`, `draft` or `archived` | تفعيل المنتج أو تحويله لمسودة أو أرشفته |
| `/order_note #1001 Note` | Replace the order note | تعديل ملاحظة الطلب |
| `/mark_paid #1001` | Record a verified Whish payment after confirmation | تسجيل دفعة Whish بعد التحقق والتأكيد |
| `/archive_order #1001` | Archive the order; does not cancel/refund | أرشفة الطلب دون إلغاء أو استرداد |
| `/reopen_order #1001` | Reopen an archived, noncancelled order | إعادة فتح طلب مؤرشف غير ملغى |
| `/kits` / `/kits pro` | Price-free sample photo and product-page video/description link | صورة دون سعر ورابط الفيديو والوصف |
| `/shoplog` | Last 15 store actions and their results | آخر 15 إجراء ونتائجها |
| `/shopack AUDIT_ID` | Confirm that you reviewed an uncertain result in Shopify; unlock the record without repeating the operation | تأكيد مراجعة نتيجة غير محسومة ورفع الحظر دون تكرارها |
| `/shopadmin` | Open orders, products/media, payments, themes or digital-download apps | فتح أقسام الإدارة |

Product commands accept a numeric Shopify product ID, a full product GID, or the aliases below. Price commands require a **variant** ID, available from `/product`.

| Alias | Product | Product ID | Current variant ID |
| --- | --- | --- | --- |
| `basic` | JUST AI Sales Kit BASIC | 15428288446740 | 67729998610708 |
| `pro` | JUST AI Sales Kit PRO | 15431893352724 | 67748257038612 |
| `sprint` | JUST AI 7-Day Content Sprint | 15432147599636 | 67750008815892 |

The sample command amount `29.00` is only an example; setup/testing did not change product prices. IDs above were verified during this store's media work; use `/product` to refresh them if products change.

## Confirmation and payment behavior

Every write requires an owner-only preview and a single-use confirmation within two minutes. A newer preview replaces the previous one. The bot checks current record data again before submitting and reads the result back before reporting success. This detects changes already visible before submission; Shopify does not provide an atomic compare-and-swap for these mutations, so another administrator can still edit concurrently between the read and write.

Only `SHOPIFY_OWNER_IDS` that also belong to `ALLOWED_USER_IDS` can use store controls. Groups and stale queued commands cannot trigger store operations. The API is pinned to this store's numeric identity and host; URLs supplied in Telegram cannot redirect requests or receive credentials. User text is passed as GraphQL variables, not executable code.

`/mark_paid` is limited to eligible orders whose payment gateways are Whish. It does not log into Whish or collect/transfer funds. Independently verify receipt of the exact outstanding amount before confirming; a customer receipt image alone is not payment verification. Shopify digital-delivery automations may run when payment is recorded. Setup does not change those delivery settings.

A durable audit row is written before each change. Network timeouts, crashes or unsuccessful readback leave a record blocked against further writes until the owner checks Admin and confirms `/shopack`. There are no automatic retries of mutations. Audit records contain owner ID, action, Shopify record ID, time and status; they exclude notes, customer details and credentials. The audit survives `/forget` so unresolved operations remain blocked. The database itself is local and not encrypted; Telegram retains the messages you receive.

## Operations that open Shopify Admin

Refunds, cancellations, fulfillment/delivery, new product creation, inventory adjustments, discount creation, media/file uploads, payment provider configuration, payout/banking details, themes, app installation and settings remain Shopify Admin workflows. The buttons make them accessible from Telegram but do not execute them inside the bot. The bot never publishes a theme or modifies payment-account details. AI chat cannot execute store commands automatically.

BASIC previews contain actual template excerpts. PRO and Sprint videos are product overviews; illustrative samples are labelled. Viewing a preview does not deliver paid toolkit ZIP files to customers.

## التفعيل والاستخدام

افتح `activate-shopify-windows.cmd` على هذا الكمبيوتر وأدخل البيانات السرية في نافذة الطرفية فقط. لا ترسل رمز البوت أو مفاتيح Shopify في Telegram أو ChatGPT. أدخل رقم حسابك الشخصي في Telegram لتحديد المالك، ثم انتظر نجاح التحقق من هوية البوت والمتجر. بعد التشغيل أرسل `/language ar` ثم `/shop`.

الأوامر الخاصة بالمتجر لا تحتاج اشتراك OpenAI. أبقِ الكمبيوتر مستيقظًا والبوت قيد التشغيل. كل تعديل يعرض معاينة وزر تأكيد لمدة دقيقتين. عند وجود نتيجة غير محسومة، راجع المتجر قبل رفع الحظر عبر `/shopack`؛ لا تكرر عملية الدفع دون تحقق. الإعدادات المتقدمة مثل بوابات الدفع والاسترداد والقوالب تُفتح من `/shopadmin` وتُدار في Shopify.

## Official references

- [Shopify client credentials grant](https://shopify.dev/docs/apps/build/authentication-authorization/client-credentials-grant)
- [Shopify access scopes](https://shopify.dev/docs/api/usage/access-scopes)
- [Shopify orderMarkAsPaid](https://shopify.dev/docs/api/admin-graphql/2026-10/mutations/orderMarkAsPaid)
- [Shopify productVariantsBulkUpdate](https://shopify.dev/docs/api/admin-graphql/2026-10/mutations/productVariantsBulkUpdate)
- [Telegram Bot API](https://core.telegram.org/bots/api)
