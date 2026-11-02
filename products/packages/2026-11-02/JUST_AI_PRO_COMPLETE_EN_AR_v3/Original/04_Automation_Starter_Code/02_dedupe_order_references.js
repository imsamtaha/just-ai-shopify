// أداة محلية لكشف مراجع الطلبات المتكررة دون إرسال بيانات. تُهمل المراجع الفارغة.
// JUST AI Pro • Deterministic order reference deduplicator (local utility)
function findDuplicateOrderReferences(rows) {
  if (!Array.isArray(rows)) throw new TypeError('rows must be an array / يجب أن تكون المدخلات مصفوفة');
  const seen = new Set(); const duplicates = [];
  for (const row of rows) {
    const ref = String(row?.orderReference ?? '').trim();
    if (!ref) continue;
    if (seen.has(ref)) duplicates.push(ref); else seen.add(ref);
  }
  return [...new Set(duplicates)];
}
module.exports = { findDuplicateOrderReferences };
if (require.main === module) console.log(findDuplicateOrderReferences([{orderReference:'A1'},{orderReference:'A2'},{orderReference:'A1'}]));
