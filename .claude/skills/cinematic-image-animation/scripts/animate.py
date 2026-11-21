#!/usr/bin/env python3
"""Turn still images into a cinematic animated video (camera pan/zoom, rack focus,
lighting shifts, transitions). Usage: python3 animate.py storyboard.json out.mp4
Needs: Pillow, numpy, ffmpeg. See SKILL.md for the storyboard schema."""
import json, subprocess, sys, math, os
import numpy as np
from PIL import Image, ImageFilter

def ease(t, kind="inout"):
    t = min(max(t, 0.0), 1.0)
    if kind == "linear": return t
    if kind == "out": return 1 - (1 - t) ** 3
    if kind == "in": return t ** 3
    return t * t * (3 - 2 * t)  # smooth in-out

def lerp(a, b, t): return a + (b - a) * t

class Shot:
    def __init__(self, d, W, H, fps, base):
        self.d, self.W, self.H = d, W, H
        self.dur = float(d.get("duration", 4))
        self.n = max(2, round(self.dur * fps))
        p = d["image"] if os.path.isabs(d["image"]) else os.path.join(base, d["image"])
        im = Image.open(p).convert("RGB")
        # cover-fit then keep 1.6x headroom so zoom/pan never reveals edges
        s = max(W / im.width, H / im.height) * 1.6
        self.img = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        self.cam = d.get("camera", {})
        self.ease = self.cam.get("ease", "inout")
        self.seed = abs(hash(d["image"])) % 1000

    def frame(self, i, total_i=None):
        t = i / (self.n - 1)
        e = ease(t, self.ease)
        c = self.cam
        z = lerp(c.get("zoom", [1.0, 1.15])[0], c.get("zoom", [1.0, 1.15])[1], e)
        px = lerp(*c.get("pan_x", [0, 0]), e)   # -1..1, fraction of available slack
        py = lerp(*c.get("pan_y", [0, 0]), e)
        # handheld shake (px) for "real camera" feel
        sh = c.get("shake", 0.0)
        sx = sh * (math.sin(t * 17 + self.seed) + .5 * math.sin(t * 41 + 1)) if sh else 0
        sy = sh * (math.sin(t * 13 + 2 + self.seed) + .5 * math.sin(t * 37)) if sh else 0
        iw, ih = self.img.size
        aspect = self.W / self.H
        vh = ih / 1.6 / z
        vw = vh * aspect
        if vw > iw / 1.0: vw = iw / 1.0; vh = vw / aspect
        slack_x, slack_y = (iw - vw) / 2, (ih - vh) / 2
        cx = iw / 2 + px * slack_x * 0.9 + sx
        cy = ih / 2 + py * slack_y * 0.9 + sy
        cx = min(max(cx, vw / 2), iw - vw / 2); cy = min(max(cy, vh / 2), ih - vh / 2)
        roll = c.get("roll", [0, 0]); ang = lerp(roll[0], roll[1], e)
        src = self.img
        if ang:
            src = src.rotate(-ang, resample=Image.BICUBIC, center=(cx, cy))
        fr = src.transform((self.W, self.H), Image.EXTENT,
                           (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2), Image.BICUBIC)
        fr = self.focus(fr, t)
        return self.caption(self.light(fr, t, e), t)

    def caption(self, fr, t):
        c = self.d.get("caption")
        if not c: return fr
        from PIL import ImageDraw, ImageFont
        a = min(1, t / 0.12) * min(1, (1 - t) / 0.08)  # fade in/out
        if a <= 0: return fr
        font = ImageFont.truetype(c.get("font", "/usr/share/fonts/opentype/inter/Inter-Bold.otf"),
                                  int(c.get("size", 0.055) * self.H))
        d0 = ImageDraw.Draw(fr)
        words, lines, cur = c["text"].split(), [], ""
        for w in words:
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

    def focus(self, fr, t):
        f = self.d.get("focus")
        if not f: return fr
        mode = f.get("mode", "pull_in"); r = f.get("blur", 14)
        if mode in ("pull_in", "pull_out"):
            a, b = f.get("start", 0.0), f.get("end", 0.6)  # progress window of the pull
            k = ease((t - a) / max(b - a, 1e-6))
            rad = r * (1 - k) if mode == "pull_in" else r * k
            return fr.filter(ImageFilter.GaussianBlur(rad)) if rad > 0.4 else fr
        if mode == "tiltshift":  # sharp band at focus_y, blur falls off (miniature / depth feel)
            fy = lerp(*f.get("y", [0.5, 0.5]), ease(t))
            bl = np.asarray(fr.filter(ImageFilter.GaussianBlur(r)), np.float32)
            sh = np.asarray(fr, np.float32)
            ys = np.linspace(0, 1, self.H)[:, None, None]
            m = np.clip((np.abs(ys - fy) - f.get("band", 0.15)) / 0.3, 0, 1)
            return Image.fromarray((sh * (1 - m) + bl * m).astype(np.uint8))
        return fr

    def light(self, fr, t, e):
        L = self.d.get("light")
        if not L: return fr
        a = np.asarray(fr, np.float32) / 255
        ex = lerp(*L.get("exposure", [1, 1]), e)
        wm = lerp(*L.get("warmth", [0, 0]), e)  # -1 cool .. +1 warm
        a = a * ex * np.array([1 + .18 * wm, 1 + .02 * wm, 1 - .18 * wm], np.float32)
        H, W = a.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); xx /= W; yy /= H
        if "sweep" in L:  # moving soft light beam
            s = L["sweep"]; pos = lerp(-0.3, 1.3, e)
            d = (xx + yy * s.get("slant", .4)) / (1 + s.get("slant", .4)) - pos
            beam = np.exp(-(d / s.get("width", .15)) ** 2) * s.get("strength", .35)
            a = a + beam[..., None] * np.array([1, .93, .8], np.float32)
        v = L.get("vignette", 0)
        if v:
            r2 = ((xx - .5) ** 2 + (yy - .5) ** 2) * 2
            a = a * (1 - v * r2)[..., None]
        if L.get("flicker"):
            a = a * (1 + L["flicker"] * math.sin(t * 90) * math.sin(t * 23))
        g = self.d.get("grain", 0)
        if g: a = a + np.random.default_rng().normal(0, g, a.shape).astype(np.float32)
        return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def blend(a, b, k, kind):
    A = np.asarray(a, np.float32); B = np.asarray(b, np.float32); k = ease(k)
    H, W = A.shape[:2]
    if kind == "dip_black":
        m = (1 - 2 * k) if k < .5 else (2 * k - 1)
        return (A if k < .5 else B) * m
    if kind == "flash":  # light-leak flash cut
        m = 1 - abs(2 * k - 1)
        return np.clip((A if k < .5 else B) * (1 - m) + 255 * m, 0, 255)
    if kind == "whip":  # horizontal motion-blur whip pan
        sh = int(W * k); sh2 = int(W * (k - 1))
        out = np.concatenate([A, B], axis=1)[:, sh:sh + W] if sh < W else B
        n = int(40 * math.sin(math.pi * k)) + 1
        out = np.mean([np.roll(out, j * 2 - n, axis=1) for j in range(n)], axis=0) if n > 1 else out
        return out
    if kind == "zoom":  # push-through: outgoing scales up while fading
        s = 1 + .35 * k
        im = Image.fromarray(A.astype(np.uint8)).transform((W, H), Image.EXTENT,
             (W / 2 - W / 2 / s, H / 2 - H / 2 / s, W / 2 + W / 2 / s, H / 2 + H / 2 / s), Image.BICUBIC)
        return np.asarray(im, np.float32) * (1 - k) + B * k
    return A * (1 - k) + B * k  # crossfade

def main(sb_path, out):
    sb = json.load(open(sb_path)); base = os.path.dirname(os.path.abspath(sb_path))
    W, H = sb.get("size", [720, 1280]); fps = sb.get("fps", 30)
    shots = [Shot(s, W, H, fps, base) for s in sb["shots"]]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
    if sb.get("audio"):
        cmd += ["-i", sb["audio"], "-shortest", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    put = lambda arr: pr.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
    for idx, sh in enumerate(shots):
        nxt = shots[idx + 1] if idx + 1 < len(shots) else None
        tr = sh.d.get("transition", {"type": "crossfade", "duration": 0.8}) if nxt else None
        tn = round(tr["duration"] * fps) if tr else 0
        # frames of this shot already consumed by previous transition
        start = round(shots[idx - 1].d.get("transition", {"duration": 0.8})["duration"] * fps) if idx else 0
        for i in range(start, sh.n - tn):
            put(np.asarray(sh.frame(i)))
        for j in range(tn):
            put(blend(sh.frame(sh.n - tn + j), nxt.frame(j), (j + 1) / (tn + 1), tr["type"]))
    pr.stdin.close(); pr.wait()
    print("wrote", out)

if __name__ == "__main__":
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
