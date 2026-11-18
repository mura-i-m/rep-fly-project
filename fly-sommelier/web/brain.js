// brain.js — ハエの嗅覚回路モデル（UI から独立。Node でもテストできる）
//
//  香り → 糸球体 → 投射ニューロン(PN) ─┬→ ケニオン細胞(KC) → MBON（キノコ体：教わった好み）
//                                      └→ 側角(LH)              （生まれつきの好み）
//
//  学習：👍/👎 でドーパミン細胞（PAM=ごほうび / PPL1=罰）が発火し、
//        その区画で「いま発火した KC → MBON」の結合を弱める（本物のハエで知られている可塑性）。
//  MBON → ドーパミン細胞のフィードバックは本物の配線。グルタミン酸の符号は切り替えられる。

(function (root) {
  const KC_FRACTION = 0.05;   // 発火させる KC の割合（APL ニューロンによる抑制のまね）
  const ETA = 0.25;           // ドーパミン1単位あたり、結合をどれだけ弱めるか
  const RECOVER = 0.05;       // ドーパミンがないときに元に戻る速さ（忘却）
  const FEEDBACK = 2.0;       // MBON → ドーパミン細胞のフィードバックの強さ
  const INNATE_GAIN = 25.0;   // 生まれつきの好みの目盛り合わせ

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  class FlyBrain {
    constructor(data, { randomWiring = false, glutamateExcites = true, seed = 1 } = {}) {
      this.data = data;
      this.G = data.glomeruli.length;
      this.P = data.n_pn;
      this.K = data.n_kc;
      this.M = data.mbon_types.length;
      this.D = data.dan_types.length;
      this.kActive = Math.round(this.K * KC_FRACTION);
      this.randomWiring = randomWiring;
      this.glutamateExcites = glutamateExcites;

      // ---- 入口：糸球体 → PN
      this.glomPn = data.glom_pn;
      this.compounds = {};
      for (const [name, c] of Object.entries(data.compounds)) {
        const v = new Float64Array(this.G);
        for (const [i, x] of c.g) v[i] = x;
        this.compounds[name] = v;
      }

      // ---- PN → KC
      this.kcInputs = Array.from({ length: this.K }, () => []);
      for (const [k, p, w] of data.pn_kc) this.kcInputs[k].push([p, w]);
      if (randomWiring) {
        const rand = mulberry32(seed);
        for (const inputs of this.kcInputs) {
          const used = new Set();
          for (const inp of inputs) {
            let p;
            do { p = Math.floor(rand() * this.P); } while (used.has(p));
            used.add(p); inp[0] = p;
          }
        }
      }

      // ---- KC → MBON（本物のシナプス数が初期値）
      this.W0 = new Float64Array(this.K * this.M);
      for (const [k, m, w] of data.kc_mbon) this.W0[k * this.M + m] = w;
      this.mbonSize = new Float64Array(this.M);
      for (let k = 0; k < this.K; k++) for (let m = 0; m < this.M; m++) this.mbonSize[m] += this.W0[k * this.M + m];
      this.mbonBase = this.mbonSize.map((s) => s / this.K);
      this.sign = data.mbon_sign;              // +1 近づく / −1 避ける
      this.isPam = data.dan_types.map((d) => d.startsWith("PAM"));

      // ---- ドーパミン細胞 → 区画（MBON）
      this.danMbon = data.dan_mbon;            // [D][M]、MBON ごとに合計1
      // ---- MBON → ドーパミン細胞（神経伝達物質で符号を付け、ドーパミン細胞ごとに正規化）
      this.setGlutamate(glutamateExcites);

      // ---- 側角：生まれつきの好み
      const val = new Float64Array(this.G);
      for (const [g, o] of Object.entries(data.innate.glomeruli)) {
        const i = data.glomeruli.indexOf(g);
        if (i >= 0) val[i] = o.valence;
      }
      this.glomValence = val;
      const pnVal = new Float64Array(this.P), pnTot = new Float64Array(this.P);
      for (const [g, p, w] of this.glomPn) { pnVal[p] += w * val[g]; pnTot[p] += w; }
      const L = data.lh_types.length;
      this.L = L;
      this.pnLh = data.pn_lh;
      const lhIn = new Float64Array(L), lhVal = new Float64Array(L);
      for (const [p, l, w] of this.pnLh) { lhIn[l] += w; lhVal[l] += w * pnVal[p]; }
      this.lhIn = lhIn;
      this.lhVal = lhVal.map((v, l) => (lhIn[l] ? v / lhIn[l] : 0));

      this.reset();
    }

    setGlutamate(excites) {
      this.glutamateExcites = excites;
      const s = { acetylcholine: 1, gaba: -1, glutamate: excites ? 1 : -1 };
      const F = this.data.mbon_dan.map((row, m) => row.map((x) => x * (s[this.data.mbon_nt[m]] || 0)));
      const tot = new Float64Array(this.D);
      F.forEach((row) => row.forEach((x, d) => (tot[d] += Math.abs(x))));
      this.F = F.map((row) => row.map((x, d) => (tot[d] ? x / tot[d] : 0)));
    }

    reset() {
      this.W = Float64Array.from(this.W0);
      this.history = []; // 学習ごとのドーパミン量など
    }

    // ワイン（品種＋香りの言葉）→ 分子の混ざり具合
    mixture(variety, notes = []) {
      const wine = this.data.wine;
      const m = {};
      const add = (obj) => { for (const [k, v] of Object.entries(obj)) if (!k.startsWith("_")) m[k] = (m[k] || 0) + v; };
      add(wine.base);
      if (variety && wine.varieties[variety]) add(wine.varieties[variety].aroma);
      for (const n of notes) if (wine.descriptors[n]) add(wine.descriptors[n]);
      return m;
    }

    // 嗅ぐ：入口から MBON・側角までの活動をまとめて返す
    sniff(mix) {
      const glom = new Float64Array(this.G);
      for (const [name, amount] of Object.entries(mix)) {
        const v = this.compounds[name];
        if (v) for (let i = 0; i < this.G; i++) glom[i] += amount * v[i];
      }
      const pin = new Float64Array(this.P);
      for (const [g, p, w] of this.glomPn) pin[p] += glom[g] * w;
      let S = 0; for (const x of pin) S += x;
      const pn = new Float64Array(this.P);
      const s15 = Math.pow(0.1, 1.5), m15 = Math.pow(0.04 * S, 1.5);
      for (let i = 0; i < this.P; i++) { const a = Math.pow(pin[i], 1.5); pn[i] = a / (a + s15 + m15); }

      const kcIn = new Float64Array(this.K);
      for (let k = 0; k < this.K; k++) {
        let s = 0; for (const [p, w] of this.kcInputs[k]) s += pn[p] * w; kcIn[k] = s;
      }
      const order = Array.from(kcIn.keys()).sort((a, b) => kcIn[b] - kcIn[a]);
      const active = order.slice(0, this.kActive).filter((k) => kcIn[k] > 0);

      // 側角
      const lh = new Float64Array(this.L);
      for (const [p, l, w] of this.pnLh) lh[l] += pn[p] * w;
      let lhSum = 0, lhVal = 0;
      for (let l = 0; l < this.L; l++) {
        if (!this.lhIn[l]) continue;
        const a = lh[l] / this.lhIn[l]; lh[l] = a; lhSum += a; lhVal += a * this.lhVal[l];
      }
      const raw = lhSum ? lhVal / lhSum : 0;
      // どのワインにも共通する土台の匂いとの差を「そのワインらしさへの生まれつきの反応」とする
      if (this.innateBase === undefined) { this.innateBase = null; this.innateBase = this.sniff(this.mixture()).rawInnate; }
      const innate = this.innateBase === null ? 0 : Math.max(-1, Math.min(1, INNATE_GAIN * (raw - this.innateBase)));

      return { glom, pn, active, lh, innate, rawInnate: raw, ...this.readout(active) };
    }

    // KC → MBON → 好き度
    mbonActivity(active, W) {
      const M = new Float64Array(this.M);
      if (!active.length) return M;
      for (const k of active) for (let m = 0; m < this.M; m++) M[m] += W[k * this.M + m];
      for (let m = 0; m < this.M; m++) M[m] /= this.mbonBase[m] * active.length || 1;
      return M;
    }
    valenceOf(M) {
      let num = 0, den = 0;
      for (let m = 0; m < this.M; m++) { num += this.sign[m] * this.mbonSize[m] * M[m]; den += this.mbonSize[m] * M[m]; }
      return den ? num / den : 0;
    }
    readout(active) {
      const mbon = this.mbonActivity(active, this.W);
      const naive = this.valenceOf(this.mbonActivity(active, this.W0));
      // 教わった好み：学習前の同じ匂いからの変化分（目盛りを ±1 付近に合わせる）
      const learned = Math.max(-1, Math.min(1, 2 * (this.valenceOf(mbon) - naive)));
      return { mbon, learned };
    }
    overall(s) { return Math.max(-1, Math.min(1, s.learned + 0.5 * s.innate)); }

    // ドーパミン細胞の活動：ごほうび/罰の入力 ＋ MBON からのフィードバック
    dopamine(mbon, r) {
      const d = new Float64Array(this.D);
      for (let i = 0; i < this.D; i++) {
        let fb = 0;
        for (let m = 0; m < this.M; m++) fb += this.F[m][i] * (mbon[m] - 1);
        const us = this.isPam[i] ? (r > 0 ? 1 : 0) : (r < 0 ? 1 : 0);
        d[i] = Math.max(0, us + FEEDBACK * fb);
      }
      return d;
    }

    // 評価 r（+1 好き / 0 ふつう / −1 苦手）で学習
    learn(smell, r) {
      const before = this.overall(smell);
      const dan = this.dopamine(smell.mbon, r);
      const da = new Float64Array(this.M); // 区画ごとに届くドーパミン
      for (let m = 0; m < this.M; m++) for (let i = 0; i < this.D; i++) da[m] += this.danMbon[i][m] * dan[i];
      for (const k of smell.active) {
        for (let m = 0; m < this.M; m++) {
          const j = k * this.M + m, a = Math.min(1, da[m]);
          this.W[j] *= 1 - ETA * a;
          this.W[j] += RECOVER * (1 - a) * (this.W0[j] - this.W[j]);
        }
      }
      let pam = 0, ppl1 = 0;
      dan.forEach((x, i) => (this.isPam[i] ? (pam += x) : (ppl1 += x)));
      const after = this.readout(smell.active);
      const rec = { r, before, pam, ppl1, surprise: r > 0 ? pam : r < 0 ? ppl1 : 0 };
      this.history.push(rec);
      return { ...rec, dan, da, after: this.overall({ ...after, innate: smell.innate }), mbonAfter: after.mbon };
    }

    overlap(a, b) {
      if (!a.length) return 0;
      const s = new Set(b); let n = 0;
      for (const k of a) if (s.has(k)) n++;
      return n / a.length;
    }
  }

  root.FlyBrain = FlyBrain;
  if (typeof module !== "undefined") module.exports = { FlyBrain };
})(typeof window !== "undefined" ? window : globalThis);
