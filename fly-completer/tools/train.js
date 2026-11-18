/*
 * train.js — Python のコードを1文字ずつハエに嗅がせて学習させる
 *
 * 使い方: node tools/train.js [学習する文字数=20000] [つまみ JSON]
 *   例: node tools/train.js 30000 '{"mb":{"kcGain":1.6}}'
 * 出力: data/brain.json（学習した結合）
 */
const fs = require("fs");
const path = require("path");
const FlyCompleter = require("../js/completer.js");
const ROOT = path.resolve(__dirname, "..");
const circuit = JSON.parse(fs.readFileSync(path.resolve(ROOT, "../fly-core/data/mb_circuit.json"), "utf8"));
const alphabet = JSON.parse(fs.readFileSync(path.join(ROOT, "data/alphabet.json"), "utf8"));

const N = Number(process.argv[2] || 20000);
const opt = JSON.parse(process.argv[3] || "{}");
const fly = new FlyCompleter(circuit, alphabet, opt);

// 行頭のインデントの途中は予測しない（補完で役に立たないので）
function positions(text) {
  const pos = [];
  let lineStart = true;
  for (let i = 1; i < text.length; i++) {
    const ch = text[i - 1];
    if (ch === "\n") lineStart = true;
    else if (ch !== " ") lineStart = false;
    if (lineStart && text[i] === " ") continue;
    pos.push(i);
  }
  return pos;
}

const train = fs.readFileSync(path.join(ROOT, "corpus/train.py"), "utf8");
const test = fs.readFileSync(path.join(ROOT, "corpus/test.py"), "utf8");
const trainPos = positions(train);
const testPos = positions(test);

function evaluate(n = 1500) {
  let ok = 0, cnt = 0;
  const step = Math.floor(testPos.length / n);
  for (let k = 0; k < n; k++) {
    const i = testPos[k * step];
    if (!fly.charToUnit.has(test[i])) continue;
    cnt++;
    if (fly.predict(test.slice(Math.max(0, i - 8), i)).char === test[i]) ok++;
  }
  return ok / cnt;
}

const demos = ["de", "    def __in", "    ret", "imp", "sel", "for i in ra", "    if x is No", "print"];
function showDemos() {
  return demos.map((s) => `${JSON.stringify(s)}→${JSON.stringify(fly.predict(s).char)}`).join("  ");
}

const t0 = Date.now();
console.log(`学習前  テスト正解率 ${(evaluate() * 100).toFixed(1)}%`);
let i0 = 0, recent = 0, recentN = 0;
const start = Math.floor(Math.random() * 0) ; // 先頭から順に
for (let n = 0; n < N; n++) {
  const i = trainPos[(start + n) % trainPos.length];
  const r = fly.train(train.slice(Math.max(0, i - 8), i), train[i]);
  if (r) { recentN++; if (r.ok) recent++; }
  if ((n + 1) % Math.max(1, Math.floor(N / 8)) === 0) {
    const sec = ((Date.now() - t0) / 1000).toFixed(0);
    console.log(`${n + 1}文字  学習中の正解率 ${(recent / recentN * 100).toFixed(1)}%  テスト ${(evaluate() * 100).toFixed(1)}%  (${sec}秒)`);
    recent = 0; recentN = 0;
  }
}
console.log(showDemos());
fs.writeFileSync(path.join(ROOT, "data/brain.json"), JSON.stringify({ opt, ...fly.save() }));
