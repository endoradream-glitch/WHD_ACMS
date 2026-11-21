import asyncio, edge_tts, json, os, subprocess
N=json.load(open("narration.json"))
async def one(i,t):
    await edge_tts.Communicate(t,"en-US-AndrewNeural",rate="-4%",proxy=os.environ.get("HTTPS_PROXY")).save(f"aud/{i:02d}.mp3")
async def main():
    for i,(t,_) in enumerate(N): await one(i,t)
asyncio.run(main())
d=[float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"aud/{i:02d}.mp3"])) for i in range(len(N))]
json.dump(d,open("durations.json","w")); print(d, sum(d))
