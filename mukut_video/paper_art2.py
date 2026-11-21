"""Dark layered-papercut stills, 1920x1080, for the 'Mukut' music video.
Every shape is a paper layer: drop shadow + edge bevel + grain. Usage: python3 paper_art2.py out_dir [ids...]"""
import numpy as np, math, sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops
W, H = 1920, 1080
rng = np.random.default_rng(5)

def M(fn):
    m = Image.new("L", (W, H), 0); fn(ImageDraw.Draw(m)); return m
def grad(c1, c2, y0=0, y1=H):
    t = np.clip((np.arange(H) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    a = np.array(c1) * (1 - t) + np.array(c2) * t
    return Image.fromarray(np.broadcast_to(a, (H, W, 3)).astype(np.uint8))

class Paper:
    def __init__(s, top, bot, y0=0, y1=H): s.cv = grad(top, bot, y0, y1).convert("RGBA")
    def put(s, mask, color, sh=1.0):
        if sh:
            sm = ImageChops.offset(mask, int(8 * sh), int(14 * sh)).filter(ImageFilter.GaussianBlur(8 * sh))
            blk = Image.new("RGBA", (W, H), (5, 2, 15, 0)); blk.putalpha(sm.point(lambda v: int(v * .55)))
            s.cv = Image.alpha_composite(s.cv, blk)
        fill = color if isinstance(color, Image.Image) else Image.new("RGB", (W, H), color)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); lay.paste(fill.convert("RGBA"), (0, 0), mask)
        edge = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(5)))
        dk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dk.putalpha(edge.point(lambda v: int(v * .3)))
        s.cv = Image.alpha_composite(Image.alpha_composite(s.cv, lay), dk)
    def glow(s, mask, color, alpha=.4, blur=24):
        m = mask.filter(ImageFilter.GaussianBlur(blur)); lay = Image.new("RGBA", (W, H), tuple(color) + (0,))
        lay.putalpha(m.point(lambda v: int(v * alpha))); s.cv = Image.alpha_composite(s.cv, lay)
    def finish(s):
        a = np.asarray(s.cv.convert("RGB"), np.float32)
        n = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        n = np.asarray(Image.fromarray((n * 40 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) - 128
        return Image.fromarray((a + n[..., None] * .12).clip(0, 255).astype(np.uint8))

# ---- primitives --------------------------------------------------------------------
def poly(p): return M(lambda d: d.polygon(p, fill=255))
def circ(x, y, r): return M(lambda d: d.ellipse((x - r, y - r, x + r, y + r), fill=255))
def ell(x, y, rx, ry): return M(lambda d: d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255))
def rect(x0, y0, x1, y1, r=0): return M(lambda d: d.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=255))
def strip(p, w): return M(lambda d: d.line(p, fill=255, width=w, joint="curve"))
def hill(y0, a, f, ph, a2=0, f2=0):
    pts = [(x, y0 + a * math.sin(x * f + ph) + a2 * math.sin(x * f2 + ph * 2)) for x in range(-20, W + 40, 16)]
    return poly(pts + [(W + 40, H + 10), (-20, H + 10)])
def wave(y, a, f, ph): return [(x, y + a * math.sin(x * f + ph)) for x in range(-20, W + 40, 16)]
def band(y, th, a, f, ph):
    top = wave(y, a, f, ph); return poly(top + [(x, yy + th) for x, yy in reversed(top)])
def star5(cx, cy, r, rot=0, ratio=.45):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * ratio; a = rot + i * math.pi / 5 - math.pi / 2
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return poly(pts)
GOLD = lambda y0, y1: grad((255, 226, 130), (214, 132, 38), y0, y1)

def stars(P, n, ymax=500, col=(255, 236, 160)):
    for _ in range(n): P.put(star5(rng.uniform(20, W - 20), rng.uniform(20, ymax), rng.uniform(5, 13), rng.uniform(0, 1)), col, .25)
