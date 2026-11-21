---
name: cinematic-image-animation
description: Use when asked to make a short vertical video, reel or "real animation" look from AI-generated still images (e.g. Google Flow / ImageFX / Whisk free image generation) using camera pan, zoom, focus shifts, lighting changes and transitions, or to recreate the style of an Instagram reel built from animated stills.
---

# Cinematic Image Animation

Make a reel-style video from still images: each image gets a virtual camera
(zoom/pan/roll/handheld shake), a focus pull, a lighting shift, and a
transition into the next shot. No video-gen model needed.

**Core principle:** motion must have *motivation*. Every shot = one camera move + one focus or light change that points the eye at the subject. Moves are eased, never linear.

## Workflow

1. **Storyboard first.** 5-10 shots, 3-5 s each (8-12 s hooks for reels: first shot ≤2.5 s). One sentence per shot: subject, camera move, focus/light change, transition.
2. **Generate images in Google Flow (free).** Open labs.google/fx/tools/flow (or Whisk/ImageFX), aspect **9:16**, follow [references/flow-prompts.md](references/flow-prompts.md) for style-locked prompts. Download at the highest resolution (≥1080x1920). Name them `01.png, 02.png...`. This step is manual: Flow has no public API and needs the user's Google login; ask the user to upload the images into the working directory.
   - If the user has no images yet, hand them the numbered prompt list and stop; do not substitute placeholder art.
3. **Write `storyboard.json`** (schema below; working example: `references/example-storyboard.json`).
4. **Render:** `python3 scripts/animate.py storyboard.json out.mp4` (needs Pillow, numpy, ffmpeg; ~10 fps rendering at 540x960, set `size` to `[1080,1920]` for final).
5. **Review frames,** not just the file: `ffmpeg -ss 1.5 -i out.mp4 -frames:v 1 f.png`. Check edges never show, blur isn't muddy, moves are readable. Adjust and re-render.
6. **Narration (edge-tts):** `pip install edge-tts`; per scene `edge_tts.Communicate(text, "en-US-AndrewNeural", rate="-4%", proxy=os.environ.get("HTTPS_PROXY")).save("NN.mp3")` (the explicit `proxy=` is required in sandboxes; host `speech.platform.bing.com` must be allowed). Measure each clip with ffprobe, set `duration = audio + ~1.0 s (+ transition)`, then place clips with ffmpeg `adelay` at each shot's start (start_i = sum of earlier durations minus their transition overlaps) and mix to one file.
7. Optional: add music with `"audio": "track.mp3"` (trimmed to video length).

## Storyboard schema

```json
{"size":[1080,1920],"fps":30,"audio":"optional.mp3","shots":[{
  "image":"01.png","duration":4,
  "camera":{"zoom":[1,1.25],"pan_x":[-0.5,0.5],"pan_y":[0,0],"roll":[0,1.5],"shake":3,"ease":"inout"},
  "focus":{"mode":"pull_in|pull_out|tiltshift","blur":14,"start":0,"end":0.6,"y":[0.3,0.7]},
  "light":{"exposure":[0.7,1.1],"warmth":[-0.5,0.6],"vignette":0.4,"flicker":0.03,
           "sweep":{"width":0.15,"strength":0.35,"slant":0.4}},
  "grain":0.03,
  "caption":{"text":"On-screen line","y":0.8,"size":0.042},
  "transition":{"type":"crossfade|whip|zoom|flash|dip_black","duration":0.8}}]}
```
`pan_x/pan_y` are -1..1 of available headroom (images get 1.6x headroom). `transition` on a shot joins it to the *next* shot; frames overlap, so duration is subtracted from total length.

## Recipe table (look → settings)

| Feeling | Camera | Focus | Light | Transition |
|---|---|---|---|---|
| Reveal / establishing | zoom 1→1.2, slow pan_x | `pull_in` blur 16 | exposure 0.6→1.1, sweep | crossfade |
| Intimate / emotion | zoom 1→1.4 (push-in), no pan | `pull_in` on subject | warmth 0→0.5, vignette 0.5 | dip_black |
| Action / energy | zoom 1.3→1, pan_x ±0.8, shake 5 | none | flash, flicker 0.05 | whip or flash |
| Depth / miniature | pan_y slow, roll ±1.5 | `tiltshift` y moving | vignette 0.4 | zoom |
| Ending / fade | zoom out 1.3→1 | `pull_out` late | exposure 1→0.5 | dip_black |

## Rules that make it read as "real animation"

- Alternate directions shot to shot (push in, then pull out/pan opposite); same move repeated looks like a slideshow.
- Camera moves at 1-2% scale/second feel natural; faster needs a whip or flash to justify it.
- Pair a whip/flash transition with the *end* of a move and the next shot starting moving immediately (momentum carry-over).
- Keep grain 0.02-0.04 and a small `shake` (2-4) for filmic life; skip shake on close-ups where it reads as jitter.
- Keep style/character tokens identical across all Flow prompts, or the cuts will look like different films.

## Common mistakes

- Zoom beyond ~1.5x on a 1080p source: soft. Generate at max Flow resolution or lower the zoom.
- Blur > 20 with `pull_in` looks like an encoding glitch; use 10-16.
- Forgetting the last shot's `transition` is harmless (ignored); forgetting to ask for images is not: don't invent images.
