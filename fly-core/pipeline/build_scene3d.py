"""
build_scene3d.py — 3D表示用のデータ（ニューロンの形・脳の領域の形）を作る（fly-core 共通データ）

  python pipeline/build_scene3d.py

雄CNSの公開データから
  ・経路上のニューロン（PN / KC / MBON / ドーパミン細胞 / APL）の骨格
  ・脳の輪郭と、触角葉・萼・側角・キノコ体の葉のメッシュ
を取ってきて、ブラウザで軽く描けるよう間引いて web/data/scene3d.js に書き出す。
初回は約4,500本の骨格をダウンロードする（raw/skeletons/ に保存、数分）。
"""
import base64
import json
import struct
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mcns  # noqa: E402

ROOT = mcns.CORE
RAW = mcns.RAW
OUT = ROOT / "data" / "scene3d.js"
SKEL, ROI_MESH, SHELL_MESH = mcns.SKELETONS, mcns.ROI_MESH, mcns.SHELL_MESH

# 描く脳の領域（左右）と色
REGIONS = {
    "触角葉": (["AL(L)", "AL(R)"], "#8e44ad"),
    "萼":     (["CA(L)", "CA(R)"], "#27ae60"),
    "側角":   (["LH(L)", "LH(R)"], "#e67e22"),
    "キノコ体の葉": (["PED(L)", "PED(R)", "aL(L)", "aL(R)", "a'L(L)", "a'L(R)",
                    "bL(L)", "bL(R)", "b'L(L)", "b'L(R)", "gL(L)", "gL(R)"], "#c0392b"),
}
# 骨格を間引く間隔（分岐点・端点は必ず残す）
STRIDE = {"kc": 45, "pn": 15, "mbon": 20, "dan": 25, "apl": 25}
# これより短い枝先（点の数）は切り落とす
PRUNE = {"kc": 90, "pn": 30, "mbon": 60, "dan": 80, "apl": 80}
UNIT = 100.0  # 座標の単位：100nm（int16 に収める）


fetch = mcns.fetch_bytes


def read_skeleton(data):
    nv, ne = struct.unpack("<II", data[:8])
    v = np.frombuffer(data[8:8 + nv * 12], dtype="<f4").reshape(-1, 3)
    e = np.frombuffer(data[8 + nv * 12:8 + nv * 12 + ne * 8], dtype="<u4").reshape(-1, 2)
    return v, e


def prune(v, e, min_len):
    """短い枝先を切り落とす（形の大筋だけ残す）"""
    n = len(v)
    adj = [[] for _ in range(n)]
    for a, b in e:
        adj[a].append(b); adj[b].append(a)
    alive = np.ones(n, bool)
    for leaf in [i for i in range(n) if len(adj[i]) == 1]:
        path, prev, cur = [leaf], -1, leaf
        while True:
            nxt = [x for x in adj[cur] if x != prev]
            if len(nxt) != 1:
                break
            prev, cur = cur, nxt[0]
            if len(adj[cur]) != 2:
                break
            path.append(cur)
        if len(adj[cur]) > 2 and len(path) < min_len:
            alive[path] = False
    keep = alive[e[:, 0]] & alive[e[:, 1]]
    return e[keep]


def simplify(v, e, stride):
    """分岐点と端点、それに stride ごとの点だけ残した線分のリストにする"""
    n = len(v)
    if n < 2:
        return np.zeros((0, 2, 3))
    deg = np.bincount(e.ravel(), minlength=n)
    adj = [[] for _ in range(n)]
    for a, b in e:
        adj[a].append(b); adj[b].append(a)
    keep = deg != 2
    seen = np.zeros(n, bool)
    segs = []
    # 木を幅優先でたどりながら、残す点どうしを結ぶ
    if len(e) == 0:
        return np.zeros((0, 2, 3))
    keep &= deg > 0
    # 切り落とされずに残った部分の端（または分岐点）からたどり始める
    cand = np.flatnonzero((deg > 0) & (deg != 2))
    start = int(cand[0]) if len(cand) else int(e[0, 0])
    stack = [(start, start, 0)]
    seen[start] = True
    while stack:
        node, anchor, steps = stack.pop()
        for nb in adj[node]:
            if seen[nb]:
                continue
            seen[nb] = True
            s = steps + 1
            if keep[nb] or s >= stride:
                segs.append((anchor, nb))
                stack.append((nb, nb, 0))
            else:
                stack.append((nb, anchor, s))
    return v[np.array(segs)] if segs else np.zeros((0, 2, 3))


