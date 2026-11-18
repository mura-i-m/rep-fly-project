/*
 * build_alphabet.js — 文字とハエの脳をつなぐ表を作る
 *
 *  入力：1文字ごとに、実在の香り分子（DoOR）を1つ割り当てる
 *        よく使う文字ほど、ほかの文字と似ていない匂いを先に選ぶ
 *  出力：MBON を「主にどのドーパミン細胞（タイプ×左右）が入るか」で区画に分け、
 *        区画1つ = 予測する文字1つ とする。区画の数がそのまま語彙の大きさになる
 *
 * 使い方: node tools/build_alphabet.js  →  data/alphabet.json
 */
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const CIRCUIT = path.resolve(ROOT, "../fly-core/data/mb_circuit.json");
const d = JSON.parse(fs.readFileSync(CIRCUIT, "utf8"));
const corpus = fs.readFileSync(path.join(ROOT, "corpus/train.py"), "utf8");

// ---------- 文字の出現回数（行頭のインデントは数えない）
const freq = new Map();
for (const line of corpus.split("\n")) {
  const body = line.replace(/^\s+/, "") + "\n";
  for (const ch of body) freq.set(ch, (freq.get(ch) || 0) + 1);
}
const byFreq = [...freq.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);

// ---------- 出力：区画を作る
const nM = d.mbon.body.length;
const unitOf = new Map(); // "PPL103_R" → MBON の配列
const D = Array.from({ length: d.dan.body.length }, () => new Float64Array(nM));
for (const [a, b, x] of d.dan_mbon) D[a][b] += x;
const danKey = d.dan.type.map((t, i) => `${t}_${d.dan.side[i]}`);
const keys = [...new Set(danKey)];
for (let m = 0; m < nM; m++) {
  const s = new Map();
  danKey.forEach((k, i) => s.set(k, (s.get(k) || 0) + D[i][m]));
  const [best] = [...s.entries()].sort((a, b) => b[1] - a[1])[0];
  if (!unitOf.has(best)) unitOf.set(best, []);
  unitOf.get(best).push(m);
}
// MBON が多い区画ほど安定するので、よく出る文字を割り当てる
const units = [...unitOf.entries()].sort((a, b) => b[1].length - a[1].length);
const outChars = byFreq.slice(0, units.length);
const output = units.map(([key, mbons], i) => ({
  char: outChars[i],
  compartment: key,
  mbons,
  mbonTypes: [...new Set(mbons.map((m) => d.mbon.type[m]))],
  dans: danKey.map((k, j) => (k === key ? j : -1)).filter((j) => j >= 0),
}));

// ---------- 入力：文字 → 香り分子
const nG = d.glomeruli.length;
const lib = Object.entries(d.odor_library)
  .filter(([name]) => !/water|solvent|paraffin|mineral oil/i.test(name))
  .map(([name, o]) => {
    const v = new Float64Array(nG);
    for (const [g, x] of o.g) v[g] = x;
    const norm = Math.hypot(...v);
    return { name, v, norm, measured: o.measured };
  })
  .filter((o) => o.norm > 0.3);
const cos = (a, b) => { let s = 0; for (let i = 0; i < nG; i++) s += a.v[i] * b.v[i]; return s / (a.norm * b.norm); };

const N_IN = Math.min(64, lib.length - 1);
const chosen = [];
const pool = lib.slice().sort((a, b) => b.norm - a.norm);
chosen.push(pool.shift());
while (chosen.length < N_IN) {
  let best = -1, bestScore = Infinity;
  pool.forEach((o, i) => {
    const s = Math.max(...chosen.map((c) => cos(o, c)));
    if (s < bestScore) { bestScore = s; best = i; }
  });
  chosen.push(pool.splice(best, 1)[0]);
}
const input = {};
byFreq.slice(0, N_IN - 1).forEach((ch, i) => { input[ch] = chosen[i].name; });
input["<other>"] = chosen[N_IN - 1].name;

const out = { note: "文字 → 香り分子（DoOR）と、予測の区画（MBON とドーパミン細胞）", input, output };
fs.writeFileSync(path.join(ROOT, "data/alphabet.json"), JSON.stringify(out, null, 1));
console.log(`区画（=予測できる文字）: ${units.length}`);
console.log(output.map((o) => `${JSON.stringify(o.char)}←${o.compartment}(MBON${o.mbons.length})`).join("  "));
console.log(`\n入力の文字: ${Object.keys(input).length}`);
console.log(Object.entries(input).slice(0, 12).map(([c, n]) => `${JSON.stringify(c)}=${n}`).join(", "), "…");
