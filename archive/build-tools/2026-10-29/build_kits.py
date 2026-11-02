from pathlib import Path
import json, shutil, zipfile, html, csv, textwrap
from PIL import Image, ImageDraw, ImageFont
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs'/'product-packages'
BUILD=ROOT/'work'/'packages'
DATA=json.loads((ROOT/'work/kit-content.json').read_text(encoding='utf-8'))
OUT.mkdir(parents=True,exist_ok=True)
BUILD.mkdir(parents=True,exist_ok=True)
CSS='''body{margin:0;background:#f4f2ec;color:#142b3a;font:18px/1.7 system-ui,Arial,sans-serif}main{max-width:960px;margin:auto;padding:48px 24px}header{border-bottom:3px solid #12a398;padding-bottom:24px}small,.eyebrow{letter-spacing:2px;color:#137c76}h1{font-size:42px;line-height:1.15}h2{line-height:1.3}section{background:white;padding:28px;margin:24px 0;border-radius:16px}a{color:#08756e}code{overflow-wrap:anywhere}video{width:100%;border-radius:12px}li{margin:8px 0}.ar{border-top:1px solid #ddd;padding-top:14px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd7d8;padding:9px;text-align:left}@media print{video{display:none}section{break-inside:avoid}body{font-size:12px}}'''
def write(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
def page(title,body):return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+CSS+'</style></head><body><main>'+body+'</main></body></html>'
def guide(key,d):
    base=BUILD/key;base.mkdir(exist_ok=True)
    if d['source']:shutil.copytree(ROOT/'work/source'/d['source'],base/'Original',dirs_exist_ok=True)
    steps=''
    transcript='# '+d['name']+' — tutorial transcript\n\nEnglish synthetic narration. Arabic written translation below each step. Original instructional slide video; fictional examples. Version 2.0, 29 October 2026.\n\n'
    for i,s in enumerate(d['steps'],1):
        steps+=f'<section><small>STEP {i:02d}</small><h2>{html.escape(s[0])}</h2><p>{html.escape(s[1])}</p><p class="ar" lang="ar" dir="rtl">{html.escape(s[2])}</p><ul><li>{html.escape(s[3])}</li><li>{html.escape(s[4])}</li></ul></section>'
        transcript+=f'## {i}. {s[0]}\n\n{s[1]}\n\n{s[2]}\n\n'
    filelinks=''.join(f'<li><a href="{p.relative_to(base).as_posix()}">{html.escape(p.relative_to(base).as_posix())}</a></li>' for p in sorted(base.rglob('*')) if p.is_file())
    note='The original kit is in Original/. Its existing license and language limitations still apply.' if d['source'] else 'A standalone campaign-planning kit. It does not include BASIC, PRO or the Content Sprint planner.'
    body=f'<header><div class="eyebrow">JUST AI / PRACTICAL GUIDES / v2.0</div><h1>{d["name"]}</h1><h2 lang="ar" dir="rtl">{d["ar"]}</h2><p>{d["goal"]}</p><p lang="ar" dir="rtl">{d["argoal"]}</p></header><section><h2>Watch, then try</h2><video controls preload="metadata" poster="VIDEO_POSTER.png"><source src="HOW_TO.mp4" type="video/mp4"><track kind="subtitles" src="CAPTIONS_EN.vtt" srclang="en" label="English">Open HOW_TO.mp4 in your video player.</video><p>English synthetic narration with readable instructional slides. Arabic written steps and a complete transcript are included. Pause between steps and try the task in your own copy.</p><p lang="ar" dir="rtl">الشرح بصوت اصطناعي إنجليزي مع شرائح واضحة. الخطوات العربية مكتوبة أدناه. أوقف الفيديو بين الخطوات وجرّب في نسختك.</p><p><a href="TRANSCRIPT_EN_AR.md">Read the transcript</a> · <a href="HOW_TO.mp4">Open the video</a></p></section>'+steps+f'<section><h2>Files and requirements</h2><p>{note}</p><ul>{filelinks}</ul><p>Extract the entire ZIP before opening files. Use a modern browser, a DOCX editor and/or an XLSX-compatible spreadsheet app as needed. AI and third-party tools use your own accounts and may have separate charges. No account connections, automatic sending or automatic publishing are included.</p><h3>Troubleshooting</h3><ul><li>Video does not play: open HOW_TO.mp4 in a local MP4 player or read the transcript.</li><li>File will not edit: make a local working copy and open it in an app that supports the format.</li><li>Arabic appears reversed: use an editor with right-to-left support.</li><li>Spreadsheet rates are blank: enter the required denominator; blank is not zero performance.</li><li>Planner data disappeared: restore your exported JSON backup. Browser storage can be cleared.</li></ul><p>Keep customer details private. Use only content you own or have permission to use. Examples are fictional and do not promise revenue, reach or results.</p><p>Support: <a href="mailto:ImSamtaha.ai@gmail.com">ImSamtaha.ai@gmail.com</a>. Include product name, filename and the problem; never send passwords or private customer records. Custom work is agreed separately.</p></section>'
    write(base/'START_HERE.html',page(d['name'],body));write(base/'TRANSCRIPT_EN_AR.md',transcript)
    return base

def marketing():
    b=BUILD/'MARKETING';b.mkdir(exist_ok=True)
    write(b/'01_CAMPAIGN_BRIEF.md','''# Campaign brief / موجز الحملة

Make a working copy. Complete every field using real facts before generating copy.
انسخ النموذج واملأ الحقول بحقائق فعلية قبل صياغة المحتوى.

| Field / الحقل | Your answer / إجابتك |
|---|---|
| Business / النشاط | |
| One audience / جمهور محدد | |
| Problem they recognize / المشكلة | |
| One offer and exact contents / العرض ومحتوياته | |
| Price and currency / السعر والعملة | |
| Evidence you can show / دليل قابل للعرض | |
| What is excluded / غير المشمول | |
| One next action / الخطوة المطلوبة | |
| Channel and owner / القناة والمسؤول | |
| Start/end and review date / المدة والمراجعة | |
| Budget ceiling you approve / سقف الإنفاق | |
| Success metric / مقياس النجاح | |
| Current baseline / الوضع الحالي | |
| Hypothesis, not promise / الفرضية وليست وعداً | |

## Fictional completed brief / مثال خيالي
Business: Cedar Desk, a fictional slide-design studio.
Audience: founders reviewing a pitch presentation themselves.
Problem: crowded slides hide the main message.
Offer: a self-service editable slide review checklist with a worked example.
Example price: USD 9. This is not a price for a JUST AI product.
Proof: demonstrate three checks on a fictional slide with before/after captions.
Excluded: slide redesign, fundraising advice, client-specific feedback.
CTA: read the exact checklist contents on the product page.
Channel: organic Instagram. Owner: studio owner. Period: 30 days.
Budget: zero ad spend in this example. Staff time still has a cost.
Metric: qualified inquiries from people who understand the self-service scope.
Baseline: unknown. First week establishes a baseline, not a guaranteed target.
Hypothesis: clearer demonstrations may improve understanding of the offer.

المثال: استوديو خيالي يساعد المؤسسين على مراجعة شرائحهم بأنفسهم. العرض قائمة مراجعة رقمية بسعر تجريبي 9 دولارات، لا خدمة تصميم. الدليل عرض تطبيقي على شريحة خيالية. القناة إنستغرام دون إعلانات مدفوعة. مقياس النجاح استفسارات مناسبة تفهم حدود العرض. الفرضية قابلة للاختبار ولا تضمن نتيجة.
''')
    prompts=[
    ('Audience','Using only this brief, describe one audience, three likely questions and the assumptions that still need validation. Do not invent research.','استناداً إلى الموجز فقط، صف جمهوراً واحداً وثلاثة أسئلة محتملة والافتراضات التي تحتاج تحققاً. لا تختلق بحثاً.'),
    ('Offer clarity','Rewrite this offer as audience, job, deliverables, requirements and exclusions. Keep the exact price and flag contradictions.','أعد صياغة العرض إلى جمهور ومهمة ومخرجات ومتطلبات واستثناءات. حافظ على السعر وأظهر التناقضات.'),
    ('Content pillars','Suggest three content themes linked to the audience problem. Give two factual post ideas per theme; identify facts I must supply.','اقترح ثلاثة محاور مرتبطة بمشكلة الجمهور وفكرتين لكل محور. حدد الحقائق التي يجب أن أزوّدك بها.'),
    ('Calendar','Turn these approved themes into a 30-day draft calendar. Include topic, format, one CTA, evidence needed and owner. Avoid repetitive sales posts.','حوّل المحاور المعتمدة إلى مسودة تقويم 30 يوماً مع الموضوع والصيغة ودعوة واحدة والدليل المطلوب والمسؤول.'),
    ('Educational caption','Draft a helpful caption from these verified facts. Structure it as problem, practical step and one invitation. No unsupported promises.','اكتب نصاً مفيداً من الحقائق المؤكدة: مشكلة وخطوة عملية ودعوة واحدة دون وعود غير موثقة.'),
    ('Bilingual adaptation','Adapt this approved English caption into natural Arabic without changing numbers, offer terms or limitations. List ambiguous phrases.','كيّف النص الإنجليزي المعتمد إلى عربية طبيعية دون تغيير الأرقام والشروط والقيود، وحدد العبارات الغامضة.'),
    ('Demonstration script','Write a 30-second demonstration script using this actual process. Include shot, spoken line, on-screen label and evidence. Label fictional data DEMO.','اكتب سيناريو عرض مدته 30 ثانية من الخطوات الفعلية مع اللقطة والجملة والنص المرئي والدليل. علّم البيانات الخيالية كتجريبية.'),
    ('FAQ','Draft five FAQs using only the supplied product facts. Answer unknowns with a question for the owner rather than an invented policy.','صغ خمسة أسئلة شائعة من معلومات المنتج فقط. عند غياب الإجابة، وجّه سؤالاً للمالك ولا تختلق سياسة.'),
    ('Landing page','Create a concise page outline: buyer problem, contents, demonstration, requirements, delivery and CTA. Use only provided proof.','اكتب مخطط صفحة موجزاً: مشكلة العميل والمحتويات والعرض والمتطلبات والتسليم والدعوة، باستخدام الدليل المقدم فقط.'),
    ('Opt-in follow-up','Draft one low-pressure follow-up to this customer who asked for a reminder. Use anonymous context, confirm current facts and include an easy way to decline.','اكتب متابعة واحدة دون ضغط لعميل طلب تذكيراً. استخدم سياقاً مجهول الهوية وحقائق حديثة وخياراً واضحاً لرفض المتابعة.'),
    ('Experiment','Turn this question into a test with one changed variable, a metric, equal review windows and conditions that would make the comparison unreliable.','حوّل السؤال إلى تجربة بمتغير واحد ومقياس وفترات متساوية، وحدد ما يجعل المقارنة غير موثوقة.'),
    ('Review','Review these aggregate results. Separate observation from explanation, flag missing data and suggest one next test. Do not claim causality from a small sample.','راجع النتائج المجمعة وافصل الملاحظة عن التفسير، وحدد البيانات الناقصة واقترح اختباراً واحداً دون استنتاج سببية من عينة صغيرة.')]
    intro='# 12 paired AI prompts / ١٢ توجيهاً باللغتين\n\nFor every prompt, paste your completed brief and relevant approved facts. Replace placeholders. Ask the tool to list missing facts. Remove personal data. These prompts draft text; they do not publish, send or launch ads.\n\nلكل توجيه، أرفق موجزك والحقائق المعتمدة فقط واحذف البيانات الشخصية. راجع الناتج قبل الاستخدام.\n\n'
    write(b/'03_AI_PROMPTS_EN_AR.md',intro+'\n\n'.join(f'## {i}. {t}\n\nEN: {en}\n\nAR: {ar}\n\nInput: [completed brief] + [approved facts]. Output: draft + missing facts + review checklist.' for i,(t,en,ar) in enumerate(prompts,1)))
    write(b/'04_CAMPAIGN_PLAYBOOKS.md','''# Three campaign playbooks / ثلاثة أدلة للحملات

## 1. New offer launch / إطلاق عرض
Goal: help the right buyer understand a new offer.
Before starting: confirm contents, price, delivery, limitations and capacity.
Days 1–3: collect real questions; publish a useful tip tied to the problem.
Days 4–7: demonstrate one included item with a fictional or permitted example.
Days 8–10: answer the most important scope and delivery questions.
Days 11–14: invite readers to the product page with accurate terms; no invented deadline.
Review: compare product-page visits and qualified inquiries during equal windows. If people misunderstand the scope, rewrite the offer before spending more.
الخطوات: تحقق من العرض، اشرح المشكلة، اعرض عنصراً فعلياً، أجب عن الأسئلة ثم ادعُ لقراءة التفاصيل. إن لم يفهم الجمهور نطاق الخدمة، حسّن الشرح قبل زيادة الإنفاق.

## 2. Educational series / سلسلة تعليمية
Goal: answer one recurring customer question through practical examples.
Pick a problem you can demonstrate; split it into three manageable lessons.
Publish lesson 1 as a checklist, lesson 2 as a demonstration and lesson 3 as an FAQ.
Use a consistent topic and one action per post. Invite questions without requesting private data publicly.
Review saves, substantive questions and relevant clicks. High views alone do not establish buyer intent.
الخطوات: اختر سؤالاً متكرراً وقدّم قائمة عملية وعرضاً تطبيقياً وأسئلة شائعة. راقب الحفظ والأسئلة المفيدة والنقرات المناسبة، لا المشاهدات وحدها.

## 3. Requested follow-up / متابعة بموافقة العميل
Goal: deliver the reminder or information a customer requested.
Check that the request and channel are recorded and still relevant.
Verify current stock, price and offer terms. Write one personal, factual reminder.
Review before sending manually. If the person declines, record that and stop promotional follow-up.
No purchased lists, scraped contacts, automatic bulk sending or fabricated familiarity.
Review replies for usefulness, not just volume. Keep private details outside AI prompts and public worksheets.
الخطوات: تحقق من طلب المتابعة، راجع المعلومات، اكتب تذكيراً شخصياً واحداً ثم راجعه وأرسله يدوياً. احترم الرفض ولا تستخدم قوائم مشتراة أو بيانات مستخرجة دون إذن.
''')
    write(b/'05_COPY_CANVAS.md','''# Copy canvas / مخطط النص

Use one canvas per asset. Write short, concrete answers.
1. Audience / الجمهور: Who should recognize themselves?
2. Problem / المشكلة: What specific task is difficult?
3. Useful step / الخطوة: What can the reader do now?
4. Evidence / الدليل: What can you actually show or substantiate?
5. Offer / العرض: What exact files or service are included?
6. Limitation / القيد: What should the buyer not expect?
7. Action / الدعوة: What is one useful next step?
8. Review / المراجعة: Are price, claims, links, translation and permissions correct?

## Fictional completed example / مثال خيالي
Audience: a founder reviewing a short pitch deck.
Problem: multiple messages compete on one slide.
Step: write the single sentence the audience should remember.
Evidence: a labelled fictional slide before and after changing the heading.
Offer: editable checklist and worked example.
Limitation: no redesign service or fundraising guarantee.
Action: read the checklist contents before buying.

EN draft: A crowded slide can hide your main idea. Write the one sentence your audience should remember, then make it the heading. See our fictional before-and-after example. Need a repeatable review process? Read the checklist contents to check whether the self-service format fits your work.

AR draft: قد تخفي الشريحة المزدحمة فكرتك الرئيسية. اكتب الجملة التي تريد أن يتذكرها الجمهور واجعلها العنوان. شاهد المثال الخيالي قبل التعديل وبعده. تحتاج إلى خطوات مراجعة متكررة؟ اقرأ محتويات القائمة لتتأكد من أن صيغة الاستخدام الذاتي تناسبك.
''')
    write(b/'06_REVIEW_CHECKLIST.md','''# Review checklist / قائمة المراجعة

## Before publishing / قبل النشر
- One audience, one useful point and one next action.
- Prices, stock, delivery, included items and exclusions match the actual offer.
- All placeholders removed; English and Arabic reviewed separately.
- Evidence exists for factual claims; fictional examples labelled.
- Links open correctly; images and music have appropriate usage rights.
- No private customer information, fake testimonials or invented urgency.
- Budget and owner approved before any paid campaign is started elsewhere.

جمهور واضح، معلومة مفيدة ودعوة واحدة. طابق الأسعار والمحتويات والتسليم، وراجع اللغتين والروابط والحقوق. لا تنشر بيانات خاصة أو شهادات مختلقة. اعتماد الميزانية يسبق إطلاق إعلان مدفوع.

## After the test / بعد التجربة
- Record actual values, source and observation window.
- Separate clicks, qualified inquiries and confirmed orders.
- Use equal observation windows; flag small samples and tracking gaps.
- Calculate ratios only when their denominator is greater than zero.
- ROAS is revenue / ad spend, not profit or proof of causality.
- Record one learning, one uncertainty and one next change.
- Save a dated workbook copy. Archive unused experiments without erasing results.

سجّل القيم الفعلية ومصدرها والفترة. افصل النقرات والاستفسارات والطلبات. لا تحسب نسبة بمقام صفر. عائد الإعلان ليس ربحاً. سجّل تعلّماً واحداً وحدود الاستنتاج وخطوة تالية واحفظ نسخة مؤرخة.
''')
    write(b/'07_LICENSE.txt','''JUST AI AI Marketing Toolkit — single-business use
You may edit the templates and use the resulting marketing content for one business you own or operate. Keep the original toolkit, video and templates private. Reselling, sublicensing or redistributing the toolkit, or using it as a multi-client agency template library, is not included. Contact ImSamtaha.ai@gmail.com for expanded use.
No software hosting, paid accounts, advertising spend, campaign management, custom implementation, guaranteed support response time, ongoing updates or sales results are included. Third-party tools have their own terms and charges. Original educational materials, version 2.0, 29 October 2026.
استخدام لنشاط واحد تملكه أو تديره. يمكنك تعديل القوالب واستخدام المحتوى الناتج لنشاطك، ولا يشمل الترخيص إعادة بيع الحزمة أو توزيعها أو استخدامها لعدة عملاء. لا تشمل الحزمة خدمات مستضافة أو إعلانات أو تنفيذ مخصص أو ضمان نتائج. للتوسع تواصل مع الدعم.
''')
    w=Workbook();start=w.active;start.title='Start'
    for row in [('JUST AI — Campaign Workbook','v2.0'),('Use','Read Start, complete Brief, customize Calendar, then enter actual Metrics.'),('Arabic / العربية','أكمل الموجز والتقويم ثم سجّل المؤشرات الفعلية.'),('Demo','Demo values are fictional. Metrics begins blank.'),('Rates','CTR = clicks / impressions; inquiry rate = qualified inquiries / clicks; ROAS = revenue / ad spend.'),('Limits','ROAS is not profit. Rates remain blank for zero denominators. No automatic account connection.'),('Working copy','Save a dated copy. The blue-text cells are inputs; dark cells in calculated columns contain formulas.')]:start.append(row)
    brief=w.create_sheet('Brief');brief.append(['Field / الحقل','Your answer / إجابتك'])
    for f in ['Business / النشاط','Audience / الجمهور','Problem / المشكلة','Offer / العرض','Price / السعر','Proof / الدليل','Exclusions / الاستثناءات','CTA / الدعوة','Channel / القناة','Owner / المسؤول','Review date / المراجعة','Budget ceiling / سقف الإنفاق','Baseline / خط الأساس','Hypothesis / الفرضية']:brief.append([f,''])
    cal=w.create_sheet('Calendar');cal.append(['Day','Date','Suggested angle / الزاوية','Format','Verified fact / حقيقة','Caption draft / النص','CTA / الدعوة','Owner','Status'])
    angles=['Recognize the problem / المشكلة','One useful tip / نصيحة','Common mistake / خطأ شائع','FAQ / سؤال شائع','Demonstration / عرض','Offer contents / المحتويات','Listen to questions / استمع','Behind the process / الطريقة','A checklist / قائمة','Requirements / المتطلبات','A comparison / مقارنة','One detail / تفصيل','Scope limits / الحدود','Weekly recap / ملخص','Customer question / سؤال','Before-after demo / مثال','How to choose / الاختيار','Workflow step / خطوة','Fact check / تحقق','Delivery explained / التسليم','Ask for feedback / ملاحظات','Use case / استخدام','Troubleshooting / مشكلة','Cost clarity / تكلفة','Teach one skill / مهارة','Common misconception / تصور خاطئ','Product walkthrough / شرح','Answer objections / استفسار','What we learned / تعلّم','Next cycle / الدورة التالية']
    for i,a in enumerate(angles,1):cal.append([i,'',a,'','','','','','Draft'])
    dv=DataValidation(type='list',formula1='"Draft,Ready,Posted,Skipped"');cal.add_data_validation(dv);dv.add('I2:I31')
    metrics=w.create_sheet('Metrics');metrics.append(['Date','Campaign/post','Impressions','Clicks','Qualified inquiries','Orders','Revenue USD','Ad spend USD','CTR','Inquiry rate','Order/click rate','ROAS','Source / notes'])
    for r in range(2,32):
        metrics.append(['']*8+[f'=IF(OR(C{r}="",C{r}=0),"",D{r}/C{r})',f'=IF(OR(D{r}="",D{r}=0),"",E{r}/D{r})',f'=IF(OR(D{r}="",D{r}=0),"",F{r}/D{r})',f'=IF(OR(H{r}="",H{r}=0),"",G{r}/H{r})',''])
        for c in ['I','J','K']:metrics[f'{c}{r}'].number_format='0.0%'
        metrics[f'L{r}'].number_format='0.00"x"'
    nonneg=DataValidation(type='decimal',operator='greaterThanOrEqual',formula1='0',allow_blank=True);nonneg.error='Use zero or a positive number.';nonneg.errorTitle='Check measurement';nonneg.showErrorMessage=True;metrics.add_data_validation(nonneg);nonneg.add('C2:H31')
    exp=w.create_sheet('Experiments');exp.append(['Hypothesis / فرضية','One variable / متغير واحد','A','B','Metric / المقياس','Window / الفترة','Actual result / النتيجة','Uncertainty / حدود','Next action / التالي']);exp.append(['Clearer headline may improve relevant clicks','Headline','General message','Specific customer task','Qualified inquiries / clicks','Same duration; log audience differences','','',''])
    demo=w.create_sheet('Demo');demo.append(['FICTIONAL EXAMPLE','Value','Explanation']);
    for x in [('Impressions',1000,'Example only'),('Clicks',50,'Example only'),('Qualified inquiries',5,'Example only'),('Orders',2,'Example only'),('Revenue USD',18,'Two fictional USD 9 checklist orders'),('Ad spend USD',10,'Fictional measurement example, not a budget recommendation'),('CTR',0.05,'50 / 1000'),('Inquiry rate',0.10,'5 / 50'),('Order / click rate',0.04,'2 / 50'),('ROAS',1.8,'18 / 10; does not include costs, is not profit')]:demo.append(x)
    for s in w:
        s.freeze_panes='A2';s.auto_filter.ref=s.dimensions
        for c in s[1]:c.fill=PatternFill('solid',fgColor='153D4C');c.font=Font(color='FFFFFF',bold=True);c.alignment=Alignment(wrap_text=True)
        for row in s.iter_rows(min_row=2):
            for c in row:c.alignment=Alignment(wrap_text=True,vertical='top');c.font=Font(color='142B3A' if c.data_type=='f' else '1763A5',size=11)
        for col in s.columns:s.column_dimensions[col[0].column_letter].width=25
        s.row_dimensions[1].height=34
    start.column_dimensions['B'].width=95;brief.column_dimensions['B'].width=70;cal.column_dimensions['F'].width=55
    w.save(b/'02_CAMPAIGN_WORKBOOK.xlsx')

def slides(key,d):
    folder=ROOT/'work/video'/key;folder.mkdir(parents=True,exist_ok=True)
    font=lambda n,bold=False:ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),n)
    for i,s in enumerate(d['steps']):
        im=Image.new('RGB',(1280,720),'#0c2331');dr=ImageDraw.Draw(im)
        dr.rectangle((0,0,1280,12),fill='#36d0bc');dr.text((64,46),'JUST AI  /  '+d['name'].upper(),font=font(23,True),fill='#7de4d5')
        dr.text((64,104),f'{i+1:02d} / 06',font=font(24),fill='#a8bfcc')
        title=textwrap.wrap(s[0],39);y=155
        for line in title:dr.text((64,y),line,font=font(48,True),fill='white');y+=58
        y=max(y+45,320)
        for j,item in enumerate(s[3:5]):
            dr.rounded_rectangle((64,y-8,1216,y+93),radius=14,fill='#173f50')
            for k,line in enumerate(textwrap.wrap(item,64)):dr.text((86,y+10+k*34),line,font=font(28),fill='#f3f7f8')
            y+=124
        dr.text((64,653),'PAUSE • TRY THE STEP • CONTINUE     |     Fictional examples',font=font(20),fill='#abc9d5')
        for j in range(6):dr.rectangle((64+j*192,702,240+j*192,709),fill='#36d0bc' if j<=i else '#315362')
        im.save(folder/f'{i:02d}.png')
        write(folder/f'{i:02d}.txt',s[1])
    shutil.copy2(folder/'00.png',BUILD/key/'VIDEO_POSTER.png')

