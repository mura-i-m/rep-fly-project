"""
mcns.py — 雄CNSコネクトームと DoOR を読み込む共通部品（fly-core）

rep-fly-project のどのアプリも、コネクトームはここから読む。
ダウンロードしたデータは fly-core/raw/ にまとめて保存し、アプリ間で使い回す。

  import sys; sys.path.insert(0, "<rep-fly-project>/fly-core/pipeline")
  import mcns
  ann = mcns.annotations()
  front = mcns.olfactory_front()     # 糸球体 → PN → KC（どのアプリでも同じ選び方）

出典：male CNS v1.0 (Berg et al., Cell 2026, CC BY 4.0) / DoOR 2.0 (Münch & Galizia, Sci Rep 2016, CC BY-SA 4.0)
"""
import io
import urllib.parse
import urllib.request
import zipfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

CORE = Path(__file__).resolve().parent.parent
RAW = CORE / "raw"

GCS = "https://storage.googleapis.com/flyem-male-cns/"
FLAT = GCS + "v1.0/connectome-data/flat-connectome/"
ANN = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
WEIGHTS = "connectome-weights-male-cns-v1.0-minconf-0.5-traced-only.feather"
NTS = "body-neurotransmitters-male-cns-v1.0.feather"
SKELETONS = GCS + "v1.0/segmentation/skeletons-malecns/skeletons-precomputed/"
ROI_MESH = GCS + "rois/fullbrain-roi-v5/mesh/"
SHELL_MESH = GCS + "rois/brain-shell-v2.2/mesh/brain-shell.ngmesh"
DOOR_ZIP = "https://github.com/ropensci/DoOR.data/archive/refs/heads/master.zip"

MIN_SYN = 3  # PN→KC・ORN→PN などで、これ未満のシナプス数の結合は使わない

SOURCES = {
    "connectome": "male CNS v1.0 (Berg et al., Cell 2026), CC BY 4.0",
    "odor": "DoOR 2.0 (Münch & Galizia, Sci Rep 2016), CC BY-SA 4.0",
}


# ---------------------------------------------------------------- ダウンロード
def download(url, dest):
    """url を dest に保存（あれば使い回す）"""
    dest = Path(dest)
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"ダウンロード中: {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(urllib.parse.quote(url, safe=":/"), tmp)
    tmp.rename(dest)
    return dest


