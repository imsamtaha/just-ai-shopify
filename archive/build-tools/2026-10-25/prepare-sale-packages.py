from pathlib import Path, PurePosixPath
import json,zipfile,hashlib,re,subprocess,shutil
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parent.parent
SOURCE=Path(r'<LOCAL_HOME>\Documents\Codex\2026-10-29\plugin-creator-plugin-plugin-connector-1p-5\outputs\product-packages')
OUT=ROOT/'outputs/sale-packages-2026-11-01'
OUT.mkdir(exist_ok=True)
audit=[]
for p in sorted(SOURCE.glob('*.zip')):
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        data={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
        manifest=json.loads(data['MANIFEST.json'])
        assert set(manifest)==set(data)-{'MANIFEST.json'}
        assert all(hashlib.sha256(data[n]).hexdigest()==v['sha256'] and len(data[n])==v['bytes'] for n,v in manifest.items())
        assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and ':' not in n for n in data)
        for name,value in data.items():
            if name.endswith('.html'):
                for link in re.findall(r'(?:href|src)=[\"\x27]([^\"\x27]+)',value.decode('utf-8')):
                    if ':' not in link and not link.startswith('#'):
                        target=str(PurePosixPath(name).parent / unquote(link.split('#')[0]))
                        assert target in data,(p.name,name,link)
        service='HOW_TO.mp4' not in data
        changed=[]
        if service:
            html=data['START_HERE.html'].decode('utf-8')
            html,count=re.subn(r'Current listed price: USD [0-9]+\.', 'Use the current product-page and checkout price.',html)
            assert count==1
            data['START_HERE.html']=html.encode('utf-8')
            changed=['Removed copied service price; current storefront price applies']
            data['MANIFEST.json']=json.dumps({n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in data.items() if n!='MANIFEST.json'},indent=2).encode('utf-8')
        output=OUT/(p.name.replace('_v2.zip','_v2_1.zip') if service else p.name)
        if service:
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
                for name,value in data.items():z.writestr(name,value)
        else:shutil.copy2(p,output)
        media=None
        if not service:
            video=ROOT/'work'/('validate-'+p.stem+'.mp4')
            video.write_bytes(data['HOW_TO.mp4'])
            probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height','-of','json',str(video)],capture_output=True,check=True)
            media=json.loads(probe.stdout)
            assert {s['codec_type'] for s in media['streams']} >= {'video','audio'}
            subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],capture_output=True,check=True)
        audit.append({'file':output.name,'path':str(output),'bytes':output.stat().st_size,'files':len(data),'type':'service onboarding only' if service else 'digital toolkit','changes':changed,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'zip_crc':'pass','manifest':'pass','relative_links':'pass','media':media})
(OUT/'PACKAGE-VALIDATION.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'file':a['file'],'type':a['type'],'files':a['files'],'duration':a['media']['format']['duration'] if a['media'] else None,'checks':'passed'} for a in audit]))
