// build_extension.js — 拡張機能（vscode/）に、ハエの脳の部品と学習済みの結合をコピーする
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const dst = path.join(ROOT, "vscode/brain");
fs.mkdirSync(dst, { recursive: true });
const files = [
  [path.resolve(ROOT, "../fly-core/js/mb_spiking.js"), "mb_spiking.js"],
  [path.resolve(ROOT, "../fly-core/data/mb_circuit.json"), "mb_circuit.json"],
  [path.join(ROOT, "js/word_completer.js"), "word_completer.js"],
  [path.join(ROOT, "data/alphabet.json"), "alphabet.json"],
  [path.join(ROOT, "data/brain.json"), "brain.json"],
];
for (const [src, name] of files) {
  fs.copyFileSync(src, path.join(dst, name));
  console.log(`コピー: ${name}`);
}
