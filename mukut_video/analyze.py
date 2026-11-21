"""Beat grid + section/event detection for the song. Writes timeline.json."""
import numpy as np, json, subprocess, sys
src = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else "timeline.json"
sr = 22050; hop = 256
raw = subprocess.check_output(["ffmpeg","-loglevel","error","-i",src,"-ac","1","-ar",str(sr),"-f","f32le","-"])
x = np.frombuffer(raw, np.float32); dur = len(x)/sr
W = 1024
fr = np.lib.stride_tricks.sliding_window_view(x, W)[::hop]*np.hanning(W)
S = np.abs(np.fft.rfft(fr, axis=1)); f = np.fft.rfftfreq(W, 1/sr); t = np.arange(len(S))*hop/sr; fps = sr/hop
def band(a, b): m = (f >= a) & (f < b); return (S[:, m]**2).sum(1)
def flux(a, b):
    L = np.log1p(30*S[:, (f >= a) & (f < b)]); o = np.r_[0, np.maximum(0, np.diff(L, axis=0)).sum(1)]
    return (o-o.mean())/(o.std()+1e-9)
oenv = flux(30, 9000); olow = flux(30, 160)
# ---- tempo/phase: comb scan
best = (-1e9, 0, 0)
for bpm in np.arange(70, 170.01, 0.05):
    period = 60*fps/bpm
    for ph in np.arange(0, period, 2):
        idx = (ph + np.arange(0, len(oenv)-period-1, period)).astype(int)
        sc = oenv[idx].sum() + 0.7*olow[idx].sum()
        if sc > best[0]: best = (sc, bpm, ph)
print("global best bpm", round(best[1],2), "phase s", round(best[2]/fps,3))
# restrict to the 75-90 family and report stability per quarter
def score(bpm, ph, a, b):
    period = 60*fps/bpm; idx = (ph + np.arange(a*fps, b*fps, period)).astype(int); idx = idx[idx < len(oenv)]
    return (oenv[idx]+0.7*olow[idx]).mean()
res = {}
for bpm in np.arange(76, 90.01, 0.05):
    period = 60*fps/bpm; bs = (-1e9, 0)
    for ph in np.arange(0, period, 1):
        idx = (ph + np.arange(0, len(oenv)-period-1, period)).astype(int)
        sc = (oenv[idx]+0.7*olow[idx]).mean()
        if sc > bs[0]: bs = (sc, ph)
    res[round(float(bpm),2)] = bs
bpm0 = max(res, key=lambda k: res[k][0]); ph0 = res[bpm0][1]
print("best in 76-90:", bpm0, "score", round(res[bpm0][0],3), "phase", round(ph0/fps,3))
for a, b in ((0,60),(60,120),(120,180),(180,240)):
    print(f"  {a}-{b}s score at grid:", round(score(bpm0, ph0, a, b),3))
json.dump({"bpm": bpm0, "phase": float(ph0/fps), "dur": float(dur)}, open(out+".tmp","w"))
np.save("oenv.npy", oenv); np.save("olow.npy", olow)