def moon(P, x, y, r, col=(255, 246, 215)):
    for k, a in ((2.4, .10), (1.7, .16), (1.25, .24)): P.glow(circ(x, y, r * k), (255, 240, 200), a, 30)
    P.put(circ(x, y, r), col, .6)
    for dx, dy, rr in ((-.3, -.2, .18), (.25, .15, .22), (-.1, .35, .12)): P.put(circ(x + dx * r, y + dy * r, rr * r), (235, 225, 190), 0)
def cloud(x, y, s, col):
    return M(lambda d: [d.ellipse((x + a * s - r * s, y + b * s - r * s, x + a * s + r * s, y + b * s + r * s), fill=255)
                        for a, b, r in ((0, 0, 60), (80, -30, 75), (170, 0, 60), (90, 20, 65))] + [d.rectangle((x - 50 * s, y + 10 * s, x + 220 * s, y + 70 * s), fill=255)])
def rain(P, n=260, alpha=.35, ang=.22, ln=(40, 120)):
    def f(d):
        for _ in range(n):
            x, y, l = rng.uniform(-100, W), rng.uniform(-50, H), rng.uniform(*ln)
            d.line([(x, y), (x - l * ang, y + l)], fill=255, width=int(rng.integers(2, 4)))
    P.glow(M(f), (190, 215, 255), alpha, 1.2)
def crown(P, cx, cy, s, glow=True, col=None):
    """Paper crown, width ~ s, base at cy."""
    col = col or GOLD(cy - s * .6, cy)
    if glow:
        for k, a in ((2.2, .10), (1.5, .16), (1.1, .22)): P.glow(ell(cx, cy - s * .25, s * .6 * k, s * .4 * k), (255, 200, 90), a, 40)
    pts = [(cx - s / 2, cy), (cx - s / 2, cy - s * .38), (cx - s * .27, cy - s * .2), (cx - s * .16, cy - s * .62),
           (cx, cy - s * .3), (cx + s * .16, cy - s * .62), (cx + s * .27, cy - s * .2), (cx + s / 2, cy - s * .38), (cx + s / 2, cy)]
    P.put(poly(pts), col, 1.2)
    P.put(rect(cx - s / 2, cy - s * .09, cx + s / 2, cy + s * .04, int(s * .02)), (224, 150, 50), .6)
    for x, y in ((cx - s * .16, cy - s * .64), (cx + s * .16, cy - s * .64), (cx, cy - s * .32), (cx - s / 2, cy - s * .4), (cx + s / 2, cy - s * .4)):
        P.put(circ(x, y, s * .035), (255, 245, 200), .4)
    for dx, c in ((-.3, (220, 40, 70)), (0, (60, 150, 255)), (.3, (220, 40, 70))): P.put(circ(cx + dx * s, cy - s * .045, s * .03), c, .2)
def figure(P, x, y, s, col=(10, 8, 18), cloak=True):
    """Silhouette in a long coat, feet at y, height ~ 1.7*s."""
    if cloak: P.put(poly([(x + s * .1, y - s * 1.35), (x + s * 1.2, y - s * .9), (x + s * 1.9, y - s * .1), (x + s * 1.0, y), (x + s * .1, y)]), (22, 16, 34), .8)
    P.put(poly([(x - s * .22, y - s * 1.4), (x + s * .22, y - s * 1.4), (x + s * .42, y), (x - s * .42, y)]), col, 1)
    P.put(circ(x, y - s * 1.55, s * .17), col, 1)
def sunrays(P, cx, cy, r0, r1, n, c1, c2, rot=0):
    for i in range(n):
        a0 = rot + i * 2 * math.pi / n; a1 = a0 + math.pi / n * .9
        P.put(poly([(cx + r0 * math.cos(a0), cy + r0 * math.sin(a0)), (cx + r1 * math.cos((a0 + a1) / 2), cy + r1 * math.sin((a0 + a1) / 2)),
                    (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1))]), c1 if i % 2 else c2, .4)
