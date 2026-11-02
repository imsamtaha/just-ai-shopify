// تنشئ رابط مسودة لجهة اتصال واحدة معتمدة، ولا ترسل رسالة. يضغط الإنسان إرسال بعد التحقق من الموافقة.
// JUST AI Pro • Creates a message draft URL for a single, approved contact
// Never sends a message; a human must click Send. Always check customer consent.
function createWhatsAppDraftUrl(phone, message, approved = false) {
  if (approved !== true) throw new Error('Human approval required / الموافقة البشرية مطلوبة');
  const digits = String(phone ?? '').replace(/\D/g, '');
  if (digits.length < 8 || digits.length > 15) throw new Error('Provide an international phone number / أدخل رقم هاتف دولياً');
  const body = String(message ?? '').trim();
  if (!body || body.length > 2000) throw new Error('Invalid message length / طول الرسالة غير صالح');
  return `https://wa.me/${digits}?text=${encodeURIComponent(body)}`;
}
module.exports = { createWhatsAppDraftUrl };
if (require.main === module) console.log(createWhatsAppDraftUrl('+961 70 000 000', 'Demo reply رد تجريبي', true));
