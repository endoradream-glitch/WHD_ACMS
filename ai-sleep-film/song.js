// THE SONG — ambient score + Bengali narration, all from score.js.
const path = require('path');
const { SR, Bus, reverb, pingpong } = require('./engine/audio/dsp');
const I = require('./engine/audio/instruments');
const MIX = require('./engine/audio/mix');
const Voice = require('./engine/audio/voice');
const sc = require('./score');
const { DURATION, ev, S, T } = sc;
const N = Math.ceil(DURATION * SR), bus = () => new Bus(N);
const pad = bus(), bass = bus(), keys = bus(), fx = bus(), pulse = bus(), verb = bus(), dly = bus();
const { m } = require('./engine/music');

// pads + bass drone per chord
for (const c of sc.chords) {
  const dark = c.scene === 'nightmare';
  const opts = { cutoff: dark ? 700 : 1100, attack: 1.2, release: 1.8 };
  const g = c.scene === 'room' || c.scene === 'final' ? 0.07 : 0.09;
  for (const n of c.notes) { const { L, R } = I.padNote(m(n), c.t1 - c.t0, opts); pad.addStereo(L, R, c.t0, g); }
  bass.addMono(I.bass(m(c.bass), Math.min(3.8, c.t1 - c.t0), { bright: 0.2, sub: 1 }), c.t0, dark ? 0.7 : 0.45);
}
// music-box arpeggios: sparse in the room, flowing in the dream, tender at the end
const arp = {
  Am: ['A4', 'C5', 'E5', 'A5'], F: ['A4', 'C5', 'F5', 'A5'], C: ['G4', 'C5', 'E5', 'G5'], G: ['G4', 'B4', 'D5', 'G5'],
  Dm: ['A4', 'D5', 'F5', 'A5'], Em: ['G4', 'B4', 'E5', 'G5'], Fmaj: ['A4', 'C5', 'E5', 'G5'], Dis: ['Bb4', 'Eb5', 'Gb5', 'Bb5'],
};
for (const c of sc.chords) {
  const step = { room: 1, title: 0.5, brain: 0.5, forget: 0.5, sleep: 1, dream: 0.5, city: 0.5, nightmare: 0, final: 1, outro: 1 }[c.scene];
  if (!step) continue;
  const notes = arp[c.name];
  let i = 0;
  for (let t = c.t0 + 0.2; t < c.t1 - 0.3; t += step, i++) {
    if (t > ev.silenceStart - 0.3 && t < ev.silenceEnd) continue;
    const midi = m(notes[(c.scene === 'dream' ? i * 2 : i) % notes.length]) + (c.scene === 'dream' && i % 4 === 3 ? 12 : 0);
    const mb = I.musicBox(midi); const g = c.scene === 'dream' ? 0.17 : 0.13;
    keys.addMono(mb, t, g, ((i % 5) - 2) * 0.25); verb.addMono(mb, t, 0.2); dly.addMono(mb, t, 0.07);
  }
}
// city: a quiet electronic pulse; nightmare: heartbeat; forgetting: low ticks that thin out
const K = I.kick();
for (let t = S.city[0] + 1; t < S.city[1] - 1; t += 0.5) pulse.addMono(I.bass(m('A2'), 0.18, { bright: 0.6 }), t, 0.12);
for (let t = S.nightmare[0] + 0.1; t < S.nightmare[1]; t += 0.95) { pulse.addMono(K, t, 0.5); pulse.addMono(K, t + 0.27, 0.28); }
for (let t = S.forget[0] + 1; t < ev.forgetWord; t += 1.0) pulse.addMono(I.thud(120 - (t - S.forget[0]) * 0.8, 0.06), t, 0.2);

// fx tied to the picture
fx.addMono(I.noiseSweep(3.0, 300, 6000, { q: 1, pink: true }), S.title[0] - 1.5, 0.18);            // into the title
fx.addMono(I.subBoom(2.4), ev.titleIn, 0.5);
fx.addMono(I.noiseSweep(1.6, 8000, 300, { q: 1, pink: true }), ev.forgetWord - 1.0, 0.25);
fx.addMono(I.subBoom(1.8), ev.forgetWord, 0.55);
fx.addMono(I.noiseSweep(4.0, 200, 5000, { q: 1, pink: true, shape: (x) => x * x }), S.nightmare[1] - 4.2, 0.3); // riser out of the nightmare
fx.addMono(I.subBoom(2.0), ev.end + 0.4, 0.45);

const out = path.join(__dirname, 'out');
const vo = Voice.speak(sc.LINES.map((l) => ({ at: l.at, text: l.tts, voice: l.voice, rate: l.rate, display: l.show, ...(l.id === 'dreamt' ? { gain: 0.9 } : {}) })), { out, engine: 'espeak-ng', length: DURATION, gain: 1.7 });

const stems = { pad, bass, keys, fx, pulse, verb: reverb(verb, { room: 0.88, damp: 0.35 }), dly: pingpong(dly, 0.75, 0.4, 3200) };
const GAIN = { pad: 1.9, bass: 0.8, keys: 1, fx: 0.9, pulse: 1, verb: 1, dly: 1 };
const music = MIX.mixdown(stems, GAIN, {});
MIX.duck([music], vo.bus, { depth: 0.55 });
// the held silence before the question (music and reverb tails gone)
const fadeA = ev.silenceStart + 0.3;
for (let i = Math.floor(fadeA * SR); i < Math.floor(ev.silenceEnd * SR); i++) { const k = Math.max(0, 1 - (i / SR - fadeA) / 0.5); music.L[i] *= k; music.R[i] *= k; }
// the nightmare ends on a hard cut
const mix = MIX.mixdown({ music, voice: vo.bus }, { music: 0.7, voice: 1 }, {});
MIX.highpass(mix, 22);
MIX.fadeOut(mix, DURATION - 3.5, DURATION);
const M = MIX.master(mix, 0.8, undefined, { lufs: process.env.LUFS ? parseFloat(process.env.LUFS) : -16 });
MIX.writeWav(path.join(out, 'music.wav'), mix);
console.log(`wrote out/music.wav (${DURATION.toFixed(1)}s, voice engine ${vo.engine}${M.lufs !== undefined ? `, ${M.lufs.toFixed(1)} LUFS` : ''})`);
