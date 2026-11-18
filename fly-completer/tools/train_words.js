/*
 * train_words.js — 単語の先頭を嗅がせて、どの単語か当てさせる
 *
 * 使い方: node tools/train_words.js [学習回数=6000] [周回=2]
 * 出力: data/brain.json（学習した結合。VSCode 拡張機能が読み込む）
 */
const fs = require("fs");
const path = require("path");
const FlyWordCompleter = require("../js/word_completer.js");
const { mulberry32 } = require("../../fly-core/js/mb_spiking.js");
const ROOT = path.resolve(__dirname, "..");
const circuit = JSON.parse(fs.readFileSync(path.resolve(ROOT, "../fly-core/data/mb_circuit.json"), "utf8"));
const alphabet = JSON.parse(fs.readFileSync(path.join(ROOT, "data/alphabet.json"), "utf8"));

const N = Number(process.argv[2] || 6000);
const EPOCHS = Number(process.argv[3] || 2);
const opt = JSON.parse(process.argv[4] || '{"readout":"ratio","confine":true,"consolidate":0.005,"mb":{"danUniform":true,"lr":0.03,"lrUp":0.03}}');
const fly = new FlyWordCompleter(circuit, alphabet, opt);
const words = alphabet.words.map((w) => w.word);

// コード中の出現位置から「直前3文字＋単語の先頭1〜3文字」を作る
function samples(file, n, seed) {
  const t = fs.readFileSync(path.join(ROOT, "corpus", file), "utf8");
  const re = new RegExp(`\\b(${words.join("|")})\\b`, "g");
  const occ = [];
  let m;
  while ((m = re.exec(t))) occ.push([m.index, m[1]]);
  const rnd = mulberry32(seed);
  // よく出る単語ばかりにならないよう、単語ごとの出やすさを回数の平方根にならす
  const byWord = new Map();
  for (const o of occ) { if (!byWord.has(o[1])) byWord.set(o[1], []); byWord.get(o[1]).push(o); }
  const ws = [...byWord.keys()];
  const wt = ws.map((w) => Math.sqrt(byWord.get(w).length));
  const tot = wt.reduce((a, b) => a + b, 0);
  const pick = () => { let r = rnd() * tot; for (let j = 0; j < ws.length; j++) { r -= wt[j]; if (r <= 0) return ws[j]; } return ws[ws.length - 1]; };
  const out = [];
  for (let k = 0; k < n; k++) {
    const list = byWord.get(pick());
    const [i, w] = list[Math.floor(rnd() * list.length)];
    const L = 1 + Math.floor(rnd() * Math.min(3, w.length - 1));
    out.push([t.slice(Math.max(0, i - 3), i + L), w]);
  }
  return out;
}

const train = samples("train.py", N, 1);
const test = samples("test.py", 800, 2);

function evaluate() {
  fly.mb.opt.useLongTerm = true;
  let ok = 0, okLong = 0, nLong = 0;
  for (const [s, w] of test) {
    const hit = fly.predict(s).word === w;
    ok += hit;
    if (s.match(/[A-Za-z_]+$/)[0].length >= 2) { nLong++; okLong += hit; }
  }
  fly.mb.opt.useLongTerm = false;
  return [ok / test.length, okLong / nLong];
}

const demos = ["    de", "    ret", "(sel", "\nimp", "\nfro", " = No", " = Tr", "pri", "for i in ra", "    whi", "lamb", "    ex"];

const t0 = Date.now();
for (let e = 0; e < EPOCHS; e++) {
  let ok = 0;
  train.forEach(([s, w], i) => {
    if (fly.train(s, w).ok) ok++;
    if ((i + 1) % 2000 === 0) process.stdout.write(".");
  });
  const [all, long] = evaluate();
  console.log(`\n周回${e + 1}  学習中 ${(ok / train.length * 100).toFixed(1)}%  テスト ${(all * 100).toFixed(1)}%（2文字以上打った時 ${(long * 100).toFixed(1)}%）  ${((Date.now() - t0) / 1000).toFixed(0)}秒`);
}
fly.mb.opt.useLongTerm = true;
console.log(demos.map((s) => { const c = fly.complete(s); return `${JSON.stringify(s)}→${c.prefix || ""}[${c.suffix}]`; }).join("  "));
fs.writeFileSync(path.join(ROOT, "data/brain.json"), JSON.stringify({ opt, ...fly.save() }));
console.log(`保存: data/brain.json (${(fs.statSync(path.join(ROOT, "data/brain.json")).size / 1e6).toFixed(1)} MB)`);