def skyline(P, y0, n, cols, hmin, hmax, win=True, lit=.5, seed=0):
    r = np.random.default_rng(seed); x = -20
    while x < W:
        w = r.uniform(70, 170); h = r.uniform(hmin, hmax); c = cols[int(r.integers(len(cols)))]
        P.put(rect(x, y0 - h, x + w, y0 + 400, 0), c, .6)
        if r.random() < .3: P.put(poly([(x + w * .5 - 10, y0 - h), (x + w * .5, y0 - h - r.uniform(40, 120)), (x + w * .5 + 10, y0 - h)]), c, 0)
        if win:
            for wy in range(int(y0 - h + 22), int(y0 - 14), 34):
                for wx in range(int(x + 14), int(x + w - 22), 28):
                    if r.random() < lit: P.put(rect(wx, wy, wx + 13, wy + 18, 2), (255, int(r.uniform(190, 230)), int(r.uniform(90, 150))), 0)
        x += w + r.uniform(0, 14)
def car(P, x, y, s):
    """Black sedan, wheels on y, length ~ 700*s."""
    body = [(-350, 0), (-338, -62), (-210, -96), (-120, -168), (90, -168), (205, -98), (338, -66), (352, 0)]
    P.put(poly([(x + a * s, y + b * s) for a, b in body]), (12, 12, 20), 1.3)
    P.put(poly([(x + a * s, y + b * s) for a, b in ((-110, -154), (-60, -154), (-60, -102), (-175, -102))]), (46, 60, 96), 0)
    P.put(poly([(x + a * s, y + b * s) for a, b in ((-40, -154), (80, -154), (170, -102), (-40, -102))]), (46, 60, 96), 0)
    for wx in (-215, 225): P.put(circ(x + wx * s, y, 62 * s), (6, 6, 12), 1); P.put(circ(x + wx * s, y, 28 * s), (110, 120, 140), 0)
    P.put(circ(x + 340 * s, y - 40 * s, 15 * s), (255, 250, 220), 0)
    P.glow(poly([(x + 345 * s, y - 52 * s), (x + 1100 * s, y - 230 * s), (x + 1100 * s, y + 90 * s), (x + 345 * s, y - 28 * s)]), (255, 240, 190), .30, 22)
def lamp(P, x, ytop, ybot, cone=True):
    P.put(rect(x - 9, ytop, x + 9, ybot, 3), (10, 10, 20), 1); P.put(rect(x - 60, ytop - 8, x + 20, ytop + 6, 4), (10, 10, 20), 1)
    P.put(circ(x - 48, ytop + 12, 16), (255, 240, 190), 0)
    for k, a in ((3.4, .12), (2.2, .2)): P.glow(circ(x - 48, ytop + 12, 16 * k * 2.2), (255, 235, 170), a, 30)
    if cone: P.glow(poly([(x - 56, ytop + 24), (x - 330, ybot), (x + 230, ybot)]), (255, 235, 170), .22, 26)

# ---- scenes ------------------------------------------------------------------------
def a1():  # crown on wet asphalt, rain, bokeh
    P = Paper((10, 14, 34), (4, 6, 16));
    for _ in range(26):
        x, y, r = rng.uniform(0, W), rng.uniform(0, 520), rng.uniform(24, 80)
        P.glow(circ(x, y, r), [(90, 200, 255), (200, 120, 255), (255, 160, 90)][int(rng.integers(3))], .18, 14)
    P.put(poly([(0, 600), (W, 600), (W, H), (0, H)]), grad((28, 34, 60), (10, 12, 26), 600, H), 0)
    for k in range(5): P.put(ell(960, 770 + k * 38, 760 - k * 80, 90 - k * 10), (34 + k * 4, 44 + k * 4, 78), .3)
    crown(P, 960, 740, 420)
    P.glow(ell(960, 800, 380, 40), (255, 200, 90), .25, 24)
    for k in range(7): P.put(M(lambda d, k=k: d.ellipse((620 - k * 12 + k * 140, 880 - k * 3, 760 + k * 140 - k * 12, 940)) or d.ellipse((630 - k * 12 + k * 140, 885, 750 + k * 140 - k * 12, 935), fill=0)), (150, 190, 255), 0)
    rain(P, 320, .4); return P.finish()
