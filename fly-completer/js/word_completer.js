/*
 * word_completer.js — ハエのキノコ体で「打ちかけの単語」を当てる
 *
 *  1. 直前の数文字を、文字ごとの香り分子の「残り香」として混ぜて嗅がせる
 *     （いちばん新しい文字が濃く、古い文字ほど薄い）
 *  2. キノコ体（スパイクモデル）が反応する
 *  3. MBON の30区画それぞれに1単語を割り当ててある。
 *     「学習前と比べて入力がいちばん減った（＝黙った）区画」の単語が答え
 *  4. 間違えたら、正解の区画のドーパミン細胞を発火させてその匂いを覚えさせ、
 *     間違えて選んだ区画は少し元に戻す
 *
 * Node でもブラウザでも動く（VSCode 拡張機能から直接呼ぶ）
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    let MB;
    try { MB = require("./mb_spiking.js"); } catch (e) { MB = require("../../fly-core/js/mb_spiking.js"); }
    module.exports = factory(MB);
  } else root.FlyWordCompleter = factory(root.FlyMB);
})(typeof self !== "undefined" ? self : this, function (FlyMB) {
  "use strict";

  const DEFAULT_MB = { pnGain: 3, pnMax: 300, kcGain: 1.2, aplKCGain: 4, mbonDrive: 2000, lr: 0.03, lrUp: 0.03, danUniform: true };

  class FlyWordCompleter {
    constructor(circuit, alphabet, opt = {}) {
      this.opt = Object.assign({
        contextLen: 4,   // 何文字前まで嗅ぐか
        decay: 0.45,     // 1文字さかのぼるごとの残り香の濃さ
        window: 200,     // 1回に嗅ぐ時間（ms、ハエの体感時間）
        consolidate: 0.005,
        readout: "ratio",// drop: 入力の減り量 / ratio: 減った割合 / sqrt: その中間
        confine: true,   // true: ドーパミンを担当区画の MBON だけに効かせる
      }, opt);
      this.mb = new FlyMB.MushroomBody(circuit, Object.assign({}, DEFAULT_MB, opt.mb || {}));
      this.nG = circuit.glomeruli.length;
      this.odor = {};
      for (const [ch, name] of Object.entries(alphabet.input)) {
        const v = new Float32Array(this.nG);
        for (const [g, x] of circuit.odor_library[name].g) v[g] = x;
        const n = Math.hypot(...v) || 1;
        for (let i = 0; i < this.nG; i++) v[i] /= n;
        this.odor[ch] = v;
      }
      this.odorName = alphabet.input;
      this.units = alphabet.words; // [{word, compartment, mbons, dans}]
      this.wordToUnit = new Map(this.units.map((u, i) => [u.word, i]));
      this.stats = { seen: 0, correct: 0 };
    }

    /** テキスト末尾 → 嗅ぐ文字の列（連続する空白は1つにまとめる） */
    context(text) {
      const t = text.replace(/[ \t]+/g, " ");
      return [...t.slice(-this.opt.contextLen)];
    }

    smell(chars) {
      const g = new Float32Array(this.nG);
      let c = 1;
      for (let i = chars.length - 1; i >= 0; i--) {
        const v = this.odor[chars[i]] || this.odor["<other>"];
        for (let k = 0; k < this.nG; k++) g[k] += v[k] * c;
        c *= this.opt.decay;
      }
      return g;
    }

    /**
     * 予測する。onStep(t, mb) は毎ステップ呼ばれる（タッピング・発火の可視化用）
     * @returns {{word, unit, scores, margin, ranking, odors, activity}}
     */
    predict(text, onStep) {
      const chars = this.context(text);
      this.mb.setOdor(this.smell(chars));
      this.mb.resetActivity();
      const r = this.mb.run(this.opt.window, onStep);
      const scores = this.units.map((u) => {
        let drop = 0, naive = 0;
        for (const m of u.mbons) { drop += r.mbonNaive[m] - r.mbonIn[m]; naive += r.mbonNaive[m]; }
        if (this.opt.readout === "ratio") return naive > 0 ? drop / naive : 0;
        if (this.opt.readout === "sqrt") return naive > 0 ? drop / Math.sqrt(naive) : 0;
        return drop;
      });
      const order = scores.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0]);
      const unit = order[0][1];
      return {
        word: this.units[unit].word,
        unit,
        scores,
        margin: order[0][0] - order[1][0],
        ranking: order.slice(0, 5).map(([s, i]) => [this.units[i].word, +s.toFixed(3)]),
        odors: chars.map((c) => [c, this.odorName[c] || this.odorName["<other>"]]),
        activity: r,
      };
    }

    /** 予測 → 答え合わせ → 間違えたら学習 */
    train(text, word) {
      const target = this.wordToUnit.get(word);
      if (target === undefined) return null;
      const useLT = this.mb.opt.useLongTerm;
      this.mb.opt.useLongTerm = false; // 学習中の答え合わせは短期の記憶で
      const p = this.predict(text);
      this.mb.opt.useLongTerm = useLT;
      const ok = p.unit === target;
      this.stats.seen++; if (ok) this.stats.correct++;
      if (!ok) {
        const lim = this.opt.confine;
        this.mb.dopamine(this.units[target].dans, -1, 1, lim ? this.units[target].mbons : null);
        this.mb.dopamine(this.units[p.unit].dans, +1, 1, lim ? this.units[p.unit].mbons : null);
      }
      this.mb.consolidate(this.opt.consolidate);
      return { ok, pred: p.word };
    }

    /**
     * 補完：打ちかけの単語 prefix に対し、ハエの答えが prefix で始まるときだけ残りを返す
     * （合わないときは「わからない」として何も出さない）
     */
    complete(text, onStep) {
      const m = text.match(/[A-Za-z_]+$/);
      if (!m) return { suffix: "", prediction: null };
      const prefix = m[0];
      const p = this.predict(text, onStep);
      const ok = p.word.startsWith(prefix) && p.word.length > prefix.length;
      return { suffix: ok ? p.word.slice(prefix.length) : "", prefix, prediction: p };
    }

    save() { return { plastic: this.mb.exportPlastic(), stats: this.stats }; }
    load(state) {
      this.mb.importPlastic(state.plastic);
      this.stats = state.stats || this.stats;
      this.mb.opt.useLongTerm = true;
    }
  }

  return FlyWordCompleter;
});
