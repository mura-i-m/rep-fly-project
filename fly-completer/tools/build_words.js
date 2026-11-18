/*
 * build_words.js — 30区画にPythonの単語を1つずつ割り当てる
 *
 * MBON を「主にどのドーパミン細胞（タイプ×左右）が入るか」で分けると30区画になる。
 * 出てくる回数が多い単語ほど、MBON の多い（＝安定した）区画に割り当てる。
 * 文字 → 香り分子の対応は build_alphabet.js が作った data/alphabet.json の input を使う。
 *
 * 使い方: node tools/build_words.js  →  data/alphabet.json に words を追加
 */
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const alphabet = JSON.parse(fs.readFileSync(path.join(ROOT, "data/alphabet.json"), "utf8"));
const corpus = fs.readFileSync(path.join(ROOT, "corpus/train.py"), "utf8");

const WORDS = [
  "def", "return", "self", "import", "from", "class", "None", "True", "False", "print",
  "range", "len", "for", "while", "elif", "else", "except", "raise", "lambda", "yield",
  "with", "append", "not", "and", "try", "assert", "continue", "break", "isinstance", "str",
];
const count = (w) => (corpus.match(new RegExp(`\\b${w}\\b`, "g")) || []).length;
const words = WORDS.map((w) => [w, count(w)]).sort((a, b) => b[1] - a[1]);

// 区画は build_alphabet.js が作った output（MBON の多い順）をそのまま使う
alphabet.words = alphabet.output.map((u, i) => ({
  word: words[i][0],
  count: words[i][1],
  compartment: u.compartment,
  mbons: u.mbons,
  mbonTypes: u.mbonTypes,
  dans: u.dans,
}));
fs.writeFileSync(path.join(ROOT, "data/alphabet.json"), JSON.stringify(alphabet, null, 1));
console.log(alphabet.words.map((w) => `${w.word}(${w.count})←${w.compartment}/MBON${w.mbons.length}`).join("  "));