def fetch_bytes(url, dest):
    """小さなファイル（骨格・メッシュ）を取ってきて中身を返す。raw/ にキャッシュ"""
    dest = Path(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(urllib.request.urlopen(urllib.parse.quote(url, safe=":/"), timeout=60).read())
    return dest.read_bytes()


# ---------------------------------------------------------------- コネクトーム
@lru_cache(maxsize=1)
def annotations():
    return pd.read_feather(download(FLAT + ANN, RAW / ANN))


@lru_cache(maxsize=1)
def weights():
    """全結合 (body_pre, body_post, weight)。約2,500万行"""
    print("結合データを読み込み中…（少し時間がかかります）")
    return pd.read_feather(download(FLAT + WEIGHTS, RAW / WEIGHTS), columns=["body_pre", "body_post", "weight"])


@lru_cache(maxsize=1)
def neurotransmitters():
    """bodyId → 推定神経伝達物質（acetylcholine / gaba / glutamate …）"""
    return pd.read_feather(download(FLAT + NTS, RAW / NTS)).set_index("body")["consensus_nt"]


def types():
    return annotations().set_index("bodyId")["type"]


def ids(kind):
    """よく使うニューロンの集まりの bodyId"""
    a = annotations()
    ty = a["type"].fillna("")
    sel = {
        "orn": ty.str.startswith("ORN_"),
        "pn": a["class"] == "ALPN",
        "kc": a["class"] == "Kenyon_Cell",
        "mbon": a["class"] == "MBON",
        "dan": (a["class"] == "DAN") & ty.str.match(r"^(PAM|PPL1)"),   # キノコ体のドーパミン細胞
        "apl": ty == "APL",
        "lh": ty.str.startswith("LH"),                                 # 側角
    }[kind]
    return a.loc[sel, "bodyId"]


# ---------------------------------------------------------------- DoOR（嗅覚受容体の応答）
@lru_cache(maxsize=1)
def door():
    d = RAW / "door"
    need = ["door_response_matrix.csv", "door_mappings.csv", "odor.csv"]
    if not all((d / n).exists() for n in need):
        print("DoOR データをダウンロード中…")
        data = urllib.request.urlopen(DOOR_ZIP).read()
        d.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in need:
                (d / n).write_bytes(z.read(f"DoOR.data-master/data/{n}"))
    resp = pd.read_csv(d / "door_response_matrix.csv", sep=";", index_col=0)
    maps = pd.read_csv(d / "door_mappings.csv", sep=";")
    odor = pd.read_csv(d / "odor.csv", sep=";")
    return resp, maps, odor


# ---------------------------------------------------------------- 嗅覚の入口：糸球体 → PN → KC
@lru_cache(maxsize=1)
def olfactory_front():
    """
    どのアプリでも同じ選び方で、匂いの入口からケニオン細胞までを取り出す。
      ・糸球体：DoOR に受容体データがあり、雄CNS に ORN_<糸球体> があるもの
      ・PN：その糸球体の ORN から入力を受け（MIN_SYN 以上）、KC に出力しているもの
      ・KC：その PN から入力を受けるもの
    """
    t = types()
    w = weights()
    orn, pn, kc = set(ids("orn")), set(ids("pn")), set(ids("kc"))
    resp, maps, odor = door()

    orn_pn = w[w.body_pre.isin(orn) & w.body_post.isin(pn)].copy()
    mcns_gloms = set(orn_pn.body_pre.map(t).str[4:])
    rec2glom = {r: g for r, g in maps[["receptor", "glomerulus"]].dropna().itertuples(index=False)
                if r in resp.columns and g in mcns_gloms}
    gloms = sorted(set(rec2glom.values()))
    gi = {g: i for i, g in enumerate(gloms)}

    orn_pn["glom"] = orn_pn.body_pre.map(t).str[4:]
    orn_pn = orn_pn[orn_pn.glom.isin(gi)]
    gp = orn_pn.groupby(["glom", "body_post"], as_index=False).weight.sum()
    gp = gp[gp.weight >= MIN_SYN]

    pn_kc = w[w.body_pre.isin(pn) & w.body_post.isin(kc) & (w.weight >= MIN_SYN)].copy()
    pns = sorted(set(gp.body_post) & set(pn_kc.body_pre))
    pi = {p: i for i, p in enumerate(pns)}
    gp = gp[gp.body_post.isin(pi)].copy()
    gp["w"] = gp.weight / gp.groupby("body_post").weight.transform("sum")   # PN ごとに合計1

    pn_kc = pn_kc[pn_kc.body_pre.isin(pi)].copy()
    kcs = sorted(set(pn_kc.body_post))
    ki = {k: i for i, k in enumerate(kcs)}
    return {"gloms": gloms, "gi": gi, "rec2glom": rec2glom, "glom_pn": gp,
            "pns": pns, "pi": pi, "pn_kc": pn_kc, "kcs": kcs, "ki": ki}


def odor_vector(name_or_key, front=None, sort=True):
    """香り分子（DoOR の名前か InChIKey）→ 糸球体ごとの応答 [[糸球体番号, 強さ], …] と測定数"""
    front = front or olfactory_front()
    resp, _, odor = door()
    key = name_or_key if name_or_key in resp.index else dict(zip(odor.Name, odor.InChIKey)).get(name_or_key)
    if key not in resp.index:
        raise KeyError(f"DoOR に見つからない分子: {name_or_key}")
    row = resp.loc[key]
    vals = (row - resp.loc["SFR"]).clip(lower=0)   # 自発発火を引く
    acc = {}
    for r, g in front["rec2glom"].items():
        if pd.notna(row[r]):
            acc.setdefault(g, []).append(vals[r])
    vec = [[front["gi"][g], float(np.mean(xs))] for g, xs in acc.items()]
    vec = [[i, round(x, 4)] for i, x in vec if x > 0.01]   # 弱すぎる反応は捨ててから丸める
    return (sorted(vec) if sort else vec), int(row.notna().sum())
