# JUST AI store repair verification — 2 November 2026

Scope: live JUST AI Shopify store; existing catalog and files preserved.

## Changes completed and read back

- Product 15453991436564, named "Digital product", was ACTIVE at USD 0 with JUST_AI_MARKETING_COMPLETE_v2.zip (1,997,632 bytes) and JUST_AI_MARKETING_HOW_TO.mp4 attached. Changed to DRAFT to stop new free purchases of the paid marketing bundle. Files and product were preserved. The paid Marketing Toolkit remains ACTIVE at USD 34.
- Corrected the BASIC, PRO and Sprint usage sections: removed instructions for an unattached complete v2/Original layout; disclosed that the attached customer ZIP remains v1 and v3 is not delivered yet. Existing images, videos, prices and other description sections were retained. Read back all three descriptions and confirmed the new guide, embedded video, active status and prices.
- JUSTAI10 remains a 10% discount, with one use per customer. Changed the total usage limit from 15 to 10 and saved. No completed use was recorded during testing.
- Deactivated Shopify Test payment gateway. Admin returned to the payment-provider selection screen. Whish Money and Money Order remain active manual payment methods. No live card provider is installed by this change.

## Verification

| Check | Result |
| --- | --- |
| Public store catalog | Loaded; eight intended products displayed, without the draft generic product |
| Sprint / BASIC / PRO | USD 9 / 19 / 39 |
| Three-item cart | USD 67.00 |
| JUSTAI10 checkout application | USD 6.70 discount; total USD 60.30 |
| Payment test | Checkout reached; no order submitted, no transfer made, no payment marked paid |
| Digital Products connection | Succeeded; canonical domain njcr1h-zx.myshopify.com corresponds to the just-ai-store admin alias |
| App CI on f800a4c63a7dbedfe35c4c9461c68937c2e38bf8 | GitHub Actions run 41399602843: app and telegram jobs both successful |

CI evidence: https://github.com/imsamtaha/just-ai-shopify/actions/runs/41399602843

## Unfinished delivery upgrade

Prepared packages were retrieved from this private repository and matched against their Git blob hashes. All three ZIP CRC checks passed.

| Package | Bytes |
| --- | ---: |
| JUST_AI_BASIC_COMPLETE_EN_AR_v3.zip | 1,922,553 |
| JUST_AI_PRO_COMPLETE_EN_AR_v3.zip | 2,141,814 |
| JUST_AI_SPRINT_COMPLETE_EN_AR_v3.zip | 1,660,540 |

These packages were NOT attached to Shopify. The cloud browser file chooser did not fire from the app's upload button or direct file input; the upload dialog was cancelled. Current v1 attachments were preserved. Add each matching v3 ZIP through Digital Products, verify its saved name and byte size, then revise the listing guide to describe v3. Preserve old versions as requested; clearly identify the recommended new ZIP.

The Marketing Toolkit has its complete v2 ZIP attached. BASIC's app UI reported automatic fulfillment and historical download counts, but this turn did not perform a buyer download, validate a Whish transfer, or verify an automatic customer email. A production purchase/download test and Android file-opening test remain outstanding.

The embedded app's registration, hosting and installation remain separate from these live-store catalog repairs. This report does not claim that the repository app was deployed.

## Rollback and continuation

Descriptions can be restored using Shopify product history if needed. The generic product remains a preserved draft. The discount's previous limit was 15; the test gateway can be reactivated for a controlled test session, but should not be presented as a live card-payment method.

Do not confirm a manual payment without independently verifying the transfer. Do not publish paid ZIPs as public CDN assets.

## العربية

تم إيقاف المنتج المجاني المكرر كمسودة مع حفظ ملفاته، وتصحيح تعليمات الحزم الثلاث، وضبط خصم JUSTAI10 على 10% لأول عشرة استخدامات ومرة لكل عميل، وتعطيل بوابة الدفع التجريبية. نجح اختبار السلة والخصم حتى صفحة الدفع دون تنفيذ طلب.

ملفات v3 جاهزة وسليمة، لكن رفعها تعثر بسبب أداة اختيار الملفات. بقيت مرفقات v1 محفوظة. الدفع الفعلي والتنزيل وبريد التسليم واختبار Android لم تُثبت في هذا الفحص.