def read_ngmesh(data):
    nv = struct.unpack("<I", data[:4])[0]
    v = np.frombuffer(data[4:4 + nv * 12], dtype="<f4").reshape(-1, 3)
    f = np.frombuffer(data[4 + nv * 12:], dtype="<u4").reshape(-1, 3)
    return v, f


def decimate(v, f, cell):
    """格子でまとめてポリゴン数を減らす（vertex clustering）"""
    key = np.floor(v / cell).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    nv = np.zeros((len(uniq), 3))
    np.add.at(nv, inv, v)
    nv /= np.bincount(inv)[:, None]
    nf = inv[f]
    nf = nf[(nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])]
    return nv, nf


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def main():
    # 嗅覚の経路のニューロン（どのアプリでも同じ選び方。アプリ側で bodyId から自分の番号に対応させる）
    front = mcns.olfactory_front()
    neurons = []  # (kind, bodyId)
    neurons += [("pn", b) for b in front["pns"]]
    neurons += [("kc", b) for b in front["kcs"]]
    neurons += [("mbon", b) for b in sorted(mcns.ids("mbon"))]
    neurons += [("dan", b) for b in sorted(mcns.ids("dan"))]
    neurons += [("apl", b) for b in sorted(mcns.ids("apl"))]

    print(f"骨格を取得中: {len(neurons)} 本")
    def get(item):
        kind, body = item
        try:
            v, e = read_skeleton(fetch(SKEL + str(body), RAW / "skeletons" / str(body)))
            return kind, body, simplify(v, prune(v, e, PRUNE[kind]), STRIDE[kind])
        except Exception as ex:  # 取れなかったニューロンは描かない
            print(f"  skip {body}: {ex}")
            return kind, body, np.zeros((0, 2, 3))
    with ThreadPoolExecutor(16) as ex:
        results = list(ex.map(get, neurons))

    allpts = np.concatenate([s.reshape(-1, 3) for _, _, s in results if len(s)])
    center = (allpts.min(0) + allpts.max(0)) / 2

    segs, index = [], []
    pos = 0
    for kind, body, s in results:
        q = np.round((s.reshape(-1, 3) - center) / UNIT).astype(np.int16)
        segs.append(q)
        index.append([kind, int(body), pos, len(s)])   # 種類, bodyId, 線分の開始位置, 本数
        pos += len(s)
    segs = np.concatenate(segs)

    print("脳の領域のメッシュを取得中…")
    meshes = {}
    for name, (rois, color) in REGIONS.items():
        vs, fs, off = [], [], 0
        for r in rois:
            v, f = read_ngmesh(fetch(ROI_MESH + r + ".ngmesh", RAW / "meshes" / (r + ".ngmesh")))
            v, f = decimate(v, f, 2500.0)
            vs.append(v); fs.append(f + off); off += len(v)
        v, f = np.concatenate(vs), np.concatenate(fs)
        meshes[name] = {"color": color, "pos": b64(np.round((v - center) / UNIT).astype(np.int16)),
                        "idx": b64(f.astype(np.uint32))}
    v, f = read_ngmesh(fetch(SHELL_MESH, RAW / "meshes" / "brain-shell.ngmesh"))
    v, f = decimate(v, f, 7000.0)
    meshes["脳の輪郭"] = {"color": "#b9a7ad", "pos": b64(np.round((v - center) / UNIT).astype(np.int16)),
                       "idx": b64(f.astype(np.uint32))}

    scene = {"source": mcns.SOURCES["connectome"], "unit_nm": UNIT, "segs": b64(segs), "neurons": index, "meshes": meshes}
    OUT.write_text("window.SCENE3D = " + json.dumps(scene, separators=(",", ":")) + ";\n")
    print(f"書き出しました: {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1e6:.1f} MB, 線分 {len(segs)//2:,} 本)")


if __name__ == "__main__":
    main()