def a2():  # rainy alley, streetlamp
    P = Paper((8, 12, 30), (22, 20, 50)); skyline(P, 700, 0, [(12, 16, 38), (16, 20, 46)], 260, 640, True, .25, 1)
    P.put(poly([(0, 760), (W, 760), (W, H), (0, H)]), grad((26, 30, 58), (8, 8, 18), 760, H), 0)
    lamp(P, 1280, 250, 800)
    P.glow(ell(1100, 900, 380, 40), (255, 235, 170), .25, 22)
    figure(P, 560, 840, 190, (6, 6, 14), False)
    P.put(poly([(430, 840), (370, 600), (330, 820)]), (14, 12, 26), .8)
    rain(P, 380, .45, .2); return P.finish()
def a3():  # black car under city
    P = Paper((10, 12, 36), (40, 26, 70)); stars(P, 40, 300); moon(P, 1500, 230, 90)
    skyline(P, 640, 0, [(18, 22, 54), (24, 26, 62)], 160, 420, True, .55, 2)
    skyline(P, 720, 0, [(10, 12, 30), (14, 16, 38)], 120, 300, True, .35, 3)
    P.put(poly([(0, 780), (W, 780), (W, H), (0, H)]), grad((30, 32, 60), (8, 8, 18), 780, H), 0)
    P.glow(ell(900, 900, 700, 36), (255, 240, 190), .18, 20); car(P, 760, 860, 1.0); rain(P, 300, .35); return P.finish()
def a4():  # lone figure on hill, big moon
    P = Paper((6, 10, 34), (50, 30, 80)); stars(P, 90, 600); moon(P, 1130, 330, 200)
    P.put(cloud(200, 280, 1.2, 0), (40, 34, 80), .4); P.put(hill(760, 70, .004, 1, 25, .011), (22, 18, 46), 1.3)
    P.put(hill(860, 60, .0035, 3, 20, .012), (12, 10, 28), 1.5); figure(P, 520, 800, 230, (4, 3, 10)); return P.finish()
def a5():  # layered night city + river reflection
    P = Paper((12, 14, 44), (70, 36, 90)); stars(P, 50, 380); moon(P, 400, 210, 80)
    for i, (y0, cols, lit) in enumerate(((600, [(46, 40, 96), (54, 44, 108)], .25), (690, [(28, 26, 66), (34, 30, 74)], .4), (780, [(14, 14, 36), (18, 18, 44)], .55))):
        skyline(P, y0, 0, cols, 120 + i * 40, 380 + i * 60, True, lit, 10 + i)
    P.put(poly([(0, 850), (W, 850), (W, H), (0, H)]), grad((20, 20, 50), (6, 6, 16), 850, H), 0)
    for _ in range(40): x = rng.uniform(0, W); P.put(rect(x, 870 + rng.uniform(0, 160), x + rng.uniform(40, 160), 880 + rng.uniform(0, 160), 3), (255, 200, 110), 0)
    return P.finish()
def a6():  # road to horizon, dawn
    P = Paper((60, 30, 100), (255, 170, 80), 0, 700); P.put(circ(960, 640, 150), (255, 230, 160), .5); sunrays(P, 960, 640, 160, 900, 28, (255, 200, 110), (255, 150, 90))
    P.put(hill(640, 40, .006, 0, 14, .02), (90, 40, 110), 1); P.put(hill(700, 50, .005, 2, 14, .02), (50, 24, 80), 1.2)
    P.put(poly([(900, 700), (1020, 700), (1800, H), (120, H)]), (22, 16, 40), 1.4)
    for k in range(9): y = 720 + k * k * 4.6; P.put(rect(950 - k * 2, y, 970 + k * 2, y + 6 + k * 3, 0), (255, 210, 120), 0)
    return P.finish()
