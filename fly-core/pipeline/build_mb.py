"""
build_mb.py — キノコ体の配線をニューロン単位で取り出す（fly-core 共通データ）

ワインソムリエ（fly-sommelier/pipeline/build_data.py）との違い
  - MBON とドーパミン細胞をタイプでまとめず、1個ずつ残す（スパイクモデル用）
  - APL（KC 全体にブレーキをかける巨大な抑制ニューロン）の配線も入れる
  - 香り分子は、受容体の測定が多いものを DoOR から丸ごと「香りの図書館」として書き出す
    （どの分子を使うかは各アプリが選ぶ）
糸球体 → PN → KC の選び方は mcns.olfactory_front() で、どのアプリとも共通。

使い方（fly-core フォルダで）
  pip install -r requirements.txt
  python pipeline/build_mb.py

初回は約570MBのダウンロードがあります（fly-core/raw/ に保存、ほかのアプリと共用）。メモリは 6GB 程度あると安心。
出力: data/mb_circuit.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcns  # noqa: E402

ROOT = mcns.CORE
OUT = ROOT / "data" / "mb_circuit.json"

MIN_SYN = mcns.MIN_SYN
MIN_SYN_KC_MBON = 1  # KC→MBON は細かい結合も学習の材料なので残す
MIN_MEASURED = 15    # 香りの図書館に入れる分子：この数以上の受容体で測られているもの


def pairs(df, pre_idx, post_idx):
    """(pre, post, シナプス数) のリストにする"""
    return [[pre_idx[a], post_idx[b], int(x)] for a, b, x in df[["body_pre", "body_post", "weight"]].itertuples(index=False)]


def main():
    ann = mcns.annotations()
    nt = mcns.neurotransmitters()
    t = ann.set_index("bodyId")["type"]
    side = ann.set_index("bodyId")["somaSide"].fillna("?")

    front = mcns.olfactory_front()
    gloms, gi, gp = front["gloms"], front["gi"], front["glom_pn"]
    pns, pi, kcs, ki = front["pns"], front["pi"], front["kcs"], front["ki"]
    pn_kc = front["pn_kc"]

    mbon_ids, dan_ids, apl_ids = mcns.ids("mbon"), mcns.ids("dan"), mcns.ids("apl")
    w = mcns.weights()
    keep = set(kcs) | set(mbon_ids) | set(dan_ids) | set(apl_ids)
    w = w[w.body_pre.isin(keep) & w.body_post.isin(keep)]

    def sub(pre, post, min_syn=MIN_SYN):
        return w[w.body_pre.isin(pre) & w.body_post.isin(post) & (w.weight >= min_syn)]

    # ---------- MBON / ドーパミン細胞 / APL（1個ずつ）
    mbons = sorted(mbon_ids)
    mi = {m: i for i, m in enumerate(mbons)}
    dans = sorted(dan_ids)
    di = {d: i for i, d in enumerate(dans)}
    apls = sorted(apl_ids)
    ai = {a: i for i, a in enumerate(apls)}

    kc_mbon = sub(kcs, mbons, MIN_SYN_KC_MBON)
    dan_mbon = sub(dans, mbons, 1)
    dan_kc = sub(dans, kcs, 1).groupby(["body_pre", "body_post"], as_index=False).weight.sum()
    mbon_dan = sub(mbons, dans, 1)
    mbon_mbon = sub(mbons, mbons, MIN_SYN)
    kc_apl = sub(kcs, apls, 1)
    apl_kc = sub(apls, kcs, 1)

    # ---------- 香りの図書館（DoOR）
    resp, _, odor = mcns.door()
    key2name = dict(zip(odor.InChIKey, odor.Name))
    library = {}
    for key, row in resp.iterrows():
        if key == "SFR" or key not in key2name:
            continue
        if int(row.notna().sum()) < MIN_MEASURED:
            continue
        vec, measured = mcns.odor_vector(key, front, sort=False)
        if vec:
            library[str(key2name[key])] = {"g": vec, "measured": measured}

    data = {
        "source": {"connectome": mcns.SOURCES["connectome"], "odor": mcns.SOURCES["odor"].rsplit(",", 1)[0]},
        "glomeruli": gloms,
        "glom_pn": [[gi[g], pi[p], round(float(x), 4)] for g, p, x in gp[["glom", "body_post", "w"]].itertuples(index=False)],
        "pn": {"body": [int(p) for p in pns], "type": [str(t.get(p, "")) for p in pns], "side": [side.get(p) for p in pns]},
        "kc": {"body": [int(k) for k in kcs], "type": [str(t.get(k, "")) for k in kcs], "side": [side.get(k) for k in kcs]},
        "mbon": {"body": [int(m) for m in mbons], "type": [str(t.get(m, "")) for m in mbons],
                 "side": [side.get(m) for m in mbons], "nt": [str(nt.get(m, "unknown")) for m in mbons]},
        "dan": {"body": [int(d) for d in dans], "type": [str(t.get(d, "")) for d in dans], "side": [side.get(d) for d in dans]},
        "apl": {"body": [int(a) for a in apls], "side": [side.get(a) for a in apls]},
        # [pre, post, シナプス数]
        "pn_kc": pairs(pn_kc, pi, ki),
        "kc_mbon": pairs(kc_mbon, ki, mi),
        "dan_mbon": pairs(dan_mbon, di, mi),
        "dan_kc": pairs(dan_kc, di, ki),
        "mbon_dan": pairs(mbon_dan, mi, di),
        "mbon_mbon": pairs(mbon_mbon, mi, mi),
        "kc_apl": pairs(kc_apl, ki, ai),
        "apl_kc": pairs(apl_kc, ai, ki),
        "odor_library": library,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print(f"\n書き出しました: {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.1f} MB)")
    print(f"  糸球体 {len(gloms)} → PN {len(pns)} → KC {len(kcs)} → MBON {len(mbons)}")
    print(f"  ドーパミン細胞 {len(dans)}、APL {len(apls)}")
    for k in ["pn_kc", "kc_mbon", "dan_mbon", "dan_kc", "mbon_dan", "mbon_mbon", "kc_apl", "apl_kc"]:
        print(f"  {k}: {len(data[k])} 本")
    print(f"  香りの図書館: {len(library)} 分子")


if __name__ == "__main__":
    main()
