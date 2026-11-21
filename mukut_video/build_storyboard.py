"""Build the timed storyboard: shots land on detected bars, pulses/flashes follow the music.
Usage: python3 build_storyboard.py IMG_DIR OUT.json [--w 1920 --h 1080 --fps 30] """
import json, sys, math
img_dir, out = sys.argv[1], sys.argv[2]
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
W, H, FPS = arg("--w", 1920), arg("--h", 1080), arg("--fps", 30)
bt = json.load(open("beats.json")); BARS, BEATS = bt["bars"], bt["beats"]; END = 248.4
caps = json.load(open("captions.json"))
def T(bar): return 0.0 if bar <= 0 else (BARS[bar] if bar < len(BARS) else END)

# camera views: zoom [start,end], pan in slack fractions
V = {
 "wide":   {"zoom": [1.0, 1.12]},
 "pullC":  {"zoom": [1.45, 1.05]},
 "pushC":  {"zoom": [1.05, 1.5]},
 "pushL":  {"zoom": [1.2, 1.65], "pan_x": [-.3, -.85]},
 "pushR":  {"zoom": [1.2, 1.65], "pan_x": [.3, .85]},
 "drift":  {"zoom": [1.3, 1.35], "pan_x": [-.8, .8]},
 "riseUp": {"zoom": [1.35, 1.5], "pan_y": [.8, -.8]},
 "sink":   {"zoom": [1.35, 1.5], "pan_y": [-.8, .8]},
 "slow":   {"zoom": [1.0, 1.2]},
}
# (start_bar, end_bar, image, view, transition into NEXT shot (type, seconds), light)
S = [
 # intro: rain, crown, lamp, car   (bars 0-8)
 (0, 3, "a1", "pullC", ("crossfade", .9)), (3, 6, "a2", "riseUp", ("crossfade", .9)), (6, 8, "a3", "slow", ("crossfade", .6)),
 # verse 1 (8-18): 2-bar cuts
 (8, 10, "a3", "pushL", ("crossfade", .4)), (10, 12, "a4", "wide", ("crossfade", .4)), (12, 14, "a5", "drift", ("crossfade", .4)),
 (14, 16, "a4", "pushC", ("crossfade", .4)), (16, 18, "a5", "pushR", ("crossfade", .9)),
 # pre-chorus (18-25): the light rises
 (18, 21, "a6", "pushC", ("crossfade", .8)), (21, 23, "a7", "riseUp", ("crossfade", .5)), (23, 25, "a7", "pushC", ("flash", .3)),
 # chorus (25-35)
 (25, 27, "a8", "pullC", ("cut", 0)), (27, 29, "a9", "drift", ("cut", 0)), (29, 31, "a8", "pushL", ("cut", 0)),
 (31, 33, "a10", "wide", ("cut", 0)), (33, 35, "a9", "pushR", ("crossfade", .6)),
 # verse 2 (35-51): sparse 4 bars then heavy
 (35, 37, "a11", "pushL", ("crossfade", .8)), (37, 39, "a12", "pullC", ("whip", .35)), (39, 41, "a11", "pushR", ("whip", .35)),
 (41, 43, "a13", "pushC", ("whip", .35)), (43, 45, "a12", "drift", ("whip", .35)), (45, 47, "a13", "pushL", ("whip", .35)),
 (47, 49, "a11", "pullC", ("whip", .35)), (49, 51, "a12", "pushR", ("crossfade", 1.0)),
 # bridge (51-60) + heartbeat pause at bar 58
 (51, 54, "a14", "pullC", ("crossfade", 1.0)), (54, 57, "a15", "pushC", ("dip_black", 1.4)), (57, 58, "a15", "pushR", ("crossfade", .8)),
 (58, 60, "a16", "slow", ("flash", .3)),
 # final chorus (60-79)
 (60, 62, "a17", "pullC", ("cut", 0)), (62, 64, "a8", "pushC", ("cut", 0)), (64, 66, "a9", "pushL", ("cut", 0)),
 (66, 68, "a17", "pushR", ("cut", 0)), (68, 70, "a10", "drift", ("cut", 0)), (70, 72, "a8", "pullC", ("cut", 0)),
 (72, 74, "a9", "pushR", ("cut", 0)), (74, 76, "a17", "pushC", ("crossfade", .8)), (76, 79, "a18", "riseUp", ("crossfade", 1.2)),
 # outro (79-end)
 (79, 81, "a18", "pullC", ("crossfade", 1.2)), (81, 84, "a1", "pushC", None),
]
shots = []
for i, (b0, b1, img, view, tr) in enumerate(S):
    t0 = T(b0); t1 = T(b1) if i + 1 < len(S) else END
    s = {"image": f"{img_dir}/{img}.png", "t0": round(t0, 3), "t1": round(t1, 3), "camera": dict(V[view], ease="inout"),
         "light": {"vignette": .35}, "grain": 0}
    if tr: s["transition"] = {"type": tr[0], "duration": tr[1]}
    shots.append(s)
shots[0]["t0"] = 0.0
# ---- pulses: every bar (strong), every beat (soft) by section energy
sec = [(0, 8, .008, 0), (8, 18, .012, .004), (18, 25, .012, .004), (25, 35, .03, .012), (35, 51, .022, .008),
       (51, 60, .008, 0), (60, 79, .034, .014), (79, 84, .01, 0)]
pulses = []
def amp(t):
    for b0, b1, a, ab in sec:
        if T(b0) <= t < T(b1): return a, ab
    return 0, 0
bars_set = set(round(x, 2) for x in BARS)
for t in BEATS:
    a, ab = amp(t)
    if round(t, 2) in bars_set:
        if a: pulses.append([round(t, 3), a])
    elif ab: pulses.append([round(t, 3), ab])
# ---- flashes
fl = []
for t in (3.1, 7.5, 15.9, 17.5): fl.append({"t": t, "strength": .28, "decay": .10, "color": [.8, .9, 1]})   # thunder
fl.append({"t": 10.55, "strength": .55, "decay": .16, "color": [.85, .92, 1]})
fl.append({"t": round(T(25), 2), "strength": .55, "decay": .22, "color": [1, .85, .5]})            # chorus drop
fl.append({"t": round(T(60), 2), "strength": .4, "decay": .2, "color": [1, .8, .5]})
fl.append({"t": round(T(62), 2), "strength": .6, "decay": .25, "color": [1, .85, .55]})           # final chorus
for t in (168.34, 170.31, 171.91, 174.3): fl.append({"t": t, "strength": .35, "decay": .22, "color": [1, .1, .12]})  # heartbeat
fl += [{"t": 236.39, "strength": .35, "decay": .3, "color": [1, .9, .7]}, {"t": 242.25, "strength": .7, "decay": .45, "color": [1, .9, .7]}]
exposure = [[0, 0], [2.0, 1], [150, 1], [153, .88], [168, .88], [170.5, .5], [174.6, .5], [177.0, 1], [244, 1], [247.6, 0], [248.4, 0]]
sb = {"timed": True, "size": [W, H], "fps": FPS, "audio": "/tmp/t/in.wav", "shots": shots,
      "overlays": {"pulses": pulses, "flashes": fl, "exposure": exposure, "captions": caps,
                   "font_bn": "/usr/share/fonts/truetype/freefont/FreeSans.ttf", "font_en": "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                   "size_bn": .056, "size_en": .032, "y": .79}}
json.dump(sb, open(out, "w"), ensure_ascii=False)
print(len(shots), "shots,", len(pulses), "pulses,", len(fl), "flashes; total", shots[-1]["t1"])
