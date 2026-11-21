"""Dynamic-programming beat tracker (Ellis 2007) + downbeat/bar grouping. Writes beats.json."""
import numpy as np, json
oenv=np.load("oenv.npy"); olow=np.load("olow.npy"); fps=22050/256
o=np.maximum(0,oenv+0.7*olow); o=np.convolve(o,np.hanning(5)/np.hanning(5).sum(),'same')
def track(period, tight=80.0):
    n=len(o); score=o.copy(); back=-np.ones(n,int)
    w=int(period*2)
    for i in range(n):
        lo=max(0,i-int(period*1.6)); hi=i-int(period*0.6)
        if hi<=lo: continue
        j=np.arange(lo,hi); pen=-tight*(np.log((i-j)/period))**2
        k=np.argmax(score[j]+pen); score[i]=o[i]+score[j][k]+pen[k]; back[i]=j[k]
    end=int(np.argmax(score[-int(period*2):]))+n-int(period*2); beats=[end]
    while back[beats[-1]]>=0: beats.append(back[beats[-1]])
    return np.array(beats[::-1])/fps, score[end]
bestp=None
for bpm in (80,81,82,83,84):
    b,s=track(60*fps/bpm); print(bpm,"score",round(float(s),1),"n",len(b),"median IBI->bpm",round(60/np.median(np.diff(b)),2))
    if bestp is None or s>bestp[0]: bestp=(s,b)
b=bestp[1]; ibi=np.diff(b); print("IBI sec: min %.3f p10 %.3f med %.3f p90 %.3f max %.3f"%(ibi.min(),np.percentile(ibi,10),np.median(ibi),np.percentile(ibi,90),ibi.max()))
# downbeat: pick bar offset (0-3) maximizing low-band flux on beat 1 over chorus regions
bl=[olow[int(t*fps)] for t in b]; bl=np.array(bl)
acc=[bl[k::4].mean() for k in range(4)]; print("low flux per beat offset",np.round(acc,2))
off=int(np.argmax(acc)); bars=b[off::4]
json.dump({"beats":[round(float(t),3) for t in b],"bars":[round(float(t),3) for t in bars],"bar_offset":off},open("beats.json","w"))
print("bars:",len(bars),"first bars",np.round(bars[:6],2),"median bar",round(float(np.median(np.diff(bars))),3))
