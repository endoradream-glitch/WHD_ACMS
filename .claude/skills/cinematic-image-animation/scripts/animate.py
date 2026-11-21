#!/usr/bin/env python3
"""Turn still images into a cinematic animated video: camera pan/zoom/roll/shake,
rack focus, lighting shifts, captions, transitions, optional per-shot intro clips.

Usage: python3 animate.py storyboard.json out.mp4 [--workers N]
Needs: Pillow, numpy, ffmpeg. See SKILL.md for the storyboard schema.
Frames are rendered in parallel chunks (one ffmpeg encoder per worker) and joined."""
import json, subprocess, sys, math, os, zlib, glob, shutil
import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
from concurrent.futures import ProcessPoolExecutor

SS = 1.6  # supersample factor of the working image (sharper zooms)


def ease(t, kind="inout"):
    t = min(max(t, 0.0), 1.0)
    if kind == "linear": return t
    if kind == "out": return 1 - (1 - t) ** 3
    if kind == "in": return t ** 3
    return t * t * (3 - 2 * t)


def lerp(a, b, t): return a + (b - a) * t


_GRID = {}
def grid(W, H):
    if (W, H) not in _GRID:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        _GRID[(W, H)] = (xx / W, yy / H)
    return _GRID[(W, H)]


def cover(im, W, H):
    s = max(W / im.width, H / im.height)
    return im.resize((max(W, round(im.width * s)), max(H, round(im.height * s))), Image.LANCZOS)


def match_clip(still_path, last_frame, W, H):
    """Find zoom s and centre shift (dx,dy; cover-fit px) that make the still look like the
    clip's final frame, so the still can continue seamlessly from where the clip stops."""
    A = cover(Image.open(still_path).convert("RGB"), W, H)
    f = 135 / W; w, h = 135, round(H * f)
    As = A.resize((max(1, round(A.width * f)), max(1, round(A.height * f))), Image.BILINEAR)
    tgt = np.asarray(Image.open(last_frame).convert("L").resize((w, h), Image.BILINEAR), np.float32)

    def err(s, dx, dy):
        vw, vh = w / s, h / s; cx, cy = As.width / 2 + dx, As.height / 2 + dy
        im = As.transform((w, h), Image.EXTENT, (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2),
                          Image.BILINEAR).convert("L")
        return float(np.abs(np.asarray(im, np.float32) - tgt).mean())
    best = (1e18, 1.0, 0, 0)
    for s in np.arange(0.97, 1.45, 0.01):
        for dx in range(-14, 15, 2):
            for dy in range(-14, 15, 2):
                e = err(s, dx, dy)
                if e < best[0]: best = (e, s, dx, dy)
    _, s0, dx0, dy0 = best
    for s in np.arange(s0 - .012, s0 + .0121, .003):
        for dx in np.arange(dx0 - 2, dx0 + 2.1, .5):
            for dy in np.arange(dy0 - 2, dy0 + 2.1, .5):
                e = err(s, dx, dy)
                if e < best[0]: best = (e, s, dx, dy)
    e, s, dx, dy = best
    return {"zoom": float(s), "dx": float(dx / f), "dy": float(dy / f), "err": round(e, 1)}


