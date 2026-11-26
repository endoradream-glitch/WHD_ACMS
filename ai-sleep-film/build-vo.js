// Synthesizes every narration line (cached), measures it, and writes lines.js with the start time of each line.
const fs = require('fs'), path = require('path');
const Voice = require('./engine/audio/voice');
const SCRIPT = require('./script');
const LEAD = 2.2, RATE = +(process.env.RATE || 135);
const probe = Voice.speak(SCRIPT.map((l) => ({ at: 0, text: l.tts, voice: l.voice || 'bn', rate: RATE })), { out: 'out', engine: 'espeak-ng', save: false });
let t = LEAD;
const lines = SCRIPT.map((l, i) => {
  const dur = probe.lines[i].end - probe.lines[i].t;
  const o = { id: l.id, scene: l.scene, at: +t.toFixed(2), dur: +dur.toFixed(2), tts: l.tts, show: l.show, voice: l.voice || 'bn', rate: RATE };
  t += dur + l.gap; return o;
});
const END = t + 1.5, OUTRO = 7;
const js = `(function(){const D={LINES:${JSON.stringify(lines)},END_NARR:${END.toFixed(2)},OUTRO:${OUTRO}};if(typeof module!=='undefined')module.exports=D;else globalThis.NARR=D;})();\n`;
fs.writeFileSync(path.join(__dirname, 'lines.js'), js);
console.log(lines.map((l) => `${l.at.toFixed(1)}s +${l.dur.toFixed(1)} ${l.id}`).join('\n'), `\nnarration ends ${END.toFixed(1)}s, total ${(END + OUTRO).toFixed(1)}s`);