def a7():  # crown rising on light beams
    P = Paper((8, 8, 28), (40, 14, 50)); sunrays(P, 960, 1100, 100, 1500, 24, (60, 30, 90), (90, 40, 110))
    for _ in range(80): P.put(circ(rng.uniform(300, 1620), rng.uniform(100, 1000), rng.uniform(3, 9)), (255, 200, 100), .1)
    P.put(hill(950, 40, .006, 1, 16, .02), (8, 6, 20), 1.4); crown(P, 960, 600, 520); return P.finish()
def a8():  # giant glowing crown + rays
    P = Paper((60, 10, 40), (255, 150, 60), 0, H); sunrays(P, 960, 560, 200, 1500, 32, (255, 214, 120), (220, 70, 60))
    for r, c in ((620, (120, 20, 60)), (500, (200, 50, 60)), (390, (255, 140, 50)), (290, (255, 214, 110))): P.put(circ(960, 560, r), c, 1)
    crown(P, 960, 700, 640); P.put(hill(980, 50, .005, 0, 20, .015), (30, 10, 30), 1.6); return P.finish()
def a9():  # flag in storm
    P = Paper((8, 10, 28), (60, 40, 90));
    for i, (y, c) in enumerate(((180, (30, 30, 70)), (300, (44, 40, 92)), (420, (60, 50, 110)))): P.put(band(y, 380, 60, .004 + i * .002, i * 2), c, 1)
    P.put(poly([(1380, 0), (1330, 300), (1420, 280), (1360, 520), (1470, 470), (1250, 780), (1320, 540), (1240, 580), (1300, 330), (1230, 340)]), (255, 240, 190), .3); P.glow(M(lambda d: None), (255, 240, 200), 0)
    P.glow(poly([(1380, 0), (1330, 300), (1420, 280), (1360, 520), (1250, 780), (1300, 330), (1230, 340)]), (255, 240, 200), .35, 26)
    P.put(rect(560, 140, 584, 960, 4), (200, 160, 80), 1.2)
    pts = [(584 + t * 700, 170 + 70 * math.sin(t * 7) * (.3 + t)) for t in np.linspace(0, 1, 40)]
    P.put(poly(pts + [(x, y + 330) for x, y in reversed(pts)]), (190, 24, 52), 1.3); P.put(poly(pts[:20] + [(x, y + 40) for x, y in reversed(pts[:20])]), (150, 16, 40), .5)
    crown(P, 900, 360, 170, glow=False); P.put(hill(940, 50, .005, 2, 20, .014), (6, 6, 16), 1.5); rain(P, 340, .4, .3); return P.finish()
def a10():  # king on hill, crown halo, storm
    P = Paper((10, 8, 30), (80, 30, 70)); sunrays(P, 960, 380, 120, 1500, 24, (90, 30, 80), (60, 20, 70))
    for y, c in ((120, (24, 22, 60)), (260, (36, 28, 80))): P.put(band(y, 300, 50, .005, y), c, 1)
    crown(P, 960, 330, 260); P.put(hill(820, 60, .004, 0, 24, .011), (14, 10, 30), 1.4); figure(P, 960, 860, 300, (4, 3, 8)); rain(P, 200, .3); return P.finish()
def a11():  # masks
    P = Paper((60, 12, 30), (24, 8, 26));
    for i, c in enumerate(((120, 20, 44), (150, 24, 52), (180, 30, 60))): P.put(band(100 + i * 140, 700, 50, .004 + i * .002, i * 2.4), c, 1.2)
    cols = [(240, 214, 190), (230, 190, 210), (200, 210, 235), (250, 225, 170), (60, 60, 80)]
    for i, c in enumerate(cols):
        x, y = 270 + i * 345, 560 + (30 if i % 2 else -10)
        P.put(ell(x, y, 140, 190), c, 1.2)
        for dx in (-50, 50): P.put(M(lambda d, dx=dx: d.pieslice((x + dx - 28, y - 70, x + dx + 28, y - 20), 180, 360, fill=255)), (14, 10, 22), 0)
        if i < 4: P.put(M(lambda d: d.arc((x - 60, y + 20, x + 60, y + 100), 15, 165, fill=255, width=10)), (150, 40, 60), 0)
        else:
            P.put(M(lambda d: d.line([(x - 50, y + 80), (x + 50, y + 60)], fill=255, width=10)), (200, 200, 220), 0)
            P.put(poly([(x - 10, y - 190), (x + 30, y - 40), (x - 20, y + 30), (x + 40, y + 190), (x + 10, y + 40), (x + 50, y - 30)]), (255, 70, 80), .4)
    return P.finish()
