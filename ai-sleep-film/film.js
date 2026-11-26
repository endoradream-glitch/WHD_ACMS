// THE FILM — "What if AI needs sleep?" in a 3D look: a tiny perspective engine (spheres, boxes, rings, networks)
// drawn with shaded canvas gradients. Every frame is a pure function of t.
(function () {
  const U = globalThis.U, G = globalThis.G, S = globalThis.SCORE, Studio = globalThis.Studio;
  const W = G.W, H = G.H;
  const { clamp, lerp, ease } = U;
  const TAU = Math.PI * 2;
  const sm = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
  const h = (a, b = 0) => { const x = Math.sin(a * 127.1 + b * 311.7 + 17.3) * 43758.5453; return x - Math.floor(x); };
  const BN = '"Inter","DejaVu Sans","Lohit Bengali","Mukti","Ani",sans-serif';
  const mixc = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
  const rgb = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
  const BLUE = [110, 180, 255], PURPLE = [160, 110, 255], GOLD = [255, 205, 110], RED = [255, 70, 90], TEAL = [90, 230, 210], PINK = [255, 140, 200], WHITE = [245, 248, 255];

  // ---------- text ----------
  function text(ctx, str, x, y, o = {}) {
    const { size = 48, color = [255, 255, 255], align = 'center', weight = 600, alpha = 1, glow = 0, base = 'middle' } = o;
    ctx.save();
    ctx.font = `${weight} ${size}px ${BN}`; ctx.textAlign = align; ctx.textBaseline = base; ctx.globalAlpha *= alpha;
    if (glow) { ctx.shadowColor = rgb(o.glowColor || color, 0.9); ctx.shadowBlur = glow; }
    ctx.fillStyle = Array.isArray(color) ? rgb(color) : color;
    ctx.fillText(str, x, y);
    ctx.restore();
  }
  function text3d(ctx, str, x, y, o = {}) { // extruded: stacked darker copies behind the front face
    const depth = o.depth ?? 14, dx = o.dx ?? 0.7, dy = o.dy ?? 1.0, col = o.color || WHITE, back = o.back || mixc(col, [10, 10, 40], 0.75);
    for (let i = depth; i >= 1; i--) text(ctx, str, x + dx * i, y + dy * i, { ...o, color: mixc(back, col, 1 - i / depth * 0.9), glow: 0 });
    text(ctx, str, x, y, o);
  }
  function wrap(ctx, str, maxW) {
    const words = str.split(' '), lines = []; let cur = '';
    for (const w of words) { const t2 = cur ? cur + ' ' + w : w; if (ctx.measureText(t2).width > maxW && cur) { lines.push(cur); cur = w; } else cur = t2; }
    if (cur) lines.push(cur); return lines;
  }

  // ---------- tiny 3D ----------
  const camDefault = { ry: 0, rx: 0, d: 1000, f: 1000, cx: W / 2, cy: H / 2 };
  function P(p, c) {
    const cy = Math.cos(c.ry), sy = Math.sin(c.ry), cx = Math.cos(c.rx), sx = Math.sin(c.rx);
    const x1 = p[0] * cy + p[2] * sy, z1 = -p[0] * sy + p[2] * cy;
    const y1 = p[1] * cx - z1 * sx, z2 = p[1] * sx + z1 * cx;
    const s = c.f / Math.max(60, c.d + z2);
    return { x: c.cx + x1 * s, y: c.cy + y1 * s, s, z: z2 };
  }
  function sphere(ctx, q, r, col, o = {}) {
    const R = r * q.s; if (R < 0.3) return;
    const a = o.alpha ?? 1;
    if (o.glow) { const g = ctx.createRadialGradient(q.x, q.y, R * 0.5, q.x, q.y, R * (1 + o.glow)); g.addColorStop(0, rgb(col, 0.45 * a)); g.addColorStop(1, rgb(col, 0)); ctx.fillStyle = g; ctx.fillRect(q.x - R * (1 + o.glow), q.y - R * (1 + o.glow), R * 2 * (1 + o.glow), R * 2 * (1 + o.glow)); }
    const g = ctx.createRadialGradient(q.x - R * 0.38, q.y - R * 0.42, R * 0.05, q.x, q.y, R);
    g.addColorStop(0, rgb(mixc(col, [255, 255, 255], 0.75), a)); g.addColorStop(0.35, rgb(col, a)); g.addColorStop(1, rgb(mixc(col, [8, 6, 30], 0.72), a));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(q.x, q.y, R, 0, TAU); ctx.fill();
  }
  const LIGHT = (() => { const l = [-0.5, -0.8, -0.4], n = Math.hypot(...l); return l.map((v) => v / n); })();
  const FACES = [[[0, 1, 2, 3], [0, 0, -1]], [[5, 4, 7, 6], [0, 0, 1]], [[4, 0, 3, 7], [-1, 0, 0]], [[1, 5, 6, 2], [1, 0, 0]], [[4, 5, 1, 0], [0, -1, 0]], [[3, 2, 6, 7], [0, 1, 0]]];
  function box(ctx, c, cx, cy, cz, w, hh, d, col, o = {}) { // centre (cx,cy,cz), world y down; o.yaw rotates about y
    const yaw = o.yaw || 0, cs = Math.cos(yaw), sn = Math.sin(yaw);
    const V = [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]].map(([x, y, z]) => {
      const px = x * w / 2, pz = z * d / 2; return P([cx + px * cs + pz * sn, cy + y * hh / 2, cz - px * sn + pz * cs], c);
    });
    const fs = FACES.map(([idx, n]) => {
      const nx = n[0] * cs + n[2] * sn, nz = -n[0] * sn + n[2] * cs;
      const lit = clamp(0.35 + 0.65 * Math.max(0, -(nx * LIGHT[0] + n[1] * LIGHT[1] + nz * LIGHT[2])));
      return { idx, lit, z: idx.reduce((s, i) => s + V[i].z, 0) / 4, n };
    }).sort((a, b) => b.z - a.z);
    const out = [];
    for (const f of fs) {
      const pts = f.idx.map((i) => V[i]);
      // back-face cull by signed area
      let ar = 0; for (let i = 0; i < 4; i++) { const p = pts[i], q = pts[(i + 1) % 4]; ar += p.x * q.y - q.x * p.y; }
      if (ar > 0) continue;
      ctx.fillStyle = rgb(mixc([6, 8, 28], col, f.lit), o.alpha ?? 1);
      ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.closePath(); ctx.fill();
      if (o.edge) { ctx.strokeStyle = rgb(o.edge, 0.5); ctx.lineWidth = 1.2; ctx.stroke(); }
      out.push({ pts, f });
    }
    return out; // visible faces (for windows / decals)
  }
  function uv(pts, u, v) { // bilinear point on a projected quad [tl,tr,br,bl]-ish: pts order from FACES
    const a = [lerp(pts[0].x, pts[1].x, u), lerp(pts[0].y, pts[1].y, u)], b = [lerp(pts[3].x, pts[2].x, u), lerp(pts[3].y, pts[2].y, u)];
    return [lerp(a[0], b[0], v), lerp(a[1], b[1], v)];
  }
  function windows(ctx, pts, cols, rows, fn) {
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
      const k = fn(i, j); if (!k) continue;
      const u0 = (i + 0.2) / cols, u1 = (i + 0.8) / cols, v0 = (j + 0.25) / rows, v1 = (j + 0.75) / rows;
      const p = [uv(pts, u0, v0), uv(pts, u1, v0), uv(pts, u1, v1), uv(pts, u0, v1)];
      ctx.fillStyle = k.col ? rgb(k.col, k.a ?? 0.9) : 'rgba(255,220,140,0.85)'; ctx.beginPath(); p.forEach((q, n) => (n ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1]))); ctx.fill();
    }
  }
  function ring(ctx, c, center, R, tilt, spin, col, o = {}) { // 3D ring; back half drawn first (o.back) or front half (o.front)
    const N = 64, pts = [];
    for (let i = 0; i <= N; i++) {
      const a = i / N * TAU + spin, x = Math.cos(a) * R, z0 = Math.sin(a) * R;
      pts.push(P([center[0] + x, center[1] + z0 * Math.sin(tilt) * 0.0 + (z0 * Math.sin(tilt)), center[2] + z0 * Math.cos(tilt)], c));
    }
    ctx.lineWidth = o.lw || 3; ctx.lineCap = 'round';
    for (let i = 0; i < N; i++) {
      const front = (pts[i].z + pts[i + 1].z) / 2 < P(center, c).z;
      if ((o.front && !front) || (o.back && front)) continue;
      ctx.strokeStyle = rgb(col, o.alpha ?? 0.8); ctx.beginPath(); ctx.moveTo(pts[i].x, pts[i].y); ctx.lineTo(pts[i + 1].x, pts[i + 1].y); ctx.stroke();
    }
  }
  function glowDot(ctx, x, y, r, col, a = 1) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgb(col, a)); g.addColorStop(1, rgb(col, 0));
    ctx.fillStyle = g; ctx.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function stars(ctx, t, o = {}) {
    const { n = 140, speed = 0, a = 1, seed = 1 } = o;
    for (let i = 0; i < n; i++) {
      const x = h(i, seed) * W, y = h(i, seed + 5) * H * (o.maxY ?? 1), tw = 0.5 + 0.5 * Math.sin(t * (1 + h(i, 9) * 2) + i);
      const z = speed ? ((h(i, 3) + t * speed) % 1) : 0;
      const sx = speed ? W / 2 + (x - W / 2) * (0.2 + z * 2) : x, sy = speed ? H / 2 + (y - H / 2) * (0.2 + z * 2) : y;
      const r = (speed ? 0.6 + z * 2.2 : 0.7 + h(i, 4) * 1.6);
      ctx.fillStyle = `rgba(255,255,255,${a * (0.35 + 0.65 * tw) * (speed ? Math.min(1, z * 3) : 1)})`; ctx.beginPath(); ctx.arc(sx, sy, r, 0, TAU); ctx.fill();
    }
  }
  function sky(ctx, c0, c1) { const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, rgb(c0)); g.addColorStop(1, rgb(c1)); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
  function floorGrid(ctx, t, col, o = {}) {
    const c = { ...camDefault, rx: 0.0, d: 900, f: 900, cx: W / 2, cy: o.cy ?? H * 0.62 }, y = o.y ?? 260, a = o.a ?? 0.5;
    ctx.lineWidth = 1.5;
    for (let i = -20; i <= 20; i++) { const p1 = P([i * 180, y, 100], c), p2 = P([i * 180, y, 4200], c); ctx.strokeStyle = rgb(col, a * (1 - Math.abs(i) / 22)); ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke(); }
    for (let k = 0; k < 22; k++) { const z = 100 + ((k * 180 + t * (o.speed ?? 120)) % 3960), p1 = P([-4000, y, z], c), p2 = P([4000, y, z], c); ctx.strokeStyle = rgb(col, a * (1 - z / 4200)); ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke(); }
  }

  // ---------- the AI orb (a character) ----------
  function orb(ctx, t, o) {
    const { x, y, r = 120, col = BLUE, sleepy = 0, glow = 1, look = [0, 0], ringAlpha = 0.8, eyeCol = WHITE, mouth = 0, bob = 1, seed = 0, tilt = 0.35 } = o;
    const by = y + Math.sin(t * 1.4 + seed) * 10 * bob, c = { ...camDefault, cx: x, cy: by, ry: 0, rx: 0, d: 900, f: 900 };
    const q = { x, y: by, s: 1 };
    ctx.save();
    glowDot(ctx, x, by, r * (2.6 + 0.3 * Math.sin(t * 1.4 + seed)), col, 0.35 * glow);
    // soft contact shadow
    if (o.shadowY) { ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.beginPath(); ctx.ellipse(x, o.shadowY, r * 0.9, r * 0.16, 0, 0, TAU); ctx.fill(); }
    ring(ctx, c, [0, 0, 0], r * 1.55, tilt, t * 0.9 + seed, col, { back: true, alpha: ringAlpha * 0.5, lw: 3 });
    sphere(ctx, q, r, col, { glow: 0.25 * glow });
    // face on the front of the sphere
    const ex = r * 0.36, ey = -r * 0.06, ew = r * 0.17, eh = r * 0.25 * (1 - sleepy);
    const lx = look[0] * r * 0.08, ly = look[1] * r * 0.06;
    for (const s of [-1, 1]) {
      const px = x + s * ex + lx, py = by + ey + ly;
      if (sleepy > 0.9 || eh < 2) { ctx.strokeStyle = rgb(mixc(eyeCol, [20, 20, 60], 0.3), 0.9); ctx.lineWidth = Math.max(3, r * 0.04); ctx.lineCap = 'round'; ctx.beginPath(); ctx.arc(px, py - r * 0.02, ew * 0.9, 0.15 * Math.PI, 0.85 * Math.PI); ctx.stroke(); }
      else {
        ctx.shadowColor = rgb(eyeCol, 0.9); ctx.shadowBlur = r * 0.2; ctx.fillStyle = rgb(eyeCol, 0.95);
        ctx.beginPath(); ctx.ellipse(px, py, ew, eh, 0, 0, TAU); ctx.fill(); ctx.shadowBlur = 0;
        ctx.fillStyle = rgb(mixc(col, [10, 10, 40], 0.7)); ctx.beginPath(); ctx.ellipse(px + lx * 0.6, py + ly * 0.6, ew * 0.45, eh * 0.55, 0, 0, TAU); ctx.fill();
        if (sleepy > 0.05) { ctx.fillStyle = rgb(mixc(col, [10, 10, 40], 0.35)); ctx.beginPath(); ctx.rect(px - ew * 1.3, py - eh - 2, ew * 2.6, eh * 2 * sleepy * 0.9 + 2); ctx.fill(); }
      }
    }
    ctx.strokeStyle = rgb(mixc(eyeCol, [20, 20, 60], 0.35), 0.85); ctx.lineWidth = Math.max(3, r * 0.035); ctx.lineCap = 'round';
    ctx.beginPath(); if (mouth > 0) ctx.ellipse(x + lx, by + r * 0.38, r * 0.1, r * 0.05 + r * 0.1 * mouth, 0, 0, TAU); else ctx.arc(x + lx, by + r * 0.28, r * 0.16, 0.2 * Math.PI, 0.8 * Math.PI); ctx.stroke();
    ring(ctx, c, [0, 0, 0], r * 1.55, tilt, t * 0.9 + seed, col, { front: true, alpha: ringAlpha, lw: 4 });
    // orbiting satellites
    for (let i = 0; i < 3; i++) { const a = t * 0.9 + seed + i * TAU / 3, p = P([Math.cos(a) * r * 1.55, Math.sin(a) * r * 1.55 * Math.sin(tilt), Math.sin(a) * r * 1.55 * Math.cos(tilt)], c); sphere(ctx, p, r * 0.07, mixc(col, WHITE, 0.6), { glow: 1.5 }); }
    ctx.restore();
  }
  function zzz(ctx, t, x, y, col = WHITE, k = 1) {
    for (let i = 0; i < 3; i++) {
      const ph = ((t * 0.35 + i / 3) % 1), a = Math.sin(ph * Math.PI);
      text3d(ctx, i === 1 ? 'z' : 'Z', x + ph * 90 + Math.sin(t * 2 + i) * 8, y - ph * 170, { size: (34 + i * 16) * k, color: col, alpha: a * 0.9, depth: 8, glow: 14, weight: 800 });
    }
  }

  // ---------- network (shared by brain / forgetting / sleep / nightmare) ----------
  const NET = (() => {
    const pts = [];
    const N = 96; // fibonacci shell + jitter
    for (let i = 0; i < N; i++) {
      const y = 1 - (i + 0.5) / N * 2, rr = Math.sqrt(1 - y * y), a = i * 2.399963;
      const j = 0.82 + 0.3 * h(i, 2);
      pts.push([Math.cos(a) * rr * j, y * j, Math.sin(a) * rr * j]);
    }
    const edges = [];
    for (let i = 0; i < N; i++) for (let k = i + 1; k < N; k++) { const d = Math.hypot(pts[i][0] - pts[k][0], pts[i][1] - pts[k][1], pts[i][2] - pts[k][2]); if (d < 0.5) edges.push([i, k]); }
    return { pts, edges };
  })();
  function network(ctx, t, o) {
    const { cx, cy, R = 300, ry = t * 0.25, rx = 0.25, col = BLUE, act = 1, order = 0, hl = null, alpha = 1, warp = 0, link = 0, grey = null } = o;
    const c = { ...camDefault, cx, cy, ry, rx, d: 1200, f: 1200 };
    const pr = NET.pts.map((p, i) => {
      const cl = [Math.floor(h(i, 7) * 4)], ang = cl[0] * TAU / 4 + 0.6, cp = [Math.cos(ang) * 0.6, (cl[0] % 2 ? 0.35 : -0.35), Math.sin(ang) * 0.6];
      const q = [lerp(p[0], cp[0] + p[0] * 0.28, order), lerp(p[1], cp[1] + p[1] * 0.28, order), lerp(p[2], cp[2] + p[2] * 0.28, order)];
      const w = warp * Math.sin(t * 5 + i) * 0.1;
      return { ...P([(q[0] + w) * R, q[1] * R, q[2] * R], c), i, cl: cl[0] };
    });
    ctx.save(); ctx.globalAlpha *= alpha; ctx.lineWidth = 1.4;
    for (const [a, b] of NET.edges) {
      const A = pr[a], B = pr[b], pulse = 0.5 + 0.5 * Math.sin(t * 3 * act - (a + b) * 0.4);
      const cc = grey && grey(a) > 0.5 ? [90, 95, 120] : (order > 0.5 && pr[a].cl === pr[b].cl ? GOLD : col);
      ctx.strokeStyle = rgb(cc, (0.1 + 0.28 * pulse * act) * (grey ? 1 - grey(a) * 0.6 : 1)); ctx.beginPath(); ctx.moveTo(A.x, A.y); ctx.lineTo(B.x, B.y); ctx.stroke();
    }
    if (link > 0) { // new bright cross-cluster connections
      for (let k = 0; k < 18 * link; k++) { const a = Math.floor(h(k, 40) * 96), b = Math.floor(h(k, 41) * 96); if (pr[a].cl === pr[b].cl) continue; ctx.strokeStyle = rgb(TEAL, 0.65); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(pr[a].x, pr[a].y); ctx.lineTo(pr[b].x, pr[b].y); ctx.stroke(); }
    }
    pr.sort((a, b) => b.z - a.z);
    for (const p of pr) {
      const pulse = 0.5 + 0.5 * Math.sin(t * 2.2 * act + p.i * 0.9), g = grey ? grey(p.i) : 0;
      const cc = g > 0.5 ? [100, 105, 135] : (order > 0.5 ? mixc(col, GOLD, order) : mixc(col, WHITE, pulse * 0.5 * act));
      sphere(ctx, p, 7 + 5 * pulse * act, cc, { glow: g > 0.5 ? 0 : 1.6 * act, alpha: 1 - g * 0.55 });
    }
    ctx.restore();
  }

  // ---------- captions ----------
  function caption(ctx, t, skip) {
    for (const l of S.LINES) {
      if (skip && skip.includes(l.id)) continue;
      const a = clamp((t - l.at) / 0.35) * clamp((l.at + l.dur + 0.35 - t) / 0.35);
      if (a <= 0) continue;
      ctx.save(); ctx.font = `600 44px ${BN}`;
      const ls = wrap(ctx, l.show, W * 0.78), lh = 64, bw = Math.max(...ls.map((s) => ctx.measureText(s).width)) + 80, bh = ls.length * lh + 30, y0 = H - 70 - bh;
      ctx.globalAlpha = a; ctx.fillStyle = 'rgba(6,8,24,0.62)'; ctx.beginPath(); ctx.roundRect(W / 2 - bw / 2, y0, bw, bh, 26); ctx.fill();
      ls.forEach((s, i) => text(ctx, s, W / 2, y0 + 15 + lh / 2 + i * lh, { size: 44, color: [248, 246, 255] }));
      ctx.restore();
    }
  }

  // ======================================================== SCENES
  const sc = (k) => S.S[k][0];
  const L = S.line;

  // 1. midnight room
  function room(ctx, t, u) {
    sky(ctx, [8, 12, 38], [26, 22, 60]);
    // window with moon
    const wx = W * 0.08, wy = H * 0.1, ww = W * 0.26, wh = H * 0.55;
    ctx.fillStyle = 'rgb(14,20,52)'; ctx.fillRect(wx, wy, ww, wh);
    ctx.save(); ctx.beginPath(); ctx.rect(wx, wy, ww, wh); ctx.clip(); stars(ctx, t, { n: 60, seed: 2 });
    const mp = { x: wx + ww * 0.55, y: wy + wh * 0.38, s: 1 }; sphere(ctx, mp, 85, [240, 238, 220], { glow: 1.2 });
    ctx.fillStyle = 'rgba(150,150,140,0.35)'; for (const [dx, dy, rr] of [[-20, -10, 14], [25, 18, 10], [-5, 30, 8]]) { ctx.beginPath(); ctx.arc(mp.x + dx, mp.y + dy, rr, 0, TAU); ctx.fill(); }
    ctx.restore();
    ctx.strokeStyle = 'rgb(70,60,100)'; ctx.lineWidth = 12; ctx.strokeRect(wx, wy, ww, wh); ctx.beginPath(); ctx.moveTo(wx + ww / 2, wy); ctx.lineTo(wx + ww / 2, wy + wh); ctx.moveTo(wx, wy + wh / 2); ctx.lineTo(wx + ww, wy + wh / 2); ctx.stroke();
    glowDot(ctx, wx + ww / 2, wy + wh, 500, [160, 180, 255], 0.12);
    // desk (perspective top)
    const c = { ...camDefault, rx: 0.5, cy: H * 0.78, d: 1100, f: 1000 };
    const dk = [[-1500, 0, -200], [1500, 0, -200], [1500, 0, 900], [-1500, 0, 900]].map((p) => P(p, c));
    ctx.fillStyle = 'rgb(28,22,48)'; ctx.beginPath(); dk.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.fill();
    // lamp glow
    glowDot(ctx, W * 0.5, H * 0.85, 700, [110, 120, 255], 0.12);
    // floating chat panel (3D tilt)
    const px = W * 0.74, py = H * 0.4, yaw = -0.28 + Math.sin(t * 0.7) * 0.03;
    ctx.save(); ctx.translate(px, py + Math.sin(t * 1.1) * 8); ctx.transform(Math.cos(yaw), -Math.sin(yaw) * 0.12, 0, 1, 0, 0);
    ctx.shadowColor = 'rgba(80,140,255,0.6)'; ctx.shadowBlur = 40; ctx.fillStyle = 'rgba(18,26,66,0.88)'; ctx.beginPath(); ctx.roundRect(-290, -230, 580, 460, 30); ctx.fill(); ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(120,170,255,0.6)'; ctx.lineWidth = 3; ctx.stroke();
    text(ctx, '12:07 AM', 220, -200, { size: 26, color: [140, 170, 255], align: 'right' });
    const q = clamp((u - 1.6) / 1.2);
    if (q > 0) { ctx.globalAlpha = q; ctx.fillStyle = 'rgb(60,110,230)'; ctx.beginPath(); ctx.roundRect(-250, -150, 410, 80, 22); ctx.fill(); text(ctx, 'একটা প্রশ্ন আছে…', -45, -110, { size: 34 }); ctx.globalAlpha = 1; }
    const aT = t - S.ev.answer;
    if (aT > -1.8) {
      ctx.fillStyle = 'rgb(44,40,90)'; ctx.beginPath(); ctx.roundRect(-270, -30, 540, 190, 22); ctx.fill();
      if (aT < 0) for (let i = 0; i < 3; i++) { ctx.fillStyle = `rgba(200,210,255,${0.35 + 0.65 * Math.max(0, Math.sin(t * 6 - i))})`; ctx.beginPath(); ctx.arc(-40 + i * 40, 65, 9, 0, TAU); ctx.fill(); }
      else { const full = 'দুঃখিত, আমি এখন খুব ক্লান্ত। আমাকে একটু ঘুমাতে দিন।', shown = full.slice(0, Math.floor(aT * 14)); ctx.font = `600 34px ${BN}`; wrap(ctx, shown, 480).forEach((s, i) => text(ctx, s, -245, 5 + i * 48, { size: 34, align: 'left', color: [230, 232, 255] })); text(ctx, '😴', 225, 130, { size: 40 }); }
    }
    ctx.restore();
    const sl = sm(S.ev.answer - 1, S.ev.answer + 2.5, t) * 0.85;
    orb(ctx, t, { x: W * 0.4, y: H * 0.5, r: 135, col: BLUE, sleepy: sl, look: [0.7, -0.2], mouth: 0, shadowY: H * 0.8 });
    if (sl > 0.5) zzz(ctx, t, W * 0.4 + 120, H * 0.36);
    const zoom = 1 + u * 0.004; // slow push-in baked as a vignette instead of a transform
  }

  // 2. title
  function title(ctx, t, u) {
    sky(ctx, [6, 6, 24], [30, 14, 64]);
    stars(ctx, t, { n: 150, speed: 0.18, seed: 4 });
    floorGrid(ctx, t, [150, 110, 255], { cy: H * 0.66, y: 230, a: 0.6 });
    glowDot(ctx, W / 2, H * 0.62, 900, [130, 80, 255], 0.18);
    const k = ease.outBack(clamp((t - S.ev.titleIn) / 0.9), 1.6), a = clamp((t - S.ev.titleIn) / 0.5);
    ctx.save(); ctx.translate(W / 2, H * 0.34); ctx.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k); ctx.rotate(Math.sin(t * 0.6) * 0.012);
    ctx.globalAlpha = a;
    text3d(ctx, 'WHAT IF AI', 0, -75, { size: 150, weight: 900, color: [255, 255, 255], depth: 22, back: [90, 60, 220], glow: 24, glowColor: PURPLE });
    text3d(ctx, 'NEEDS SLEEP?', 0, 85, { size: 150, weight: 900, color: GOLD, depth: 22, back: [160, 70, 40], glow: 24 });
    ctx.restore();
    text(ctx, 'কৃত্রিম বুদ্ধিমত্তারও যদি ঘুমের প্রয়োজন হয়?', W / 2, H * 0.6, { size: 54, alpha: clamp((t - S.ev.titleIn - 1.5) / 1), color: [225, 215, 255], glow: 14, glowColor: PURPLE });
    orb(ctx, t, { x: W * 0.82, y: H * 0.78, r: 70, col: BLUE, sleepy: 0.95, bob: 1 }); zzz(ctx, t, W * 0.82 + 60, H * 0.7, WHITE, 0.7);
  }

  // 3. why do we sleep: the brain network organises itself
  function brain(ctx, t, u) {
    sky(ctx, [8, 10, 36], [20, 14, 52]); stars(ctx, t, { n: 70, seed: 6 });
    const d = S.line('why').dur;
    const order = sm(d * 0.38, d * 0.62, u), link = sm(d * 0.62, d * 0.9, u);
    glowDot(ctx, W / 2, H * 0.46, 620, mixc(BLUE, GOLD, order), 0.2);
    network(ctx, t, { cx: W / 2, cy: H * 0.45, R: 330, col: BLUE, act: 1 - order * 0.5, order, link, ry: t * 0.3 });
    const lab = (s, a0, a1, y, col) => text(ctx, s, W * 0.17, y, { size: 44, alpha: sm(a0, a0 + 0.6, u) * (1 - sm(a1, a1 + 0.6, u)), color: col, glow: 16, align: 'left', weight: 700 });
    text(ctx, 'ঘুমের সময় মস্তিষ্ক…', W * 0.17, H * 0.14, { size: 40, align: 'left', color: [190, 200, 255], alpha: sm(0.3, 1, u) });
    lab('• অভিজ্ঞতা বিশ্লেষণ', d * 0.1, d * 0.38, H * 0.22, BLUE); lab('• স্মৃতি গুছিয়ে রাখা', d * 0.38, d * 0.62, H * 0.22, GOLD); lab('• নতুন সংযোগ তৈরি', d * 0.62, 99, H * 0.22, TEAL);
  }

  // 4. catastrophic forgetting
  function forget(ctx, t, u) {
    sky(ctx, [10, 8, 30], [30, 12, 44]); stars(ctx, t, { n: 60, seed: 8 });
    const f = S.line('forget'), fw = S.ev.forgetWord - f.at, prog = sm(1.5, fw, u);
    const dying = (i) => (h(i, 77) < prog * 0.85 ? 1 : 0);
    network(ctx, t, { cx: W * 0.52, cy: H * 0.44, R: 300, col: GOLD, act: 0.7, ry: t * 0.2 + 0.4, grey: dying });
    // incoming data stream: bubbles flying from the far distance
    const c = { ...camDefault, cx: W / 2, cy: H * 0.44, d: 1300, f: 1200 };
    for (let i = 0; i < 46; i++) {
      const ph = (h(i, 1) + t * (0.12 + h(i, 2) * 0.1)) % 1, ang = h(i, 3) * TAU, rr = 220 + h(i, 4) * 700;
      const p = P([Math.cos(ang) * rr * (1 - ph * 0.5), Math.sin(ang) * rr * (1 - ph * 0.5) * 0.6, 3200 * (1 - ph)], c);
      if (p.s <= 0.2) continue; sphere(ctx, p, 12 + h(i, 5) * 10, mixc(BLUE, TEAL, h(i, 6)), { glow: 1.2, alpha: Math.min(1, ph * 4) * clamp(1.4 - ph * 1.4 + 0.3) });
    }
    text(ctx, 'নতুন তথ্য', W * 0.1, H * 0.2, { size: 40, color: BLUE, glow: 14, align: 'left', alpha: sm(1, 2, u) });
    text(ctx, 'পুরোনো স্মৃতি', W * 0.9, H * 0.2, { size: 40, color: GOLD, glow: 14, align: 'right', alpha: sm(1, 2, u) });
    // memory bar
    const bx = W * 0.3, by = H * 0.74, bw = W * 0.4; ctx.fillStyle = 'rgba(255,255,255,0.12)'; ctx.beginPath(); ctx.roundRect(bx, by, bw, 18, 9); ctx.fill();
    ctx.fillStyle = rgb(mixc(GOLD, RED, prog)); ctx.beginPath(); ctx.roundRect(bx, by, bw * (1 - prog * 0.85), 18, 9); ctx.fill();
    text(ctx, 'শেখা তথ্য', bx, by - 22, { size: 28, align: 'left', color: [200, 205, 240] });
    const k = ease.outBack(clamp((t - S.ev.forgetWord) / 0.7), 2), sh = t > S.ev.forgetWord && t < S.ev.forgetWord + 0.5 ? (h(Math.floor(t * 60)) - 0.5) * 14 : 0;
    if (t > S.ev.forgetWord - 0.05) { ctx.save(); ctx.translate(W / 2 + sh, H * 0.2); ctx.scale(k, k); text3d(ctx, 'CATASTROPHIC', 0, -34, { size: 92, weight: 900, color: [255, 120, 130], depth: 16, back: [110, 20, 40], glow: 22, glowColor: RED }); text3d(ctx, 'FORGETTING', 0, 62, { size: 92, weight: 900, color: [255, 255, 255], depth: 16, back: [110, 20, 40], glow: 22, glowColor: RED }); ctx.restore(); }
  }

  // 5. digital sleep
  function sleep(ctx, t, u) {
    sky(ctx, [6, 8, 30], [24, 20, 62]); stars(ctx, t, { n: 110, seed: 10 });
    const mp = { x: W * 0.84, y: H * 0.2, s: 1 }; sphere(ctx, mp, 70, [240, 236, 215], { glow: 1 });
    const d = S.line('science').dur, order = sm(2.5, d * 0.8, u);
    orb(ctx, t, { x: W * 0.38, y: H * 0.46, r: 150, col: PURPLE, sleepy: 1, bob: 1.4, shadowY: H * 0.86 });
    zzz(ctx, t, W * 0.38 + 140, H * 0.28, [220, 210, 255], 1.1);
    // memory fragments reorganising around the orb: chaos -> neat rings
    const c = { ...camDefault, cx: W * 0.38, cy: H * 0.46, ry: t * 0.2, rx: 0.5, d: 1100, f: 1000 };
    for (let i = 0; i < 54; i++) {
      const rr = 260 + (i % 3) * 70, a = (i / 54) * TAU * 3 + t * (0.3 + (i % 3) * 0.1);
      const chaos = [(h(i, 1) - 0.5) * 900, (h(i, 2) - 0.5) * 560, (h(i, 3) - 0.5) * 700], neat = [Math.cos(a) * rr, 0, Math.sin(a) * rr];
      const p = P([lerp(chaos[0], neat[0], order), lerp(chaos[1], neat[1], order), lerp(chaos[2], neat[2], order)], c);
      sphere(ctx, p, 9, mixc(i % 2 ? BLUE : PINK, GOLD, order * 0.7), { glow: 1.6 });
    }
    // verdict panel
    const pa = sm(d * 0.42, d * 0.42 + 0.8, u);
    if (pa > 0) {
      ctx.save(); ctx.globalAlpha = pa; ctx.translate(W * 0.78, H * 0.55 + (1 - pa) * 30); ctx.fillStyle = 'rgba(20,18,60,0.8)'; ctx.beginPath(); ctx.roundRect(-250, -120, 500, 240, 26); ctx.fill(); ctx.strokeStyle = 'rgba(150,130,255,0.6)'; ctx.lineWidth = 3; ctx.stroke();
      text(ctx, 'ক্লান্তি অনুভব করা', 0, -50, { size: 38, color: [160, 160, 190] }); ctx.strokeStyle = rgb(RED); ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(-200, -50); ctx.lineTo(200, -50); ctx.stroke();
      text(ctx, '✓ তথ্য পুনর্গঠন', 0, 40, { size: 46, color: TEAL, glow: 18, weight: 700 }); ctx.restore();
    }
  }

  // 6. dreams
  function dream(ctx, t, u) {
    sky(ctx, [40, 20, 86], [14, 62, 96]); stars(ctx, t, { n: 90, seed: 12, a: 0.8, maxY: 0.6 });
    const d2 = S.line('dream2').at - sc('dream'), p2 = sm(d2 - 0.3, d2 + 1.2, u);
    glowDot(ctx, W * 0.5, H * 0.5, 800, [255, 120, 220], 0.16);
    const c = { ...camDefault, cx: W / 2, cy: H * 0.56, rx: 0.5 + 0.1 * Math.sin(t * 0.2), ry: t * 0.12, d: 1700, f: 1100 };
    // a dream city assembling from fog: boxes rise with the first dream line
    const bs = [];
    for (let i = -4; i <= 4; i++) for (let j = -4; j <= 4; j++) {
      const hh = 60 + h(i, j) * 380, rise = ease.outCubic(clamp((u - 1.0 - (Math.abs(i) + Math.abs(j)) * 0.28) / 2.2)), x = i * 160, z = j * 160;
      if (rise <= 0) continue;
      const wob = Math.sin(t * 0.8 + i * 1.3 + j) * 12 * p2;
      bs.push({ x, z, hh: hh * rise, i, j, wob });
    }
    bs.sort((a, b) => P([b.x, 0, b.z], c).z - P([a.x, 0, a.z], c).z);
    for (const b of bs) box(ctx, c, b.x, 260 - b.hh / 2 + b.wob, b.z, 110, b.hh, 110, mixc(PINK, TEAL, h(b.i, b.j + 3)), { alpha: 0.82, edge: [255, 255, 255] });
    // thousands of possible futures: orbiting memory bubbles
    for (let i = 0; i < 40; i++) { const a = t * (0.25 + h(i, 1) * 0.2) + i, rr = 560 + h(i, 2) * 300, p = P([Math.cos(a) * rr, -200 + Math.sin(a * 1.7 + i) * 220, Math.sin(a) * rr], c); sphere(ctx, p, 18 + h(i, 4) * 20, mixc(mixc(PINK, TEAL, h(i, 5)), WHITE, 0.2), { glow: 2, alpha: 0.7 }); }
    orb(ctx, t, { x: W * 0.14, y: H * 0.75, r: 80, col: PURPLE, sleepy: 1, shadowY: H * 0.86 });
    // second half: people, a city, and a shape that should not exist
    if (p2 > 0) {
      ctx.save(); ctx.globalAlpha = p2;
      const cc = { ...camDefault, cx: W * 0.5, cy: H * 0.44, ry: t * 0.5, rx: 0.5 + Math.sin(t * 0.4) * 0.3, d: 1100, f: 1000 };
      for (let k = 0; k < 4; k++) { // nested impossible cubes
        const s = 60 + k * 60, V = [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]].map(([x, y, z]) => P([x * s, y * s, z * s].map((v, n) => v * (1 + 0.08 * Math.sin(t * 2 + k + n))), { ...cc, ry: cc.ry * (k % 2 ? -1 : 1) + k }));
        ctx.strokeStyle = rgb(mixc(TEAL, PINK, k / 3), 0.9); ctx.lineWidth = 3; ctx.shadowColor = rgb(TEAL); ctx.shadowBlur = 14;
        for (const [a, b] of [[0, 1], [1, 2], [2, 3], [3, 0], [4, 5], [5, 6], [6, 7], [7, 4], [0, 4], [1, 5], [2, 6], [3, 7]]) { ctx.beginPath(); ctx.moveTo(V[a].x, V[a].y); ctx.lineTo(V[b].x, V[b].y); ctx.stroke(); }
      }
      ctx.shadowBlur = 0;
      for (let i = 0; i < 5; i++) { const x = W * (0.22 + i * 0.14), y = H * 0.7 + Math.sin(t + i) * 8; ctx.fillStyle = 'rgba(255,255,255,0.8)'; sphere(ctx, { x, y: y - 44, s: 1 }, 14, [255, 235, 230]); ctx.fillStyle = rgb(mixc(PINK, WHITE, 0.5), 0.8); ctx.beginPath(); ctx.roundRect(x - 13, y - 26, 26, 50, 12); ctx.fill(); }
      for (let i = 0; i < 4; i++) text3d(ctx, '?', W * (0.18 + i * 0.22), H * 0.2 + Math.sin(t * 1.2 + i * 2) * 20, { size: 90, weight: 900, color: [255, 255, 255], depth: 10, back: [120, 60, 200], glow: 16, glowColor: PINK, alpha: 0.85 });
      ctx.restore();
    }
  }

  // 7. 2050 city, night shift
  function city(ctx, t, u) {
    const d = S.line('city').dur, cyc = clamp(u / (d + 1)), day = 0.5 + 0.5 * Math.cos(cyc * TAU * 0.9 + 0.3); // 1 day -> 0 night
    sky(ctx, mixc([10, 12, 40], [110, 170, 230], day), mixc([30, 18, 70], [230, 200, 190], day));
    if (day < 0.6) stars(ctx, t, { n: 90, seed: 14, a: 1 - day / 0.6, maxY: 0.5 });
    const ang = cyc * TAU * 0.9, sx = W / 2 + Math.cos(ang + Math.PI * 0.2) * W * 0.46, sy = H * 0.45 - Math.sin(ang + Math.PI * 0.2) * H * 0.38;
    sphere(ctx, { x: sx, y: sy, s: 1 }, day > 0.5 ? 55 : 45, day > 0.5 ? [255, 225, 130] : [235, 235, 220], { glow: 1.6 });
    const c = { ...camDefault, cx: W / 2, cy: H * 0.66, rx: 0.62, ry: -0.7 + Math.sin(t * 0.15) * 0.15 + u * 0.01, d: 2100, f: 1500 };
    const gp = [[-1000, 220, -1000], [1000, 220, -1000], [1000, 220, 1000], [-1000, 220, 1000]].map((p) => P(p, c));
    ctx.fillStyle = rgb(mixc([14, 16, 40], [60, 90, 110], day)); ctx.beginPath(); gp.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.fill();
    const bl = [];
    for (let i = -3; i <= 3; i++) for (let j = -3; j <= 3; j++) {
      if ((i === 0 && j === 0)) continue;
      const kind = i === -2 && j === 1 ? 'hospital' : i === 2 && j === -1 ? 'bank' : i === 1 && j === 2 ? 'power' : 'b', hh = kind === 'power' ? 380 : kind === 'hospital' ? 260 : kind === 'bank' ? 200 : 90 + h(i, j) * 330;
      bl.push({ x: i * 260, z: j * 260, hh, kind, i, j });
    }
    bl.sort((a, b) => P([b.x, 0, b.z], c).z - P([a.x, 0, a.z], c).z);
    for (const b of bl) {
      const col = b.kind === 'hospital' ? [235, 240, 250] : b.kind === 'bank' ? [210, 190, 130] : b.kind === 'power' ? [150, 160, 190] : mixc([120, 130, 190], [90, 100, 160], h(b.i, b.j + 9));
      const faces = box(ctx, c, b.x, 220 - b.hh / 2, b.z, b.kind === 'bank' ? 190 : 150, b.hh, b.kind === 'bank' ? 190 : 150, mixc([40, 40, 80], col, 0.4 + day * 0.6));
      for (const { pts, f } of faces) if (Math.abs(f.n[1]) < 0.5) windows(ctx, pts, 3, Math.max(2, Math.floor(b.hh / 60)), (ii, jj) => (h(ii + b.i * 7, jj + b.j * 13) > 0.35 + day * 0.4 ? { a: 0.5 + 0.4 * (1 - day) } : null));
      const top = P([b.x, 220 - b.hh - 14, b.z], c);
      if (b.kind === 'hospital') { ctx.fillStyle = 'rgb(235,50,70)'; ctx.fillRect(top.x - 26 * top.s * 1.6, top.y - 8 * top.s, 52 * top.s * 1.6, 16 * top.s * 1.6); ctx.fillRect(top.x - 8 * top.s * 1.6, top.y - 26 * top.s, 16 * top.s * 1.6, 52 * top.s * 1.6); text(ctx, 'হাসপাতাল', top.x, top.y - 52 * top.s - 20, { size: 30, glow: 10 }); }
      if (b.kind === 'bank') text(ctx, 'ব্যাংক  $', top.x, top.y - 40, { size: 30, glow: 10, color: GOLD });
      if (b.kind === 'power') { text(ctx, '⚡ বিদ্যুৎকেন্দ্র', top.x, top.y - 40, { size: 30, glow: 10, color: [255, 235, 120] }); }
    }
    // two AIs share the shift: A works by day, B by night; the hand-over happens mid-speech
    const hand = sm(d * 0.42, d * 0.62, u);
    const A = { x: W * 0.3, y: H * 0.2 + hand * 70, col: BLUE, sl: hand * 0.95 }, B = { x: W * 0.7, y: H * 0.2 + (1 - hand) * 70, col: PURPLE, sl: (1 - hand) * 0.95 };
    for (const o of [A, B]) orb(ctx, t, { x: o.x, y: o.y, r: 70, col: o.col, sleepy: o.sl, glow: 1 - o.sl * 0.7, seed: o.x });
    if (hand > 0.05 && hand < 0.98) { ctx.strokeStyle = rgb(TEAL, 0.8 * Math.sin(hand * Math.PI)); ctx.lineWidth = 4; ctx.setLineDash([14, 12]); ctx.lineDashOffset = -t * 60; ctx.beginPath(); ctx.moveTo(A.x + 80, A.y); ctx.lineTo(B.x - 80, B.y); ctx.stroke(); ctx.setLineDash([]); text(ctx, 'দায়িত্ব হস্তান্তর', W / 2, H * 0.14, { size: 34, color: TEAL, glow: 12, alpha: Math.sin(hand * Math.PI) }); }
    // clock
    ctx.save(); ctx.translate(W * 0.9, H * 0.12); ctx.fillStyle = 'rgba(10,12,40,0.7)'; ctx.beginPath(); ctx.arc(0, 0, 60, 0, TAU); ctx.fill(); ctx.strokeStyle = 'rgba(160,190,255,0.8)'; ctx.lineWidth = 4; ctx.stroke();
    ctx.rotate(cyc * TAU * 0.9 * 2); ctx.strokeStyle = rgb(GOLD); ctx.lineWidth = 5; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, -42); ctx.stroke(); ctx.restore();
    const n = sm(d - 4.2, d - 3.2, u); if (n > 0) text3d(ctx, 'NIGHT SHIFT', W / 2, H * 0.34, { size: 120, weight: 900, color: [255, 255, 255], depth: 18, back: [60, 40, 160], glow: 26, glowColor: PURPLE, alpha: n });
  }

  // 8. the nightmare
  function nightmare(ctx, t, u) {
    const hb = (((u % 0.95) + 0.95) % 0.95) / 0.95, beat = Math.exp(-hb * 6) + 0.6 * Math.exp(-Math.abs(hb - 0.28) * 14);
    sky(ctx, mixc([8, 4, 18], [50, 6, 20], clamp((u - 4) / 8)), [20, 6, 24]);
    const d = S.line('night').dur, awake = sm(d * 0.34, d * 0.55, u), glitch = awake * (0.4 + 0.6 * (h(Math.floor(t * 12)) > 0.55 ? 1 : 0));
    network(ctx, t, { cx: W * 0.42, cy: H * 0.45, R: 360, col: mixc(PURPLE, RED, awake), act: 1.4, ry: -t * 0.3, rx: 0.3, warp: awake * 3, alpha: 0.8 });
    const col = mixc(PURPLE, RED, awake);
    // glitchy orb: drawn in horizontal slices that slip sideways
    ctx.save();
    const slices = glitch > 0.2 ? 9 : 1;
    for (let s = 0; s < slices; s++) {
      ctx.save(); ctx.beginPath(); ctx.rect(0, (s / slices) * H, W, H / slices + 1); ctx.clip();
      ctx.translate(glitch > 0.2 ? (h(s, Math.floor(t * 14)) - 0.5) * 70 * glitch : 0, 0);
      orb(ctx, t, { x: W * 0.42, y: H * 0.45, r: 170, col, sleepy: 1 - awake * 0.92, eyeCol: awake > 0.4 ? [255, 60, 70] : WHITE, glow: 1 + beat, look: [0, 0.4], shadowY: H * 0.88, tilt: 0.6 + awake });
      ctx.restore();
    }
    ctx.restore();
    // red/cyan split on the glitch
    if (glitch > 0.5) { ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.25; ctx.drawImage(ctx.canvas, 8, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; }
    // safety checklist panel
    const pa = sm(d * 0.5, d * 0.5 + 1, u);
    if (pa > 0) {
      ctx.save(); ctx.translate(W * 0.8, H * 0.46); ctx.globalAlpha = pa; ctx.transform(0.94, 0.05, 0, 1, 0, 0); ctx.fillStyle = 'rgba(30,8,24,0.9)'; ctx.beginPath(); ctx.roundRect(-250, -210, 500, 420, 26); ctx.fill(); ctx.strokeStyle = rgb(RED, 0.7); ctx.lineWidth = 3; ctx.stroke();
      text(ctx, 'নিরাপত্তা পরীক্ষা', 0, -165, { size: 38, weight: 800, color: [255, 190, 195] });
      [['নির্দেশ মানা', 0.0], ['অগ্রাধিকার', 0.3], ['সিদ্ধান্ত পদ্ধতি', 0.6]].forEach(([s, off], i) => {
        const y = -80 + i * 90, bad = clamp((awake - off) * 3), flick = h(Math.floor(t * 6), i) > 0.5;
        text(ctx, s, -220, y, { size: 32, align: 'left', color: [235, 225, 240] });
        text(ctx, bad < 0.3 ? '✓' : bad < 0.9 ? (flick ? '?' : '✓') : '?', 200, y, { size: 44, weight: 900, color: bad < 0.3 ? TEAL : RED, glow: 14 });
      });
      ctx.restore();
    }
    ctx.fillStyle = `rgba(255,0,40,${0.12 * beat})`; ctx.fillRect(0, 0, W, H);
    // vignette that thumps
    const g = ctx.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * (0.95 - beat * 0.05)); g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.7)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }

  // 9. final: waking and the question
  function final(ctx, t, u) {
    const s1 = L('final1'), s2 = L('final2'), dr = L('dreamt'), ask = L('ask');
    const quiet = sm(S.ev.silenceStart, S.ev.silenceStart + 0.8, t) * (1 - sm(S.ev.silenceEnd - 0.2, S.ev.silenceEnd + 0.6, t)); // the held silence
    sky(ctx, mixc([8, 10, 34], [2, 2, 8], quiet), mixc([24, 20, 56], [2, 2, 8], quiet)); stars(ctx, t, { n: 120, seed: 16, a: 1 - quiet });
    const mp = { x: W * 0.84, y: H * 0.18, s: 1 }; sphere(ctx, mp, 62, [240, 236, 215], { glow: 1, alpha: 1 - quiet });
    // bedroom: a sleeping person (left) and the AI (right)
    const wake = sm(s2.at - 1, s2.at + s2.dur * 0.85, t), face = sm(dr.at - 1, dr.at, t);
    const askP = sm(ask.at - 0.5, ask.at + 1.5, t);
    if (askP < 1) {
      ctx.save(); ctx.globalAlpha = 1 - askP;
      const zoom = lerp(1, 1.55, face), ox = lerp(0, -W * 0.18, face);
      ctx.translate(W / 2 + ox * 0, H * 0.5); ctx.scale(zoom, zoom); ctx.translate(-W / 2, -H * 0.5);
      const c = { ...camDefault, cx: W * 0.3, cy: H * 0.6, rx: 0.45, ry: -0.5, d: 1500, f: 1000 };
      box(ctx, c, 0, 200, 0, 520, 60, 260, [90, 90, 160], { alpha: 1 - quiet });
      box(ctx, c, 40, 160, 0, 440, 50, 230, mixc([80, 120, 200], [255, 190, 150], 0.1), { alpha: 1 - quiet });
      sphere(ctx, P([-200, 140, 0], c), 70, [250, 215, 190], { alpha: 1 - quiet });
      sphere(ctx, { x: W * 0.3, y: H * 0.35, s: 1 }, 6, WHITE, { glow: 3, alpha: 0.7 * (1 - quiet) }); // person's dream star
      for (let i = 0; i < 3; i++) { const ph = (t * 0.2 + i / 3) % 1; ctx.globalAlpha = (1 - askP) * Math.sin(ph * Math.PI) * 0.8 * (1 - quiet); text(ctx, '✦', W * 0.28 + ph * 70 + i * 20, H * 0.48 - ph * 140, { size: 28, color: GOLD, glow: 10 }); }
      ctx.globalAlpha = 1 - askP;
      const ox2 = lerp(W * 0.7, W * 0.52, face), oy = lerp(H * 0.5, H * 0.46, face), r = lerp(130, 200, face);
      // warm halo while it talks
      const talking = t >= dr.at && t < dr.at + dr.dur;
      const dim = 1 - quiet * 0.75;
      orb(ctx, t, { x: ox2, y: oy, r, col: mixc(PURPLE, GOLD, face * 0.6), sleepy: lerp(1, 0, wake) * (1 - face * 0.0), eyeCol: mixc(WHITE, [255, 240, 200], face), glow: dim, look: [-0.3 * (1 - face), 0.2], mouth: talking ? 0.5 + 0.5 * Math.sin(t * 16) ** 2 * 0.8 : 0, ringAlpha: dim, shadowY: H * 0.88 });
      if (wake < 0.5) zzz(ctx, t, ox2 + 110, oy - 130, [220, 210, 255], 0.9);
      ctx.restore();
      if (t >= dr.at - 0.2 && t < ask.at) { // the line, big, glowing
        const a = sm(dr.at - 0.2, dr.at + 0.6, t) * (1 - sm(S.ev.silenceStart + 0.8, S.ev.silenceStart + 1.8, t) * 0.0);
        const fade = 1 - sm(S.ev.silenceEnd - 0.3, S.ev.silenceEnd + 0.2, t);
        text3d(ctx, '“গত রাতে আমি একটা', W * 0.52, H * 0.09, { size: 76, color: [255, 245, 215], alpha: a * fade, glow: 26, glowColor: GOLD, depth: 8, back: [120, 80, 30], weight: 800 });
        text3d(ctx, 'স্বপ্ন দেখেছি।”', W * 0.52, H * 0.09 + 96, { size: 76, color: [255, 245, 215], alpha: a * fade, glow: 26, glowColor: GOLD, depth: 8, back: [120, 80, 30], weight: 800 });
      }
      if (quiet > 0.5) { ctx.fillStyle = `rgba(0,0,0,${0.0})`; }
    }
    // the question: two orbs trade colours, you cannot tell which is which
    if (askP > 0) {
      ctx.save(); ctx.globalAlpha = askP;
      const sw = 0.5 + 0.5 * Math.sin((t - ask.at) * 0.7), swap = sm(0.35, 0.65, sw);
      const xa = lerp(W * 0.3, W * 0.7, swap), xb = lerp(W * 0.7, W * 0.3, swap);
      orb(ctx, t, { x: xa, y: H * 0.44, r: 130, col: mixc(GOLD, BLUE, swap), sleepy: 0.0, seed: 1, glow: 1 });
      orb(ctx, t, { x: xb, y: H * 0.44, r: 130, col: mixc(BLUE, GOLD, swap), sleepy: 0.0, seed: 3, glow: 1 });
      text3d(ctx, '?', W / 2, H * 0.44, { size: 190, weight: 900, color: [255, 255, 255], depth: 18, back: [90, 60, 200], glow: 30, glowColor: PURPLE, alpha: 0.5 + 0.5 * Math.sin(t * 2) });
      const lab = clamp((t - ask.at - 3) / 1.2);
      text(ctx, 'অনুভূতি', W * 0.3, H * 0.7, { size: 44, color: GOLD, alpha: lab, glow: 14 }); text(ctx, 'অনুকরণ', W * 0.7, H * 0.7, { size: 44, color: BLUE, alpha: lab, glow: 14 });
      ctx.restore();
    }
  }

  function outro(ctx, t, u) {
    sky(ctx, [2, 3, 10], [14, 8, 34]); stars(ctx, t, { n: 150, speed: 0.04, seed: 20 });
    const a = ease.outCubic(clamp(u / 1.6));
    ctx.save(); ctx.translate(W / 2, H * 0.42); ctx.scale(0.9 + 0.1 * a, 0.9 + 0.1 * a);
    text3d(ctx, 'WHAT IF AI?', 0, 0, { size: 170, weight: 900, color: [255, 255, 255], depth: 24, back: [90, 60, 220], glow: 30, glowColor: PURPLE, alpha: a }); ctx.restore();
    text(ctx, 'কল্পনার শেষ যেখানে, ভবিষ্যতের শুরু হয় সেখানে।', W / 2, H * 0.62, { size: 50, color: [225, 215, 255], alpha: clamp((u - 1.8) / 1.2), glow: 12, glowColor: PURPLE });
    orb(ctx, t, { x: W / 2, y: H * 0.82, r: 46, col: BLUE, sleepy: 0.95, glow: 0.7 }); zzz(ctx, t, W / 2 + 40, H * 0.78, WHITE, 0.5);
  }

  const SCENES = { room, title, brain, forget, sleep, dream, city, nightmare, final, outro };
  const ORDER = [...S.order, 'outro'];

  Studio.film({
    draw(ctx, t) {
      ctx.fillStyle = '#05060f'; ctx.fillRect(0, 0, W, H);
      ORDER.forEach((k, i) => {
        const [a, b] = S.S[k];
        if (t < a - 0.5 || t >= b + 0.5) return;
        ctx.save(); ctx.globalAlpha = i === 0 ? 1 : clamp((t - (a - 0.5)) / 1.0);
        SCENES[k](ctx, t, t - a);
        ctx.restore();
      });
      if (t < S.END_NARR || true) { if (t < S.S.outro[0] + 0.3) caption(ctx, t, ['dreamt']); }
      if (t < 1.2) { ctx.fillStyle = `rgba(5,6,15,${1 - t / 1.2})`; ctx.fillRect(0, 0, W, H); }
    },
    post: { paper: 0, vignette: 0.45, grain: 0.04 },
  });
})();
