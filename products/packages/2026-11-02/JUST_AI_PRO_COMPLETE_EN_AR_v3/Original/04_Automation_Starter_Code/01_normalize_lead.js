// أداة تحقق يدوية من بيانات العميل المحتمل، ولا ترسل البيانات. استخدم بيانات جُمعت بموافقة وبطريقة قانونية.
// تُنظّف الاسم والهاتف والمنتج وتحافظ على موافقة التسويق، وتحدد السجلات التي تحتاج مراجعة.
// JUST AI Pro • Manual lead-data validation for a Make/Pipedream/Zapier code step
// Does not transmit data. Run only with lawfully collected, permissioned data.
function normalizeLead(record = {}) {
  const clean = (x) => String(x ?? '').trim().replace(/\s+/g, ' ');
  const name = clean(record.name).slice(0, 100);
  const phone = clean(record.phone).replace(/[^0-9+]/g, '');
  const product = clean(record.product).slice(0, 160);
  const consent = record.marketingConsent === true;
  const status = ['new', 'awaiting', 'quoted', 'won', 'lost'].includes(record.status) ? record.status : 'new';
  return { name, phone, product, marketingConsent: consent, status, needsReview: !name || !phone || !product };
}
module.exports = { normalizeLead };
if (require.main === module) console.log(normalizeLead({name:'  Demo Buyer عميل تجريبي ',phone:'+961 70 000 000',product:'Demo item منتج تجريبي',marketingConsent:false}));