def a12():  # cracked mirror
    P = Paper((16, 10, 36), (60, 22, 60)); P.put(ell(960, 540, 430, 500), GOLD(40, 1040), 1.5); P.put(ell(960, 540, 390, 460), (30, 44, 82), .4)
    P.put(ell(960, 540, 360, 430), grad((70, 100, 150), (24, 30, 64)), 0); figure(P, 960, 900, 280, (8, 6, 16), False)
    for ang in (0.2, 1.1, 2.0, 2.9, 4.0, 5.0):
        pts = [(960, 520)];
        for k in range(1, 6): pts.append((960 + k * 90 * math.cos(ang + rng.uniform(-.15, .15)), 520 + k * 100 * math.sin(ang + rng.uniform(-.15, .15))))
        P.put(strip(pts, 6), (240, 250, 255), 0)
    for _ in range(14): x, y = 960 + rng.uniform(-380, 380), 520 + rng.uniform(-420, 420); P.put(poly([(x, y), (x + rng.uniform(20, 60), y + rng.uniform(-30, 30)), (x + rng.uniform(-20, 40), y + rng.uniform(30, 70))]), (150, 190, 240), .3)
    return P.finish()
def a13():  # breaking chain
    P = Paper((40, 8, 28), (10, 6, 20)); P.glow(ell(960, 540, 700, 260), (255, 60, 70), .25, 60)
    def link(x, y, ang, c):
        P.put(M(lambda d: d.rounded_rectangle((x - 78, y - 42, x + 78, y + 42), radius=42, fill=255)).rotate(ang, center=(x, y)), c, 1)
        P.put(M(lambda d: d.rounded_rectangle((x - 48, y - 18, x + 48, y + 18), radius=18, fill=255)).rotate(ang, center=(x, y)), (30, 8, 22), 0)
    for i in range(7):
        x = 90 + i * 120; link(x, 540 + 12 * math.sin(i), 0 if i % 2 == 0 else 0, (150, 150, 170))
    for i in range(7):
        x = 1100 + i * 120; link(x + 40, 560 - 6 * math.sin(i) + i * 8, 8, (150, 150, 170))
    P.put(poly([(930, 500), (960, 470), (990, 520), (1010, 480), (1000, 560), (960, 600), (940, 540)]), (255, 240, 200), .3)
    for _ in range(40): P.put(circ(rng.uniform(820, 1100), rng.uniform(380, 700), rng.uniform(3, 8)), (255, 210, 120), .1)
    return P.finish()
def a14():  # empty throne room
    P = Paper((8, 10, 30), (40, 24, 60)); P.put(poly([(0, 780), (W, 780), (W, H), (0, H)]), grad((50, 34, 70), (10, 8, 20), 780, H), 0)
    for i, x in enumerate((140, 440, 1480, 1780)): P.put(rect(x - 60, 0, x + 60, 840, 6), (22 + i % 2 * 6, 18, 48), 1.3); P.put(rect(x - 80, 760, x + 80, 850, 6), (30, 24, 60), 1)
    P.glow(poly([(900, 160), (1020, 160), (1500, 1000), (420, 1000)]), (200, 220, 255), .16, 24)
    P.put(M(lambda d: d.pieslice((620, 80, 1300, 760), 180, 360, fill=255) or d.rectangle((620, 420, 1300, 700), fill=255)), (150, 170, 220), .4)
    P.put(M(lambda d: d.pieslice((660, 120, 1260, 720), 180, 360, fill=255) or d.rectangle((660, 420, 1260, 700), fill=255)), (230, 240, 255), 0)
    P.put(rect(820, 420, 1100, 860, 18), (110, 18, 40), 1.4); P.put(rect(780, 700, 1140, 780, 12), (150, 24, 52), 1.2); P.put(rect(800, 780, 1120, 900, 10), (90, 14, 34), 1)
    crown(P, 960, 400, 200, glow=True); return P.finish()
