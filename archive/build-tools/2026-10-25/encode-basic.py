from pathlib import Path
import json,subprocess,shutil
root=Path(__file__).resolve().parent
out=root.parent/'outputs'
scenes=json.loads((root/'scenes.json').read_text())
clips=[]
for scene in scenes:
    dest=root/(scene['name']+'.mp4')
    duration=scene['duration']
    filters=f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.25,fade=t=out:st={duration-0.25}:d=0.25"
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(root/(scene['name']+'.png')),'-t',str(duration),'-vf',filters,'-c:v','libx264','-preset','fast','-crf','20','-threads','4',str(dest)],check=True)
    clips.append(dest)
    print('Encoded '+scene['name'],flush=True)
listing=root/'basic-clips.txt'
listing.write_text('\n'.join("file '"+p.as_posix()+"'" for p in clips),encoding='utf-8')
dest=out/'JUST-AI-BASIC-template-showcase.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(dest)],check=True)
shutil.copy2(root/'01-cover.png',out/'JUST-AI-BASIC-video-poster.png')
info=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,pix_fmt,r_frame_rate','-of','json',str(dest)],text=True)
(root/'basic-video-validation.json').write_text(info,encoding='utf-8')
print(info,flush=True)
