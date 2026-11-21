import json
N=json.load(open("narration.json")); D=json.load(open("durations.json"))
R="/home/user/WHD_ACMS/papercut_flow"
# camera END states (start is matched to each clip's last frame). zoom=[_,end]
cams=[
 ({"zoom":[1,1.22],"pan_x":[0,.3],"shake":2},{"mode":"pull_out","blur":9,"start":.72,"end":1},{"exposure":[1,1.08],"warmth":[0,.15],"vignette":.25,"sweep":{"strength":.22}},"zoom"),
 ({"zoom":[1,1.28],"pan_y":[0,-.4]},{"mode":"tiltshift","blur":10,"y":[.6,.4]},{"exposure":[1,1.1],"warmth":[0,.3],"vignette":.25},"crossfade"),
 ({"zoom":[1,1.3],"pan_x":[0,.35],"shake":2},{"mode":"pull_out","blur":9,"start":.75,"end":1},{"exposure":[1,1.1],"vignette":.25,"sweep":{"strength":.2}},"whip"),
 ({"zoom":[1,1.35],"pan_x":[0,.5]},{"mode":"tiltshift","blur":9,"y":[.45,.4]},{"exposure":[1,1.1],"warmth":[0,-.2],"vignette":.3},"crossfade"),
 ({"zoom":[1,1.4],"roll":[0,2],"pan_y":[0,-.2]},{"mode":"pull_out","blur":9,"start":.7,"end":1},{"exposure":[1,1.15],"sweep":{"strength":.25}},"flash"),
 ({"zoom":[1,1.28],"pan_x":[0,-.3],"shake":6},{"mode":"pull_out","blur":8,"start":.8,"end":1},{"exposure":[1,.9],"flicker":.07,"vignette":.35},"dip_black"),
 ({"zoom":[1,1.3],"pan_x":[0,-.4]},{"mode":"tiltshift","blur":9,"y":[.5,.45]},{"exposure":[1,1.05],"warmth":[0,.25],"vignette":.3},"whip"),
 ({"zoom":[1,1.3],"pan_y":[0,.6]},{"mode":"tiltshift","blur":10,"y":[.3,.7],"band":.2},{"exposure":[1,1.05],"vignette":.3},"crossfade"),
 ({"zoom":[1,1.3],"roll":[0,-2]},{"mode":"pull_out","blur":9,"start":.75,"end":1},{"exposure":[1,1.1],"warmth":[0,.2],"vignette":.25},"crossfade"),
 ({"zoom":[1,1.25],"pan_y":[0,-.2]},None,{"exposure":[1,.55],"vignette":.3},None)]
TR=.7; LEAD=.35; shots=[]
for i,(c,f,l,tr) in enumerate(cams):
    dur=D[i]+LEAD+.6+(TR if tr else 0)
    s={"image":f"{R}/{i+1:02d}.jpg","intro_clip":f"{R}/clips/{i+1:02d}.mp4","duration":round(dur,3),
       "camera":c,"light":l,"caption":{"text":N[i][1],"y":.8,"size":.04}}
    if f: s["focus"]=f
    if tr: s["transition"]={"type":tr,"duration":TR if tr!="flash" else .5}
    shots.append(s)
json.dump({"size":[1080,1920],"fps":30,"audio":"mix.m4a","shots":shots},open("storyboard_flow.json","w"),indent=1)
# 2-shot test
t=dict(json.load(open("storyboard_flow.json"))); t["shots"]=shots[:2]; t["audio"]=None; t["size"]=[540,960]
json.dump(t,open("test_flow.json","w"))
