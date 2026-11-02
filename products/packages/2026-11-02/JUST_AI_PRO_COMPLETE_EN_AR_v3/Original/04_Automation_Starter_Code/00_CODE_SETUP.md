# Code utilities (optional)

Three small CommonJS JavaScript snippets are included for **manual/test-mode code steps** in Node.js-compatible environments:

1. Normalize a lead record while preserving marketing-consent status.
2. Flag duplicate order references before importing data.
3. Generate a WhatsApp draft URL with explicit human approval. It does **not** send a message.

The scripts use no external dependencies, secrets or network calls. Run `node 01_normalize_lead.js` etc. with Node.js 18+ as a demo. To adapt to Make, Zapier or Pipedream, follow that platform's code-step input/output conventions. They are examples, not plug-and-play integrations.

**Security:** Do not store API keys in scripts or this Notion workspace. Use your automation platform's secret manager.

## Input and output keys
`name`, `phone`, `product`, `marketingConsent` (boolean) and `status` are stable input keys. Status codes are `new`, `awaiting`, `quoted`, `won`, `lost`. `needsReview` is true when name, phone or product is missing. `orderReference` is the order ID key; the dedupe function ignores blank references and returns unique repeated IDs. `createWhatsAppDraftUrl` takes a phone, message and `approved`; approval must be true, the international number must contain 8–15 digits after formatting is removed, and the message must contain 1–2000 characters. Verify the number, consent and content before opening the link. A human clicks Send. All DEMO data is fictional. Do not translate code keys or function names.


---

# العربية

# أدوات برمجية اختيارية

تضم الحزمة ثلاث أدوات JavaScript صغيرة بصيغة CommonJS للاستخدام اليدوي أو في خطوات برمجية بوضع الاختبار ضمن بيئة متوافقة مع Node.js:
1. تنسيق سجل عميل محتمل مع الحفاظ على حالة الموافقة التسويقية.
2. كشف مراجع الطلبات المتكررة قبل استيراد البيانات.
3. إنشاء رابط مسودة واتساب لجهة اتصال واحدة بعد موافقة بشرية صريحة؛ لا يرسل رسالة.

لا تستخدم الأدوات مكتبات خارجية أو أسراراً أو اتصالات شبكية. شغّل `node 01_normalize_lead.js` وبقية الملفات بالطريقة نفسها باستخدام Node.js 18 أو أحدث لعرض مثال. للتكييف مع Make أو Zapier أو Pipedream، اتبع قواعد المدخلات والمخرجات للخطوة البرمجية في المنصة. هذه أمثلة وليست تكاملات تعمل بمجرد الاستيراد.

لا تخزّن مفاتيح API في الشيفرات أو مساحة Notion. استخدم مدير الأسرار في منصة الأتمتة.

## مفاتيح المدخلات والنتائج
- `name`: الاسم؛ `phone`: الهاتف؛ `product`: المنتج؛ `marketingConsent`: موافقة التسويق، بقيمة منطقية true أو false؛ `status`: الحالة.
- الحالات التقنية هي `new` جديد، `awaiting` بانتظار إجراء، `quoted` أُرسل عرض سعر، `won` تحوّل إلى عميل، و`lost` لم يتحول.
- `needsReview` يعني الحاجة إلى المراجعة عند غياب الاسم أو الهاتف أو المنتج.
- `orderReference` هو مرجع الطلب. تقبل أداة كشف التكرار مصفوفة سجلات وتعيد قائمة المراجع المتكررة الفريدة. تُتجاهل المراجع الفارغة.
- تقبل `createWhatsAppDraftUrl` الهاتف والرسالة و`approved`. يجب أن تكون الموافقة true. يجب أن يحتوي الهاتف الدولي على 8 إلى 15 رقماً بعد إزالة التنسيق، وأن يكون طول الرسالة من حرف واحد إلى 2000 حرف. تحقق من الرقم والموافقة والمحتوى قبل فتح الرابط؛ يضغط الإنسان زر الإرسال.
- أمثلة DEMO بيانات خيالية. لا تغيّر أسماء الدوال أو المفاتيح عند ترجمة رسائل العرض.
