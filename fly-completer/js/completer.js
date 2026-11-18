/*
 * completer.js — ハエのキノコ体で「次の1文字」を当てる
 *
 *  1. 直前の数文字を、文字ごとの香り分子の「残り香」として混ぜる
 *     （いちばん新しい文字が濃く、古い文字ほど薄い）
 *  2. その匂いをキノコ体（スパイクモデル）に嗅がせる
 *  3. 区画ごとの MBON の反応が「学習前と比べてどれだけ黙ったか」を見て、
 *     いちばん黙った区画の文字を答えにする
 *     （ドーパミンで学習すると、その匂いへの MBON の反応が下がる）
 *  4. 間違えたら、正解の区画のドーパミン細胞を発火させて学習する
 *
 * Node でもブラウザでも動く（VSCode 拡張機能から直接呼ぶ）
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("../../fly-core/js/mb_spiking.js"));
  else root.FlyCompleter = factory(root.FlyMB);
})(typeof self !== "undefined" ? self : this, function (FlyMB) {
  "use strict";

  class FlyCompleter {
    constructor(circuit, alphabet, opt = {}) {
      this.opt = Object.assign({
        contextLen: 4,     // 何文字前まで嗅ぐか
        decay: 0.45,       // 1文字さかのぼるごとの残り香の濃さ
        strength: 1.0,     // 匂いの濃さ
        window: 50,        // 1回に嗅ぐ時間（ms）
        readout: "suppression", // "suppression"（学習前比）または "spikes"
        margin: 0.03,      // これより僅差なら正解でも学習する
      }, opt);
      this.mb = new FlyMB.MushroomBody(circuit, opt.mb || {});
      this.alphabet = alphabet;
      this.nG = circuit.glomeruli.length;

      // 文字 → 糸球体の反応（大きさを揃える）
      this.odor = {};
      for (const [ch, name] of Object.entries(alphabet.input)) {
        const v = new Float32Array(this.nG);
        for (const [g, x] of circuit.odor_library[name].g) v[g] = x;
        const n = Math.hypot(...v) || 1;
        for (let i = 0; i < this.nG; i++) v[i] /= n;
        this.odor[ch] = v;
      }
      this.units = alphabet.output;
      this.charToUnit = new Map(this.units.map((u, i) => [u.char, i]));
      this.stats = { seen: 0, correct: 0 };
    }

    /** 入力中のテキストの末尾 → 嗅ぐ文字の列（行頭のインデントは1つの空白にまとめる） */
    context(text) {
      const t = text.replace(/[ \t]+/g, " ");
      return [...t.slice(-this.opt.contextLen)];
    }

    smell(chars) {
      const { decay, strength } = this.opt;
      const g = new Float32Array(this.nG);
      let c = strength;
      for (let i = chars.length - 1; i >= 0; i--) {
        const v = this.odor[chars[i]] || this.odor["<other>"];
        for (let k = 0; k < this.nG; k++) g[k] += v[k] * c;
        c *= decay;
      }
      return g;
    }

    /**
     * 次の1文字を予測する
     * @returns {{char, unit, scores, margin, activity}}
     */
    predict(text, onStep) {
      const chars = this.context(text);
      this.mb.setOdor(this.smell(chars));
      this.mb.resetActivity();
      const r = this.mb.run(this.opt.window, onStep);
      const scores = this.units.map((u) => {
        if (this.opt.readout === "spikes") {
          return u.mbons.reduce((s, m) => s + r.mbonSpikes[m], 0) / u.mbons.length;
        }
        let a = 0, b = 0;
        for (const m of u.mbons) { a += r.mbonIn[m]; b += r.mbonNaive[m]; }
        return b > 0 ? a / b : 1; // 1 = 学習前と同じ、0 = 完全に黙った
      });
      const order = scores.map((s, i) => [s, i]).sort((x, y) => x[0] - y[0]);
      const unit = order[0][1];
      return {
        char: this.units[unit].char,
        unit,
        scores,
        margin: order[1][0] - order[0][0],
        ranking: order.slice(0, 5).map(([s, i]) => [this.units[i].char, s]),
        activity: r,
      };
    }

    /** 予測 → 答え合わせ → 必要なら学習。正解の文字が語彙にないときは何もしない */
    train(text, nextChar) {
      const target = this.charToUnit.get(nextChar);
      if (target === undefined) return null;
      const p = this.predict(text);
      const ok = p.unit === target;
      this.stats.seen++; if (ok) this.stats.correct++;
      if (!ok || p.margin < this.opt.margin) {
        // 正解の区画にドーパミン → この匂いに対して黙るようになる
        this.mb.dopamine(this.units[target].dans, -1);
        // 間違えて選んだ区画は少し元に戻す
        if (!ok) this.mb.dopamine(this.units[p.unit].dans, +1);
      }
      return { ok, pred: p.char };
    }

    /** 数文字先まで続けて予測する（確信が持てるあいだだけ） */
    complete(text, maxLen = 6, minMargin = 0.02) {
      let out = "";
      for (let i = 0; i < maxLen; i++) {
        const p = this.predict(text + out);
        if (p.margin < minMargin || p.char === "\n") break;
        out += p.char;
        if (/[\s(:)]/.test(p.char)) break;
      }
      return out;
    }

    save() { return { plastic: this.mb.exportPlastic(), stats: this.stats }; }
    load(state) { this.mb.importPlastic(state.plastic); this.stats = state.stats || this.stats; }
  }

  return FlyCompleter;
});
