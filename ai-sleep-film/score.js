// SCORE — single source of truth: narration timing (lines.js), scenes, chords, markers.
(function () {
  const node = typeof require !== 'undefined';
  const U = node ? require('./engine/util') : globalThis.U;
  const MU = node ? require('./engine/music') : globalThis.MUSIC;
  const NARR = node ? require('./lines.js') : globalThis.NARR;
  const { makeClock } = MU;
  const FPS = 30;
  const FORMAT = U.pickFormat('16:9');
  const [W, H] = U.formatSize(FORMAT);
  const SAFE = U.safeArea(W, H);
  const clock = makeClock({ bpm: 60, offset: 0 }); // 1 bar = 4 s
  const { T, BEAT } = clock;
  const LINES = NARR.LINES;
  const END = NARR.END_NARR;
  const DURATION = END + NARR.OUTRO;

  // scenes: consecutive lines with the same scene name; each begins slightly before its first line
  const S = {};
  const order = [];
  LINES.forEach((l) => { if (!S[l.scene]) { S[l.scene] = [order.length ? Math.max(0, l.at - 0.5) : 0, END]; order.push(l.scene); } });
  order.forEach((k, i) => { if (i > 0) S[order[i - 1]][1] = S[k][0]; });
  S.outro = [END, DURATION];
  const line = (id) => LINES.find((l) => l.id === id);

  const ev = {
    answer: line('hook2').at + 2.2,        // the AI's reply appears
    titleIn: line('hook3').at + 0.2,
    forgetWord: line('forget').at + line('forget').dur * 0.72, // "Catastrophic Forgetting"
    dreamt: line('dreamt').at,
    silenceStart: line('dreamt').at + line('dreamt').dur,
    silenceEnd: line('ask').at - 0.15,
    end: END,
  };

  // chords: one per bar, progression depends on the scene (notes as names for I.padNote)
  const CH = {
    Am: { notes: ['A3', 'C4', 'E4'], bass: 'A1' }, F: { notes: ['A3', 'C4', 'F4'], bass: 'F1' },
    C: { notes: ['G3', 'C4', 'E4'], bass: 'C2' }, G: { notes: ['G3', 'B3', 'D4'], bass: 'G1' },
    Dm: { notes: ['A3', 'D4', 'F4'], bass: 'D2' }, Em: { notes: ['G3', 'B3', 'E4'], bass: 'E2' },
    Fmaj: { notes: ['A3', 'C4', 'E4', 'G4'], bass: 'F1' }, Dis: { notes: ['Bb3', 'Eb4', 'Gb4'], bass: 'Eb1' },
  };
  const PROG = {
    room: ['Am', 'F'], title: ['Am', 'F', 'C', 'G'], brain: ['Am', 'G', 'F', 'G'], forget: ['Dm', 'Am', 'Dm', 'Em'],
    sleep: ['F', 'C', 'F', 'Am'], dream: ['C', 'G', 'Am', 'F'], city: ['Am', 'F', 'C', 'G'], nightmare: ['Dis', 'Am'],
    final: ['Am', 'F'], outro: ['F', 'Fmaj'],
  };
  const chords = [];
  for (const k of [...order, 'outro']) {
    const [a, b] = S[k];
    let i = 0;
    for (let t = a; t < b - 0.01; t += 4, i++) {
      const name = PROG[k][i % PROG[k].length];
      chords.push({ scene: k, name, t0: t, t1: Math.min(b, t + 4.2), ...CH[name] });
    }
  }
  const sceneAt = (t) => { for (const k of [...order, 'outro']) if (t >= S[k][0] && t < S[k][1]) return k; return 'outro'; };

  const markers = { answer: ev.answer, title: ev.titleIn, forgetting: ev.forgetWord, dreamt: ev.dreamt, silence: ev.silenceStart, end: ev.end };
  for (const k of [...order, 'outro']) markers['sc_' + k] = S[k][0] + 1.5;

  const SCORE = { FPS, FORMAT, W, H, SAFE, WIDE: true, DURATION, clock, T, BEAT, S, order, ev, LINES, markers, chords, sceneAt, line };
  if (node) module.exports = SCORE; else globalThis.SCORE = SCORE;
})();
