from pathlib import Path
import subprocess,json,wave,zipfile,hashlib,shutil,concurrent.futures
ROOT=Path(__file__).resolve().parent.parent
DATA=json.loads((ROOT/'work/kit-content.json').read_text(encoding='utf-8'))
def run(args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def timestamp(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'
def render(key):
    d=DATA[key];v=ROOT/'work/video'/key;b=ROOT/'work/packages'/key
    elapsed=0;vtt='WEBVTT\n\n';files=[]
    for i,s in enumerate(d['steps']):
        wav=v/f'{i:02d}.wav'
        with wave.open(str(wav)) as w:duration=w.getnframes()/w.getframerate()+1.2
        target=v/f'{i:02d}.mp4'
        run(['ffmpeg','-y','-loglevel','error','-loop','1','-framerate','6','-i',str(v/f'{i:02d}.png'),'-i',str(wav),'-t',str(duration),'-c:v','libx264','-preset','fast','-tune','stillimage','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-af','apad','-r','12','-threads','2',str(target)])
        files.append(target)
        sentences=s[1].split('. ');part=duration/len(sentences)
        for j,line in enumerate(sentences):vtt+=f'{timestamp(elapsed+j*part)} --> {timestamp(elapsed+(j+1)*part)}\n{line.strip()}\n\n'
        elapsed+=duration
    concat=v/'concat.txt';concat.write_text('\n'.join("file '"+p.as_posix()+"'" for p in files),encoding='utf-8')
    run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(b/'HOW_TO.mp4')])
    (b/'CAPTIONS_EN.vtt').write_text(vtt,encoding='utf-8')
    # Decoder check catches broken output; duration and stream metadata are saved separately.
    run(['ffmpeg','-v','error','-i',str(b/'HOW_TO.mp4'),'-f','null','-'])
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height','-of','json',str(b/'HOW_TO.mp4')]))
    assert any(x['codec_type']=='audio' for x in info['streams'])
    assert any(x.get('width')==1280 and x.get('height')==720 for x in info['streams'])
    print(key,round(float(info['format']['duration']),1),'seconds',flush=True)
    shutil.copy2(b/'HOW_TO.mp4',ROOT/'outputs/product-packages'/f'JUST_AI_{key}_HOW_TO.mp4')
    return key,info
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(render,DATA))
    (ROOT/'work/video-validation.json').write_text(json.dumps(results,indent=2))
    for b in (ROOT/'work/packages').iterdir():
        if not b.is_dir():continue
        manifest={p.relative_to(b).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(b.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
        (b/'MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        target=ROOT/'outputs/product-packages'/f'JUST_AI_{b.name}_COMPLETE_v2.zip'
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
            for p in b.rglob('*'):
                if p.is_file():z.write(p,p.relative_to(b))
        with zipfile.ZipFile(target) as z:assert z.testzip() is None
        print(target.name,'PASS',len(manifest)+1,'files',target.stat().st_size,flush=True)
