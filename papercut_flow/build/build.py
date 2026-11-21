import json, subprocess
N=json.load(open("narration.json")); D=json.load(open("durations.json"))
cams=[ # (camera, focus, light, transition)
 ({"zoom":[1,1.3],"pan_x":[-.3,.3],"shake":2},{"mode":"pull_in","blur":16,"end":.5},{"exposure":[.6,1.05],"warmth":[-.3,.2],"vignette":.45,"sweep":{}},"zoom"),
 ({"zoom":[1.35,1],"pan_y":[.6,-.2]},{"mode":"tiltshift","blur":10,"y":[.65,.3]},{"exposure":[.8,1.1],"warmth":[0,.6],"vignette":.4},"crossfade"),
 ({"zoom":[1,1.35],"pan_x":[-.7,.7],"shake":2},{"mode":"pull_in","blur":12,"end":.4},{"exposure":[.8,1.1],"vignette":.4,"sweep":{"strength":.25}},"whip"),
 ({"zoom":[1.1,1.45],"pan_x":[.3,-.2]},{"mode":"pull_in","blur":14,"end":.5},{"exposure":[.7,1.1],"warmth":[-.4,.3],"vignette":.45},"crossfade"),
 ({"zoom":[1.4,1],"pan_x":[.5,-.5],"roll":[-2,2]},{"mode":"pull_out","blur":10,"start":.6,"end":1},{"exposure":[.9,1.15],"sweep":{"strength":.3}},"flash"),
 ({"zoom":[1,1.3],"pan_x":[.6,-.6],"shake":7},{"mode":"pull_in","blur":10,"end":.3},{"exposure":[1,.85],"flicker":.07,"vignette":.5},"dip_black"),
 ({"zoom":[1,1.4],"pan_y":[-.5,.5]},{"mode":"tiltshift","blur":12,"y":[.3,.6]},{"exposure":[.8,1],"warmth":[0,-.4],"vignette":.4},"whip"),
 ({"zoom":[1.4,1],"pan_y":[.5,-.5],"roll":[1.5,-1.5]},{"mode":"tiltshift","blur":10,"y":[.5,.5],"band":.2},{"exposure":[.8,1.1],"vignette":.4,"sweep":{}},"crossfade"),
 ({"zoom":[1,1.35],"roll":[-2,2],"pan_x":[0,0]},{"mode":"pull_in","blur":14,"end":.4},{"exposure":[.7,1.1],"warmth":[-.2,.3],"vignette":.35},"crossfade"),
 ({"zoom":[1.4,1],"pan_y":[-.3,.2]},{"mode":"pull_in","blur":14,"end":.45},{"exposure":[.6,1.1],"warmth":[0,.7],"vignette":.4,"sweep":{"strength":.3}},None)]
TR=.7; LEAD=.35; shots=[]; starts=[]; t=0
for i,(c,f,l,tr) in enumerate(cams):
    dur=D[i]+LEAD+.6+(TR if tr else 0)
    s={"image":f"img/{i+1:02d}.png","duration":round(dur,3),"camera":c,"focus":f,"light":l,"grain":.025,
       "caption":{"text":N[i][1],"y":.8,"size":.042}}
    if tr: s["transition"]={"type":tr,"duration":TR if tr!="flash" else .5}
    shots.append(s); starts.append(t); t+=dur-(s.get("transition",{}).get("duration",0))
json.dump({"size":[720,1280],"fps":24,"audio":"mix.m4a","shots":shots},open("storyboard.json","w"),indent=1)
total=t; print("total",total)
cmd=["ffmpeg","-y","-loglevel","error"]
for i in range(len(N)): cmd+=["-i",f"aud/{i:02d}.mp3"]
cmd+=["-f","lavfi","-i",f"aevalsrc='0.5*sin(2*PI*110*t)+0.35*sin(2*PI*164.8*t)+0.25*sin(2*PI*220.5*t)*sin(2*PI*0.2*t)':d={total+1}:s=44100"]
f=[f"[{i}:a]adelay={int((starts[i]+LEAD)*1000)}|{int((starts[i]+LEAD)*1000)},volume=1.6[v{i}]" for i in range(len(N))]
f.append(f"[{len(N)}:a]volume=0.05,afade=t=in:d=2,afade=t=out:st={total-3}:d=3[pad]")
f.append("".join(f"[v{i}]" for i in range(len(N)))+"[pad]amix=inputs=%d:normalize=0:duration=longest,atrim=0:%.2f[m]"%(len(N)+1,total))
cmd+=["-filter_complex",";".join(f),"-map","[m]","-c:a","aac","-b:a","160k","mix.m4a"]
subprocess.check_call(cmd); print("audio ok")
