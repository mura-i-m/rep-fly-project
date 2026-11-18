"""
build_data.py — ハエのワインソムリエ用のデータを作る

コネクトームと受容体データは、共通部品 fly-core（../fly-core/pipeline/mcns.py）から読む。
糸球体 → PN → KC の選び方も fly-core と同じ（mcns.olfactory_front）。

やること
  1. キノコ体の出力側（MBON・ドーパミン細胞、タイプごとにまとめる）と側角の配線を取り出す
  2. ワインの香り分子ごとに「どの糸球体がどれだけ反応するか」を作る
  3. ワイン辞書・生まれつきの好みと合わせて web/data/app_data.js に書き出す

使い方（fly-sommelier フォルダで）
  pip install -r ../fly-core/requirements.txt
  python pipeline/build_data.py

初回は約500MBのダウンロードがあります（fly-core/raw/ に保存され、ほかのアプリと共用）。
3D 表示のデータ（脳・ハエの体）は fly-core/data/ にあり、作り直すときは fly-core 側で行う。
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent / "fly-core" / "pipeline"))
import mcns  # noqa: E402

OUT = ROOT / "web" / "data" / "app_data.js"  # file:// でも開けるよう JS として書き出す
DICT = ROOT / "data" / "wine_dictionary.json"
INNATE = ROOT / "data" / "innate_valence.json"
MIN_SYN = mcns.MIN_SYN


def build_circuit(ann, t, w, kcs, ki, pns, pi):
    """キノコ体の出力側（MBON・ドーパミン細胞）と側角の配線を取り出す"""
    nt = mcns.neurotransmitters()
    mb = ann[ann["class"] == "MBON"]
    dan = ann[(ann["class"] == "DAN") & ann["type"].str.match(r"^(PAM|PPL1)")]
    mtypes = sorted(mb["type"].unique())
    dtypes = sorted(dan["type"].unique())
    mi = {m: i for i, m in enumerate(mtypes)}
    di = {d: i for i, d in enumerate(dtypes)}

    # KC → MBON（タイプごとに合計したシナプス数）。学習の初期値になる
    km = w[w.body_pre.isin(ki) & w.body_post.isin(mb.bodyId)].copy()
    km["m"] = km.body_post.map(t).map(mi)
    km = km.groupby(["body_pre", "m"], as_index=False).weight.sum()

    # ドーパミン細胞 → MBON（どの区画にどのドーパミンが入るか）
    dm = w[w.body_pre.isin(dan.bodyId) & w.body_post.isin(mb.bodyId)].copy()
    dm["d"] = dm.body_pre.map(t).map(di)
    dm["m"] = dm.body_post.map(t).map(mi)
    D = np.zeros((len(dtypes), len(mtypes)))
    np.add.at(D, (dm.d.values, dm.m.values), dm.weight.values)
    pam = np.array([d.startswith("PAM") for d in dtypes])
    share_pam = D[pam].sum(0) / np.maximum(D.sum(0), 1)
    # ごほうび系(PAM)が主に入る MBON は「避ける」向き、罰系(PPL1)が主なら「近づく」向き
    sign = np.where(share_pam > 0.5, -1, 1)
    Dn = D / np.maximum(D.sum(0, keepdims=True), 1)

    # MBON → ドーパミン細胞（フィードバック。符号はアプリ側で神経伝達物質から決める）
    md = w[w.body_pre.isin(mb.bodyId) & w.body_post.isin(dan.bodyId)].copy()
    md["m"] = md.body_pre.map(t).map(mi)
    md["d"] = md.body_post.map(t).map(di)
    F = np.zeros((len(mtypes), len(dtypes)))
    np.add.at(F, (md.m.values, md.d.values), md.weight.values)
    mnt = [nt.get(mb[mb["type"] == m].bodyId.iloc[0], "unknown") for m in mtypes]

    # PN → 側角（側角ニューロンはタイプごとにまとめる）
    lh = ann[ann["type"].fillna("").str.startswith("LH")]
    ltypes = sorted(lh["type"].unique())
    li = {x: i for i, x in enumerate(ltypes)}
    pl = w[w.body_pre.isin(pi) & w.body_post.isin(lh.bodyId) & (w.weight >= MIN_SYN)].copy()
    pl["l"] = pl.body_post.map(t).map(li)
    pl = pl.groupby(["body_pre", "l"], as_index=False).weight.sum()

    print(f"  MBON {len(mtypes)} タイプ（近づく {int((sign > 0).sum())} / 避ける {int((sign < 0).sum())}）、"
          f"ドーパミン細胞 {len(dtypes)} タイプ、側角 {len(ltypes)} タイプ")
    return {
        "mbon_types": mtypes,
        "mbon_sign": sign.tolist(),
        "mbon_nt": mnt,
        "mbon_body": {m: [int(b) for b in mb[mb["type"] == m].bodyId] for m in mtypes},
        "dan_types": dtypes,
        "dan_body": {d: [int(b) for b in dan[dan["type"] == d].bodyId] for d in dtypes},
        "dan_mbon": np.round(Dn, 4).tolist(),
        "mbon_dan": F.astype(int).tolist(),
        "kc_mbon": [[ki[k], int(m), int(x)] for k, m, x in km.itertuples(index=False)],
        "lh_types": ltypes,
        "pn_lh": [[pi[p], int(l), int(x)] for p, l, x in pl.itertuples(index=False)],
        "apl_body": [int(b) for b in ann.loc[ann["type"] == "APL", "bodyId"]],
    }


def main():
    wine = json.loads(DICT.read_text(encoding="utf-8"))

    # ---------- コネクトーム（fly-core）：糸球体 → PN → KC はどのアプリとも共通
    ann = mcns.annotations()
    t = ann.set_index("bodyId")["type"]
    front = mcns.olfactory_front()
    gloms, gi, gp = front["gloms"], front["gi"], front["glom_pn"]
    pns, pi, kcs, ki = front["pns"], front["pi"], front["kcs"], front["ki"]
    pn_kc = front["pn_kc"].copy()
    pn_kc["w"] = pn_kc.weight / pn_kc.groupby("body_post").weight.transform("sum")   # KC ごとに合計1

    circuit = build_circuit(ann, t, mcns.weights(), kcs, ki, pns, pi)

    # ---------- 分子 → 糸球体の応答（DoOR）
    needed = {n for n in wine["base"] if not n.startswith("_")}
    for v in wine["varieties"].values():
        needed |= set(v["aroma"])
    for v in wine["descriptors"].values():
        needed |= set(v)
    compounds = {}
    for n in sorted(needed):
        try:
            vec, measured = mcns.odor_vector(n, front)
        except KeyError as e:
            raise SystemExit(str(e))
        compounds[n] = {"g": vec, "measured": measured}

    kc_types = [t.get(k, "") for k in kcs]
    lobe = ["γ" if s.startswith("KCg") else "α′β′" if s.startswith("KCa'b'") else "αβ" for s in kc_types]

    data = {
        "source": {
            "connectome": mcns.SOURCES["connectome"],
            "odor": mcns.SOURCES["odor"].rsplit(",", 1)[0],
        },
        "glomeruli": gloms,
        "n_pn": len(pns),
        "n_kc": len(kcs),
        "kc_lobe": lobe,
        "glom_pn": [[gi[g], pi[p], round(float(x), 4)] for g, p, x in gp[["glom", "body_post", "w"]].itertuples(index=False)],
        "pn_kc": [[ki[k], pi[p], round(float(x), 4)] for p, k, x in pn_kc[["body_pre", "body_post", "w"]].itertuples(index=False)],
        "compounds": compounds,
        "wine": wine,
        "innate": json.loads(INNATE.read_text(encoding="utf-8")),
        "pn_body": [int(p) for p in pns],
        "kc_body": [int(k) for k in kcs],
        **circuit,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.APP_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")

    per_kc = pn_kc.groupby("body_post").size().mean()
    print(f"\n書き出しました: {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.1f} MB)")
    print(f"  糸球体 {len(gloms)} → PN {len(pns)} → KC {len(kcs)}（KC 1個あたりPN {per_kc:.1f} 本）")
    print(f"  香り分子 {len(compounds)} 種類")
    thin = [n for n, c in compounds.items() if c["measured"] < 10]
    if thin:
        print(f"  ※ 受容体データが少ない分子: {', '.join(thin)}")


if __name__ == "__main__":
    main()
