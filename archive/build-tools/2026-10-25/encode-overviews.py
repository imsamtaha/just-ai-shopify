from pathlib import Path
import json,subprocess
root=Path(__file__).resolve().parent
out=root.parent/'outputs'
for key in ['PRO','CONTENT-SPRINT']:
    folder=root/(key+'-video')
    scenes=json.loads((folder/'scenes.json').read_text())
    clips=[]
    for scene in scenes:
        dest=folder/(scene['name']+'.mp4')
        duration=scene['duration']
        filters=f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.3,fade=t=out:st={duration-0.3}:d=0.3"
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(folder/(scene['name']+'.png')),'-t',str(duration),'-vf',filters,'-c:v','libx264','-preset','fast','-crf','20','-threads','4',str(dest)],check=True)
        clips.append(dest)
        print(key+' '+scene['name'],flush=True)
    listing=folder/'clips.txt'
    listing.write_text('\n'.join("file '"+p.as_posix()+"'" for p in clips),encoding='utf-8')
    dest=out/f'JUST-AI-{key}-product-overview.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(dest)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(dest),'-f','null','-'],check=True)
    info=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,pix_fmt,r_frame_rate','-of','json',str(dest)],text=True)
    (folder/'validation.json').write_text(info)
    print(info,flush=True)