def a15():  # figure at window, moon
    P = Paper((6, 8, 28), (30, 20, 60)); moon(P, 1050, 350, 190)
    P.put(M(lambda d: d.rectangle((0, 0, 460, H), fill=255)), (60, 14, 40), 1.6); P.put(M(lambda d: d.rectangle((1460, 0, W, H), fill=255)), (60, 14, 40), 1.6)
    P.put(M(lambda d: d.rectangle((0, 0, W, 90), fill=255)), (40, 8, 28), 1.4); P.put(hill(820, 70, .004, 1, 24, .011), (12, 10, 30), 1.2)
    P.put(M(lambda d: d.rectangle((0, 940, W, H), fill=255)), (22, 14, 40), 1.4); figure(P, 700, 960, 260, (3, 2, 8), False); return P.finish()
def a16():  # heartbeat
    P = Paper((4, 2, 8), (14, 4, 12));
    for r in (520, 400, 290, 190): P.glow(ell(960, 540, r * 1.3, r * .7), (255, 40, 60), .14, 20); P.put(M(lambda d, r=r: d.ellipse((960 - r * 1.3, 540 - r * .7, 960 + r * 1.3, 540 + r * .7), outline=255, width=6)), (170, 18, 40), 0)
    pts = [(0, 540), (640, 540), (700, 540), (740, 470), (790, 610), (840, 290), (900, 760), (950, 540), (1010, 540), (1080, 500), (1150, 560), (1200, 540), (W, 540)]
    P.glow(strip(pts, 14), (255, 70, 80), .7, 14); P.put(strip(pts, 10), (255, 100, 110), .3); crown(P, 960, 640, 150, glow=False, col=(60, 20, 34)); return P.finish()
def a17():  # choir rings + crown
    P = Paper((50, 10, 30), (255, 150, 60), 0, H); sunrays(P, 960, 540, 200, 1500, 36, (255, 214, 120), (180, 40, 60))
    for r, c in ((700, (90, 16, 50)), (520, (140, 26, 56)), (360, (210, 70, 56))):
        P.put(circ(960, 540, r), c, 1)
        n = int(r / 22)
        for i in range(n):
            a = i * 2 * math.pi / n; x, y = 960 + (r - 30) * math.cos(a), 540 + (r - 30) * math.sin(a) * .92
            P.put(circ(x, y, 12), (16, 8, 22), .3); P.put(ell(x, y + 24, 18, 14), (16, 8, 22), .3)
    crown(P, 960, 640, 520); return P.finish()
def a18():  # dawn crown monument on hill
    P = Paper((70, 30, 110), (255, 190, 100), 0, 760); P.put(circ(960, 700, 220), (255, 235, 170), .4); sunrays(P, 960, 700, 230, 1300, 30, (255, 210, 120), (255, 160, 90))
    P.put(hill(720, 50, .005, 2, 16, .017), (120, 56, 120), 1); P.put(hill(800, 60, .004, 0, 20, .012), (60, 28, 80), 1.2)
    crown(P, 960, 690, 360); P.put(hill(900, 60, .0045, 1, 18, .013), (20, 12, 34), 1.5)
    for x, y in ((420, 300), (520, 250), (1400, 280), (1500, 200), (1250, 360)): P.put(M(lambda d, x=x, y=y: d.line([(x - 22, y - 8), (x, y), (x + 22, y - 8)], fill=255, width=6)), (30, 18, 40), .2)
    return P.finish()

SCENES = {f"a{i}": f for i, f in enumerate((a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11, a12, a13, a14, a15, a16, a17, a18), 1)}
if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True); ids = sys.argv[2:] or list(SCENES)
    for k in ids: SCENES[k]().save(f"{out}/{k}.png"); print(k, end=" ", flush=True)