class Shot:
    def __init__(self, d, W, H, fps, base):
        self.d, self.W, self.H = d, W, H
        self.dur = float(d.get("duration", 4))
        self.n = max(2, round(self.dur * fps))
        self.path = d["image"] if os.path.isabs(d["image"]) else os.path.join(base, d["image"])
        self._img = None
        self.cam = d.get("camera", {})
        self.ease = self.cam.get("ease", "inout")
        self.seed = zlib.crc32(d["image"].encode()) % 1000
        self.clipdir = d.get("_clipdir")
        self.clip_n = len(glob.glob(os.path.join(self.clipdir, "*.jpg"))) if self.clipdir else 0
        self.clip_n = min(self.clip_n, self.n - 2)
        self.match = d.get("_match")
        self.blend_n = int(d.get("clip_blend", 0.35) * fps) if self.clip_n else 0
        self._last = None

    @property
    def img(self):
        if self._img is None:  # headroom image: cover-fit, supersampled
            im = Image.open(self.path).convert("RGB")
            A = cover(im, self.W, self.H)
            self._img = A.resize((round(A.width * SS), round(A.height * SS)), Image.LANCZOS)
        return self._img

    # ---- frame ------------------------------------------------------------------
    def frame(self, i):
        T = i / (self.n - 1)
        if i < self.clip_n:
            fr = Image.open(os.path.join(self.clipdir, f"{i + 1:04d}.jpg")).convert("RGB")
            return self.caption(fr, T)
        j = i - self.clip_n; sn = self.n - self.clip_n
        fr = self.still(j / max(1, sn - 1))
        if self.clip_n and j < self.blend_n:
            if self._last is None:
                self._last = Image.open(os.path.join(self.clipdir, f"{self.clip_n:04d}.jpg")).convert("RGB")
            fr = Image.blend(self._last, fr, ease((j + 1) / (self.blend_n + 1)))
        return self.caption(fr, T)

    def still(self, t):
        c, W, H = self.cam, self.W, self.H
        e = ease(t, self.ease)
        ze = c.get("zoom", [1.0, 1.15])
        iw, ih = self.img.size

        def view(z):
            return W * SS / z, H * SS / z
        px = c.get("pan_x", [0, 0]); py = c.get("pan_y", [0, 0])
        if self.match:
            z = lerp(self.match["zoom"], ze[1], e)
            vw1, vh1 = view(ze[1])
            cx = lerp(iw / 2 + SS * self.match["dx"], iw / 2 + px[1] * (iw - vw1) / 2 * .9, e)
            cy = lerp(ih / 2 + SS * self.match["dy"], ih / 2 + py[1] * (ih - vh1) / 2 * .9, e)
            amt = ease(t * 1.6)  # fade effects in so the clip's last frame is not disturbed
        else:
            z = lerp(ze[0], ze[1], e); vw, vh = view(z)
            cx = iw / 2 + lerp(*px, e) * (iw - vw) / 2 * .9
            cy = ih / 2 + lerp(*py, e) * (ih - vh) / 2 * .9
            amt = 1.0
        vw, vh = view(z)
        sh = c.get("shake", 0.0)
        if sh:  # handheld shake in output pixels
            cx += SS * sh * (math.sin(t * 17 + self.seed) + .5 * math.sin(t * 41 + 1)) * amt
            cy += SS * sh * (math.sin(t * 13 + 2 + self.seed) + .5 * math.sin(t * 37)) * amt
        cx = min(max(cx, vw / 2), iw - vw / 2); cy = min(max(cy, vh / 2), ih - vh / 2)
        roll = c.get("roll", [0, 0]); ang = lerp(roll[0], roll[1], e)
        src = self.img
        if ang:
            src = src.rotate(-ang, resample=Image.BICUBIC, center=(cx, cy))
        fr = src.transform((W, H), Image.EXTENT, (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2), Image.BICUBIC)
        return self.light(self.focus(fr, t, amt), t, e, amt)

    # ---- effects ----------------------------------------------------------------
    def focus(self, fr, t, amt):
        f = self.d.get("focus")
        if not f: return fr
        mode = f.get("mode", "pull_in"); r = f.get("blur", 14)
        if mode in ("pull_in", "pull_out"):
            a, b = f.get("start", 0.0), f.get("end", 0.6)
            k = ease((t - a) / max(b - a, 1e-6))
            rad = r * (1 - k) if mode == "pull_in" else r * k
            return fr.filter(ImageFilter.GaussianBlur(rad)) if rad > 0.4 else fr
        if mode == "tiltshift":  # sharp band that slides; blur ramps in so clips hand off cleanly
            rr = r * amt
            if rr < 0.4: return fr
            fy = lerp(*f.get("y", [0.5, 0.5]), ease(t))
            bl = np.asarray(fr.filter(ImageFilter.GaussianBlur(rr)), np.float32)
            sh = np.asarray(fr, np.float32)
            ys = np.linspace(0, 1, self.H)[:, None, None]
            m = np.clip((np.abs(ys - fy) - f.get("band", 0.15)) / 0.3, 0, 1)
            return Image.fromarray((sh * (1 - m) + bl * m).astype(np.uint8))
        return fr

    def light(self, fr, t, e, amt):
        L = self.d.get("light")
        if not L: return fr
        a = np.asarray(fr, np.float32) / 255
        ex = 1 + (lerp(*L.get("exposure", [1, 1]), e) - 1) * amt
        wm = lerp(*L.get("warmth", [0, 0]), e) * amt
        a = a * ex * np.array([1 + .18 * wm, 1 + .02 * wm, 1 - .18 * wm], np.float32)
        xx, yy = grid(self.W, self.H)
        if "sweep" in L:
            s = L["sweep"]; pos = lerp(-0.3, 1.3, e)
            d = (xx + yy * s.get("slant", .4)) / (1 + s.get("slant", .4)) - pos
            beam = np.exp(-(d / s.get("width", .15)) ** 2) * s.get("strength", .35)
            a = a + beam[..., None] * np.array([1, .93, .8], np.float32)
        v = L.get("vignette", 0) * amt
        if v:
            a = a * (1 - v * (((xx - .5) ** 2 + (yy - .5) ** 2) * 2))[..., None]
        if L.get("flicker"):
            a = a * (1 + L["flicker"] * amt * math.sin(t * 90) * math.sin(t * 23))
        g = self.d.get("grain", 0)
        if g: a = a + np.random.default_rng().normal(0, g, a.shape).astype(np.float32)
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

    def caption(self, fr, t):
        c = self.d.get("caption")
        if not c: return fr
        a = min(1, t / 0.12) * min(1, (1 - t) / 0.08)
        if a <= 0: return fr
        font = ImageFont.truetype(c.get("font", "/usr/share/fonts/opentype/inter/Inter-Bold.otf"),
                                  int(c.get("size", 0.055) * self.H))
        d0 = ImageDraw.Draw(fr)
        lines, cur = [], ""
        for w in c["text"].split():
            if d0.textlength((cur + " " + w).strip(), font=font) > self.W * 0.86 and cur:
                lines.append(cur); cur = w
            else: cur = (cur + " " + w).strip()
        lines.append(cur)
        lh = font.size * 1.3
        y0 = c.get("y", 0.78) * self.H - len(lines) * lh / 2
        ov = Image.new("RGBA", fr.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        for k, ln in enumerate(lines):
            x = (self.W - d0.textlength(ln, font=font)) / 2
            d.text((x, y0 + k * lh), ln, font=font, fill=(255, 255, 255, int(255 * a)),
                   stroke_width=max(2, font.size // 14), stroke_fill=(0, 0, 0, int(200 * a)))
        return Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB")


def blend(a, b, k, kind):
    A = np.asarray(a, np.float32); B = np.asarray(b, np.float32); k = ease(k)
    H, W = A.shape[:2]
    if kind == "dip_black":
        m = (1 - 2 * k) if k < .5 else (2 * k - 1)
        return (A if k < .5 else B) * m
    if kind == "flash":
        m = 1 - abs(2 * k - 1)
        return np.clip((A if k < .5 else B) * (1 - m) + 255 * m, 0, 255)
    if kind == "whip":
        sh = int(W * k)
        out = np.concatenate([A, B], axis=1)[:, sh:sh + W] if sh < W else B
        n = int(40 * math.sin(math.pi * k) * W / 720) + 1
        return np.mean([np.roll(out, j * 2 - n, axis=1) for j in range(n)], axis=0) if n > 1 else out
    if kind == "zoom":
        s = 1 + .35 * k
        im = Image.fromarray(A.astype(np.uint8)).transform((W, H), Image.EXTENT,
             (W / 2 - W / 2 / s, H / 2 - H / 2 / s, W / 2 + W / 2 / s, H / 2 + H / 2 / s), Image.BICUBIC)
        return np.asarray(im, np.float32) * (1 - k) + B * k
    return A * (1 - k) + B * k


# ---- planning / rendering ----------------------------------------------------------
def make_plan(sb, fps):
    shots = sb["shots"]; plan = []
    for idx, s in enumerate(shots):
        n = max(2, round(float(s.get("duration", 4)) * fps))
        nxt = idx + 1 < len(shots)
        tr = s.get("transition", {"type": "crossfade", "duration": 0.8}) if nxt else None
        tn = round(tr["duration"] * fps) if tr else 0
        start = round(shots[idx - 1].get("transition", {"duration": 0.8})["duration"] * fps) if idx else 0
        for i in range(start, n - tn): plan.append(("s", idx, i))
        for j in range(tn): plan.append(("t", idx, n - tn + j, j, tn, tr["type"]))
    return plan


def render_chunk(args):
    sb, base, plan, out, W, H, fps = args
    shots = {}
    def S(i):
        if i not in shots: shots[i] = Shot(sb["shots"][i], W, H, fps, base)
        return shots[i]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
           "-preset", "fast", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for p in plan:
        if p[0] == "s":
            arr = np.asarray(S(p[1]).frame(p[2]))
        else:
            _, idx, i, j, tn, kind = p
            arr = blend(S(idx).frame(i), S(idx + 1).frame(j), (j + 1) / (tn + 1), kind)
        pr.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    pr.stdin.close(); pr.wait()
    return out


def prepare_clips(sb, base, W, H, fps, cache):
    for idx, s in enumerate(sb["shots"]):
        clip = s.get("intro_clip")
        if not clip: continue
        clip = clip if os.path.isabs(clip) else os.path.join(base, clip)
        d = os.path.join(cache, f"clip{idx:02d}"); os.makedirs(d, exist_ok=True)
        if not glob.glob(os.path.join(d, "*.jpg")):
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-vf",
                                   f"fps={fps},scale={W}:{H}:flags=lanczos", "-q:v", "2", os.path.join(d, "%04d.jpg")])
        frames = sorted(glob.glob(os.path.join(d, "*.jpg")))
        s["_clipdir"] = d
        img = s["image"] if os.path.isabs(s["image"]) else os.path.join(base, s["image"])
        s["_match"] = match_clip(img, frames[-1], W, H)
        print(f"shot {idx + 1}: clip {len(frames)} frames, match {s['_match']}", flush=True)


def main(sb_path, out, workers):
    sb = json.load(open(sb_path)); base = os.path.dirname(os.path.abspath(sb_path))
    W, H = sb.get("size", [720, 1280]); fps = sb.get("fps", 30)
    cache = os.path.abspath(out) + ".cache"; os.makedirs(cache, exist_ok=True)
    prepare_clips(sb, base, W, H, fps, cache)
    plan = make_plan(sb, fps)
    k = max(1, workers); size = math.ceil(len(plan) / k)
    jobs = [(sb, base, plan[a:a + size], os.path.join(cache, f"part{a // size:02d}.mp4"), W, H, fps)
            for a in range(0, len(plan), size)]
    print(f"{len(plan)} frames, {len(jobs)} chunks", flush=True)
    with ProcessPoolExecutor(len(jobs)) as ex:
        parts = list(ex.map(render_chunk, jobs))
    lst = os.path.join(cache, "parts.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
    if sb.get("audio"):
        au = sb["audio"] if os.path.isabs(sb["audio"]) else os.path.join(base, sb["audio"])
        cmd += ["-i", au, "-c:a", "aac", "-b:a", "160k", "-shortest"]
    subprocess.check_call(cmd + ["-c:v", "copy", "-movflags", "+faststart", out])
    shutil.rmtree(cache, ignore_errors=True)
    print("wrote", out)


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else (os.cpu_count() or 2)
    if "--workers" in sys.argv: a.remove(str(w))
    if len(a) != 2: sys.exit(__doc__)
    main(a[0], a[1], w)
