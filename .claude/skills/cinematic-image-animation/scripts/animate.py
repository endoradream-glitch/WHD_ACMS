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
PULSES = []  # [(time_s, amplitude)] camera zoom pulses (kicks/downbeats); set by timed storyboards


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
        self.n = d.get("_n") or max(2, round(self.dur * fps))
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
    def frame(self, i, gt=None):
        T = i / (self.n - 1)
        if self.clip_n and i < self.clip_n:
            fr = Image.open(os.path.join(self.clipdir, f"{i + 1:04d}.jpg")).convert("RGB")
            return self.caption(fr, T)
        j = i - self.clip_n; sn = self.n - self.clip_n
        fr = self.still(j / max(1, sn - 1), gt)
        if self.clip_n and j < self.blend_n:
            if self._last is None:
                self._last = Image.open(os.path.join(self.clipdir, f"{self.clip_n:04d}.jpg")).convert("RGB")
            fr = Image.blend(self._last, fr, ease((j + 1) / (self.blend_n + 1)))
        return self.caption(fr, T)

    def still(self, t, gt=None):
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
        if gt is not None and PULSES:  # zoom pulse on beats: sharp attack, ~0.25 s decay
            z *= 1 + sum(a * math.exp(-(gt - tp) / 0.22) for tp, a in PULSES if 0 <= gt - tp < 1.2)
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


def make_plan_timed(sb, fps):
    """Shots own [t0,t1); each transition is centred on the cut time (so impacts land on the beat)."""
    shots = sb["shots"]; b = [round(s["t0"] * fps) for s in shots] + [round(shots[-1]["t1"] * fps)]
    tn = [0 if i + 1 >= len(shots) else round(shots[i].get("transition", {}).get("duration", 0) * fps) for i in range(len(shots))]
    for i, s in enumerate(shots): s["_n"] = max(2, b[i + 1] - b[i])
    plan = []
    for g in range(b[-1]):
        hit = None
        for m in range(len(shots) - 1):
            h = tn[m] // 2
            if tn[m] and b[m + 1] - h <= g < b[m + 1] + tn[m] - h:
                hit = (m, g - (b[m + 1] - h)); break
        if hit:
            m, j = hit
            plan.append(("T", g, m, g - b[m], g - b[m + 1], j, tn[m], shots[m]["transition"]["type"]))
        else:
            k = max(i for i in range(len(shots)) if b[i] <= g)
            plan.append(("S", g, k, g - b[k]))
    return plan


_FONTS = {}
def _font(path, size):
    if (path, size) not in _FONTS:
        _FONTS[(path, size)] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _FONTS[(path, size)]


def overlay(arr, gt, ov, W, H):
    """Global post effects: exposure curve, flashes, timed captions."""
    a = arr.astype(np.float32)
    keys = ov.get("exposure")
    if keys:
        ts = [k[0] for k in keys]; vs = [k[1] for k in keys]
        a = a * float(np.interp(gt, ts, vs))
    for fl in ov.get("flashes", []):
        dt = gt - fl["t"]
        if 0 <= dt < fl.get("decay", 0.3) * 6:
            a = a + 255 * fl.get("strength", .5) * math.exp(-dt / fl.get("decay", .3)) * np.array(fl.get("color", [1, 1, 1]), np.float32)
    caps = [c for c in ov.get("captions", []) if c["t0"] <= gt < c["t1"]]
    if not caps: return np.clip(a, 0, 255)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for c in caps:
        al = min(1, (gt - c["t0"]) / 0.15) * min(1, (c["t1"] - gt) / 0.12)
        if al <= 0: continue
        fb = _font(ov["font_bn"], int(ov.get("size_bn", 0.058) * H)); fe = _font(ov["font_en"], int(ov.get("size_en", 0.034) * H))
        y = ov.get("y", 0.80) * H
        for text, fnt, col, dy in ((c.get("bn"), fb, (255, 255, 255), 0), (c.get("en"), fe, (255, 214, 140), fb.size * 1.28)):
            if not text: continue
            # wrap
            words, lines, cur = text.split(), [], ""
            for w in words:
                if d.textlength((cur + " " + w).strip(), font=fnt) > W * 0.86 and cur: lines.append(cur); cur = w
                else: cur = (cur + " " + w).strip()
            lines.append(cur)
            for ln in lines:
                x = (W - d.textlength(ln, font=fnt)) / 2
                d.text((x, y + dy), ln, font=fnt, fill=col + (int(255 * al),), stroke_width=max(2, fnt.size // 14),
                       stroke_fill=(0, 0, 0, int(220 * al)))
                if fnt is fb and ov.get("thicken", True):  # FreeSans has no Bengali bold: fatten the regular weight
                    d.text((x, y + dy), ln, font=fnt, fill=col + (int(255 * al),), stroke_width=1,
                           stroke_fill=col + (int(255 * al),))
                dy += fnt.size * 1.22
    return np.asarray(Image.alpha_composite(im, layer).convert("RGB"), np.float32)


def render_chunk(args):
    sb, base, plan, out, W, H, fps = args
    global PULSES
    PULSES = [tuple(p) for p in sb.get("overlays", {}).get("pulses", [])]
    ov = sb.get("overlays", {})
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
        elif p[0] == "t":
            _, idx, i, j, tn, kind = p
            arr = blend(S(idx).frame(i), S(idx + 1).frame(j), (j + 1) / (tn + 1), kind)
        elif p[0] == "S":
            _, g, k, i = p; arr = overlay(np.asarray(S(k).frame(i, g / fps)), g / fps, ov, W, H)
        else:
            _, g, m, i, i2, j, tn, kind = p
            arr = overlay(blend(S(m).frame(i, g / fps), S(m + 1).frame(i2, g / fps), (j + 1) / (tn + 1), kind), g / fps, ov, W, H)
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
    plan = make_plan_timed(sb, fps) if sb.get("timed") else make_plan(sb, fps)
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
