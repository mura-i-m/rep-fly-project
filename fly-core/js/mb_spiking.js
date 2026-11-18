/*
 * mb_spiking.js — スパイクで動くキノコ体（fly-core 共通部品）
 *
 * 回路（すべて male CNS の配線をニューロン1個ずつ使う）
 *   匂い → 糸球体47 → 投射ニューロン PN 254（ポアソン発火）
 *        → ケニオン細胞 KC 3,763（LIF）⇄ APL 2（KC 全体にブレーキ）
 *        → MBON 97（LIF）
 *   ドーパミン細胞 332 は「先生」役。発火すると、その区画で
 *   直前に発火した KC → MBON の結合を弱める（ハエで知られている可塑性）
 *
 * ニューロンのモデルは Shiu et al. (2024, Nature) の全脳 LIF モデルと同じ式と定数
 *   dv/dt = (v0 - v + g) / τm,  dg/dt = -g / τs,  1シナプス = 0.275 mV
 * ただし、全脳ではなくキノコ体だけを動かす（hae.satoru.net と同じ割り切り）
 *
 * Node（VSCode 拡張機能）でもブラウザでも動く。
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FlyMB = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ---------- Shiu et al. 2024 の定数
  const SHIU = {
    v0: -52, vReset: -52, vTh: -45, // mV
    tauM: 20, tauS: 5, tRef: 2.2,   // ms
    wSyn: 0.275,                    // mV / シナプス
  };

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // [pre, post, w] のリスト → 前ニューロンごとの出力表（CSR）
  function csr(list, nPre) {
    const ptr = new Int32Array(nPre + 1);
    for (const [a] of list) ptr[a + 1]++;
    for (let i = 0; i < nPre; i++) ptr[i + 1] += ptr[i];
    const post = new Int32Array(list.length);
    const w = new Float32Array(list.length);
    const fill = ptr.slice(0, nPre);
    for (const [a, b, x] of list) { const j = fill[a]++; post[j] = b; w[j] = x; }
    return { ptr, post, w };
  }

  class LIF {
    constructor(n, p) {
      this.n = n;
      this.v = new Float32Array(n).fill(p.v0);
      this.g = new Float32Array(n);
      this.ref = new Float32Array(n);
      this.spk = new Uint8Array(n);
      this.count = new Uint16Array(n);
      this.p = p;
    }
    reset() {
      this.v.fill(this.p.v0); this.g.fill(0); this.ref.fill(0); this.spk.fill(0); this.count.fill(0);
    }
    step(dt) {
      const { v0, vReset, vTh, tauM, tauS, tRef } = this.p;
      const decay = Math.exp(-dt / tauS);
      const k = dt / tauM;
      const v = this.v, g = this.g, ref = this.ref, spk = this.spk, cnt = this.count;
      let fired = 0;
      for (let i = 0; i < this.n; i++) {
        spk[i] = 0;
        if (ref[i] > 0) { ref[i] -= dt; g[i] *= decay; continue; }
        v[i] += (v0 - v[i] + g[i]) * k;
        g[i] *= decay;
        if (v[i] > vTh) { v[i] = vReset; ref[i] = tRef; spk[i] = 1; cnt[i]++; fired++; }
      }
      return fired;
    }
  }

  class MushroomBody {
    /**
     * @param {object} data  data/mb_circuit.json の中身
     * @param {object} opt   調整用のつまみ（README 参照）
     */
    constructor(data, opt = {}) {
      this.data = data;
      this.opt = Object.assign({
        dt: 0.5,            // ms
        pnBase: 2,          // PN の自発発火 Hz
        pnMax: 200,         // PN の最大発火 Hz
        pnGain: 1.0,        // 糸球体の反応 → PN 発火の倍率
        kcGain: 1.0,        // PN→KC シナプスの倍率
        aplGain: 1.0,       // KC→APL の倍率
        aplKCGain: 1.0,     // APL→KC（ブレーキの強さ）の倍率
        mbonDrive: 300,     // KC 全部が1回ずつ発火したときに MBON に入る合計（mV）。MBON ごとに揃える
        lr: 0.05,           // ドーパミン1回あたりの結合の減り方
        lrUp: 0.02,         // 間違えた区画の結合の戻り方
        danUniform: false,  // true: 区画内の MBON に一様に効かせる
        useLongTerm: false, // 読み出しに長期記憶を使う
        seed: 1,
      }, opt);
      this.rand = mulberry32(this.opt.seed);
      const nG = data.glomeruli.length;
      this.nG = nG;
      this.nPN = data.pn.body.length;
      this.nKC = data.kc.body.length;
      this.nM = data.mbon.body.length;
      this.nD = data.dan.body.length;
      this.nA = data.apl.body.length;

      // 糸球体 → PN（入力の重み。PN ごとに合計1）
      this.glomPN = csr(data.glom_pn, nG);

      const p = SHIU;
      this.kc = new LIF(this.nKC, p);
      this.apl = new LIF(this.nA, p);
      this.mbon = new LIF(this.nM, p);

      const ws = p.wSyn;
      this.pnKC = csr(data.pn_kc.map(([a, b, x]) => [a, b, x * ws]), this.nPN);
      this.kcAPL = csr(data.kc_apl.map(([a, b, x]) => [a, b, x * ws]), this.nKC);
      this.aplKC = csr(data.apl_kc.map(([a, b, x]) => [a, b, -x * ws]), this.nA); // GABA

      // KC → MBON：シナプス数 × 可塑的な強さ（はじめ 1）
      this.kcM = csr(data.kc_mbon, this.nKC);
      this.plastic = new Float32Array(this.kcM.w.length).fill(1);
      // ゆっくり定着する記憶（長期記憶）。consolidate() のたびに plastic に少しずつ近づく。
      // 読み出しにはこちらを使う（opt.useLongTerm）。一回ごとの学習のぶれをならす役目
      this.longTerm = new Float32Array(this.kcM.w.length).fill(1);
      // MBON ごとに入力の総量を揃える（ホメオスタシス）。揃えないと
      // KC 入力が数十～数千シナプスと大きく違い、一部の MBON しか動かない
      const tot = new Float32Array(this.nM);
      for (let j = 0; j < this.kcM.w.length; j++) tot[this.kcM.post[j]] += this.kcM.w[j];
      this.mbonScale = Float32Array.from(tot, (t) => (t > 0 ? 1 / t : 0));

      // ドーパミン細胞 → MBON（どの区画にどの先生が入るか）
      this.danM = csr(data.dan_mbon, this.nD);

      this.pnRate = new Float32Array(this.nPN);
      this.pnSpk = new Uint8Array(this.nPN);
      this.pnCount = new Uint16Array(this.nPN);
      this.mbonIn = new Float32Array(this.nM);    // MBON に届いた入力の合計（学習後）
      this.mbonNaive = new Float32Array(this.nM); // 学習前の結合だったら届いたはずの入力
    }

    /** 糸球体の反応（長さ47、0〜1程度）から PN の発火率を決める */
    setOdor(glom) {
      const { pnBase, pnMax, pnGain } = this.opt;
      const drive = new Float32Array(this.nPN);
      const { ptr, post, w } = this.glomPN;
      for (let g = 0; g < this.nG; g++) {
        const x = glom[g];
        if (!x) continue;
        for (let j = ptr[g]; j < ptr[g + 1]; j++) drive[post[j]] += x * w[j];
      }
      for (let i = 0; i < this.nPN; i++) {
        this.pnRate[i] = pnBase + (pnMax - pnBase) * Math.tanh(pnGain * drive[i]);
      }
    }

    resetActivity() {
      this.kc.reset(); this.apl.reset(); this.mbon.reset();
      this.pnCount.fill(0);
      this.mbonIn.fill(0); this.mbonNaive.fill(0);
    }

    /**
     * 匂いを duration ms 嗅がせる。
     * onStep(t, mb) を渡すと毎ステップ呼ばれる（発火の可視化・タッピング用）
     * 戻り値: 各層の発火数
     */
    run(duration, onStep) {
      const { dt, kcGain, aplGain, aplKCGain } = this.opt;
      const steps = Math.round(duration / dt);
      const kc = this.kc, apl = this.apl, mbon = this.mbon;
      const pnKC = this.pnKC, kcAPL = this.kcAPL, aplKC = this.aplKC, kcM = this.kcM;
      const plastic = this.opt.useLongTerm ? this.longTerm : this.plastic, scale = this.mbonScale;
      const mbonIn = this.mbonIn, mbonNaive = this.mbonNaive;
      const mg = this.opt.mbonDrive;
      const pdt = dt / 1000;
      for (let s = 0; s < steps; s++) {
        // PN（ポアソン）
        for (let i = 0; i < this.nPN; i++) {
          if (this.rand() < this.pnRate[i] * pdt) {
            this.pnSpk[i] = 1; this.pnCount[i]++;
            for (let j = pnKC.ptr[i]; j < pnKC.ptr[i + 1]; j++) kc.g[pnKC.post[j]] += pnKC.w[j] * kcGain;
          } else this.pnSpk[i] = 0;
        }
        kc.step(dt);
        // KC の発火 → APL と MBON
        for (let k = 0; k < this.nKC; k++) {
          if (!kc.spk[k]) continue;
          for (let j = kcAPL.ptr[k]; j < kcAPL.ptr[k + 1]; j++) apl.g[kcAPL.post[j]] += kcAPL.w[j] * aplGain;
          for (let j = kcM.ptr[k]; j < kcM.ptr[k + 1]; j++) {
            const m = kcM.post[j];
            const x = kcM.w[j] * scale[m] * mg;
            mbon.g[m] += x * plastic[j];
            mbonIn[m] += x * plastic[j];
            mbonNaive[m] += x;
          }
        }
        apl.step(dt);
        for (let a = 0; a < this.nA; a++) {
          if (!apl.spk[a]) continue;
          for (let j = aplKC.ptr[a]; j < aplKC.ptr[a + 1]; j++) kc.g[aplKC.post[j]] += aplKC.w[j] * aplKCGain;
        }
        mbon.step(dt);
        if (onStep) onStep(s * dt, this);
      }
      return {
        kcActive: kc.count.reduce((n, c) => n + (c > 0), 0),
        kcSpikes: kc.count.reduce((n, c) => n + c, 0),
        aplSpikes: apl.count.reduce((n, c) => n + c, 0),
        mbonSpikes: Array.from(mbon.count),
        mbonIn: Array.from(this.mbonIn),
        mbonNaive: Array.from(this.mbonNaive),
      };
    }

    /**
     * ドーパミン細胞 dans（番号の配列）を発火させる。
     * その細胞が入る MBON への「いま発火した KC」の結合を、
     * sign<0 なら弱める（学習）、sign>0 なら戻す。
     */
    dopamine(dans, sign = -1, amount = 1, only = null) {
      const target = new Float32Array(this.nM);
      for (const d of dans) {
        for (let j = this.danM.ptr[d]; j < this.danM.ptr[d + 1]; j++) target[this.danM.post[j]] += this.danM.w[j];
      }
      // only: 効かせる MBON を限定する（区画の外へのしみ出しを無視する近似）
      if (only) { const keep = new Set(only); for (let m = 0; m < this.nM; m++) if (!keep.has(m)) target[m] = 0; }
      let mx = 0;
      for (const x of target) mx = Math.max(mx, x);
      if (!mx) return;
      const lr = (sign < 0 ? this.opt.lr : this.opt.lrUp) * amount;
      const kcM = this.kcM, cnt = this.kc.count, plastic = this.plastic;
      for (let k = 0; k < this.nKC; k++) {
        const a = cnt[k];
        if (!a) continue;
        const e = Math.min(a, 3) / 3; // 適格性：最近よく発火した KC ほど変わる
        for (let j = kcM.ptr[k]; j < kcM.ptr[k + 1]; j++) {
          const m = kcM.post[j];
          if (!target[m]) continue;
          const f = lr * e * (this.opt.danUniform ? 1 : target[m] / mx);
          plastic[j] = sign < 0 ? plastic[j] * (1 - f) : plastic[j] + f * (1 - plastic[j]);
        }
      }
    }

    /** 短期の変化を長期記憶に少しだけ移す */
    consolidate(rate = 0.002) {
      const f = this.plastic, l = this.longTerm;
      for (let j = 0; j < l.length; j++) l[j] += (f[j] - l[j]) * rate;
    }

    /** 学習した結合を保存・復元 */
    exportPlastic() {
      const r = (a) => Array.from(a, (x) => Math.round(x * 1e4) / 1e4);
      return { fast: r(this.plastic), long: r(this.longTerm) };
    }
    importPlastic(p) {
      if (Array.isArray(p)) { this.plastic.set(p); this.longTerm.set(p); return; }
      this.plastic.set(p.fast); this.longTerm.set(p.long);
    }
  }

  return { MushroomBody, SHIU, mulberry32 };
});