def services():
    services={
    'LOGO':('Logo & Brand Identity',129,['Exact business name and tagline','Audience and competitors to distinguish from','Three brand adjectives and preferred/avoided colours','Where the logo will be used and required languages','Existing assets you own and examples with context'],['Logo and agreed colour variations','Colour palette and typography direction','Compact brand guide','PNG and SVG final exports']),
    'WEBSITE':('One-Page Website',199,['Business name, audience and one page goal','Approved headings and body copy','Approved logo and images with usage rights','Call-to-action URLs and public contact details','Required languages, domain and hosting arrangements'],['Responsive one-page design and implementation','Approved content and call-to-action links','Desktop and mobile review','Handover with agreed hosting arrangement']),
    'SOCIAL':('Social Media Design Pack',69,['Business and campaign goal','Five approved post texts','Brand logo, colours and image permissions','Platform and dimensions for each post','Preferred direction and examples'],['Five coordinated custom post designs','Approved branding and content','Image exports in agreed dimensions']),
    'LAUNCH':('Business Launch Pack',329,['Business name, audience and launch goal','Brand direction and required languages','Website copy, images and call-to-action links','Five approved social post texts and dimensions','Domain/hosting arrangements and target date to discuss'],['Logo & Brand Identity service','Responsive one-page website service','Five coordinated social post designs','Agreed handover and acceptance review'])}
    for key,(name,price,fields,items) in services.items():
        b=BUILD/key;b.mkdir(exist_ok=True)
        brief='# '+name+' — project brief\n\nComplete in English or Arabic. Send only the information needed to scope the work. Do not include passwords, payment details or private customer data.\nيمكن تعبئة النموذج بالعربية أو الإنجليزية. لا ترسل كلمات مرور أو بيانات دفع أو معلومات عملاء خاصة.\n\n'
        for f in fields:brief+='## '+f+'\nYour answer / إجابتك:\n\n'
        brief+='## Agreement record / سجل الاتفاق\nScope: \nRevision allowance: \nFile formats and source handover: \nDelivery date: \nDependencies from customer: \nAdditional costs: \nWritten approval: \n\nLeave these fields open until agreed with JUST AI before purchase.\nاترك بنود الاتفاق مفتوحة حتى تأكيدها كتابياً قبل الشراء.\n'
        write(b/'01_PROJECT_BRIEF_EN_AR.md',brief)
        checklist='# Delivery acceptance checklist\n\nThis is an onboarding document, not the completed custom design.\nهذا ملف بدء المشروع وليس التصميم النهائي.\n\n'+''.join('- [ ] '+x+' matches the agreed brief.\n' for x in items)+'- [ ] Spelling, contact details, URLs and languages checked.\n- [ ] Files open in the agreed formats and dimensions.\n- [ ] Usage rights and any third-party costs documented.\n- [ ] Agreed revisions completed and handover accepted in writing.\n\nراجع الأسماء والروابط واللغات وصيغ الملفات والحقوق والتعديلات المتفق عليها قبل قبول التسليم.\n'
        write(b/'02_DELIVERY_CHECKLIST_EN_AR.md',checklist)
        body=f'<header><div class="eyebrow">JUST AI / SERVICE ONBOARDING</div><h1>{name}</h1><p>Current listed price: USD {price}. Final scope, revisions and schedule are agreed before purchase.</p></header><section><h2>What the service includes</h2><ul>'+''.join('<li>'+x+'</li>' for x in items)+'</ul><p>This download contains onboarding documents only. The custom deliverables are created after the brief and written scope agreement.</p><p lang="ar" dir="rtl">يضم هذا التنزيل ملفات بدء المشروع فقط. تُنفّذ المخرجات المخصصة بعد تحديد الموجز والاتفاق الكتابي على النطاق والتعديلات والموعد قبل الشراء.</p></section><section><h2>Start your project</h2><ol><li>Make a copy of <a href="01_PROJECT_BRIEF_EN_AR.md">the project brief</a>.</li><li>Fill it with approved text, public links and owned assets.</li><li>Email your brief and product name to <a href="mailto:ImSamtaha.ai@gmail.com">ImSamtaha.ai@gmail.com</a>.</li><li>Agree scope, formats, revisions, dependencies and delivery in writing before purchase.</li><li>Use <a href="02_DELIVERY_CHECKLIST_EN_AR.md">the delivery checklist</a> at handover.</li></ol><p lang="ar" dir="rtl">انسخ الموجز واملأه بمحتوى معتمد. أرسله للدعم مع اسم الخدمة واتفق كتابياً على التفاصيل قبل الشراء. استخدم قائمة المراجعة عند التسليم.</p></section><section><h2>Scope notes</h2><p>Domain, hosting, paid assets and external subscriptions are separate. No guaranteed revenue, advertising management, automated posting, e-commerce backend or trademark registration is included. Any expanded scope is quoted separately. Existing store service terms apply.</p></section>'
        write(b/'START_HERE.html',page(name,body))

if __name__=='__main__':
    marketing()
    for key,d in DATA.items():guide(key,d);slides(key,d)
    services()
    print('Created 4 toolkit guides, 24 tutorial slides, marketing workbook/resources and 4 service onboarding packs.')
