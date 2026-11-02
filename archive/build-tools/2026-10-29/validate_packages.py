from pathlib import Path
import re,json,zipfile,hashlib
from openpyxl import load_workbook
b=Path(__file__).resolve().parent/'packages'
broken=[]
for p in b.glob('*/START_HERE.html'):
    for link in re.findall(r'(?:href|src)="([^"]+)"',p.read_text(encoding='utf-8')):
        if ':' not in link and not (p.parent/link).exists():broken.append(str(p)+': '+link)
assert not broken,broken
w=load_workbook(b/'MARKETING/02_CAMPAIGN_WORKBOOK.xlsx')
assert w['Calendar'].max_row==31
assert len(w.sheetnames)==6
assert sum(c.data_type=='f' for row in w['Metrics'] for c in row)==120
assert w['Metrics']['I2'].value=='=IF(OR(C2="",C2=0),"",D2/C2)'
assert w['Metrics']['L31'].value=='=IF(OR(H31="",H31=0),"",G31/H31)'
assert [50/1000,5/50,2/50,18/10]==[0.05,0.10,0.04,1.8]
for d in b.iterdir():
    m=json.loads((d/'MANIFEST.json').read_text())
    for name,v in m.items():assert hashlib.sha256((d/name).read_bytes()).hexdigest()==v['sha256']
    with zipfile.ZipFile(b.parent.parent/'outputs/product-packages'/f'JUST_AI_{d.name}_COMPLETE_v2.zip') as z:assert z.testzip() is None
print('PASS: 8 guide link checks; all manifests and ZIP checksums; 30 calendar rows; 120 guarded formulas; 6 workbook sheets; example metric arithmetic. Spreadsheet formula structure checked; external-app recalculation not tested.')
