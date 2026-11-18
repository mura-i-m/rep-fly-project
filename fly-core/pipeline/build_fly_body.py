"""
build_fly_body.py — ハエの体（NeuroMechFly）と動きを、ブラウザ用に書き出す（fly-core 共通データ）

  pip install "flygym @ git+https://github.com/NeLy-EPFL/flygym.git"
  python pipeline/build_fly_body.py

・体：NeuroMechFly v2（X線CTから作られたハエの3Dモデル、Apache-2.0）
・歩く：本物のハエの歩行で測った関節角度の記録を、そのまま再生（flygym 同梱のデータ）
・触角で嗅ぐ／前脚でトントン／口吻を伸ばして飲む／飛び立つ：関節を手で動かしたアニメーション
出力：data/fly3d.js（各体節の形と、動きごとの各体節の位置・向き）
"""
import base64
import json
from pathlib import Path

import mujoco as mj
import numpy as np
from flygym.anatomy import AxisOrder, JointPreset, Skeleton
from flygym.compose import KinematicPosePreset, NeuroMechFly
from flygym_demo.spotlight_data import MotionSnippet

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "fly3d.js"
FPS = 50
WALK_FPS = 100  # 歩行は速いので細かく取り出し、ブラウザでスロー再生する

LEGS = ["lf", "lm", "lh", "rf", "rm", "rh"]
COLOR = {"eye": "#9b1c1c", "wing": "#cfd8dc", "haltere": "#c9a46a", "arista": "#5a4632",
         "default": "#b07a3a", "abdomen": "#8a5a2b", "tarsus": "#6b4a2a"}


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def main():
    fly = NeuroMechFly()
    sk = Skeleton(axis_order=AxisOrder.YAW_PITCH_ROLL, joint_preset=JointPreset.ALL_BIOLOGICAL)
    fly.add_joints(sk, neutral_pose=KinematicPosePreset.NEUTRAL)
    m, d = fly.compile()
    neutral = KinematicPosePreset.NEUTRAL.get_pose_by_axis_order(AxisOrder.YAW_PITCH_ROLL).joint_angles_lookup_rad
    jid = {mj.mj_id2name(m, mj.mjtObj.mjOBJ_JOINT, i): i for i in range(m.njnt)}
    bodies = [mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, i) for i in range(1, m.nbody)]  # world を除く

    def pose(extra=None):
        a = dict(neutral)
        for k, v in (extra or {}).items():
            a[k] = a.get(k, 0.0) + v
        d.qpos[:] = 0
        for k, v in a.items():
            d.qpos[m.jnt_qposadr[jid[k]]] = v
        mj.mj_kinematics(m, d)
        return np.concatenate([d.xpos[1:], d.xquat[1:]], axis=1).astype(np.float32)  # (体節, 7)

    # ---------- 歩く：本物の記録
    sn = MotionSnippet()
    names = []
    for leg in sn.legs:
        for p, c, ax in sn.dofs_per_leg:
            names.append(f"{'c_thorax' if p == 'thorax' else f'{leg}_{p}'}-{leg}_{c}-{ax}")
    # flygym と同じく Savitzky-Golay で平滑化してから、WALK_FPS で取り出す
    from scipy.signal import savgol_filter
    win = int(0.03 * sn.data_fps); win += 1 - win % 2
    ang = savgol_filter(sn.joint_angles, window_length=win, polyorder=3, axis=0)
    n_raw = ang.shape[0]
    src_t = np.arange(n_raw) / sn.data_fps
    t = np.arange(0, n_raw / sn.data_fps, 1 / WALK_FPS)
    walk = []
    for ti in t:
        flat = np.array([np.interp(ti, src_t, ang[:, li, di]) for li in range(len(sn.legs)) for di in range(len(sn.dofs_per_leg))])
        full = dict(neutral); full.update(zip(names, flat))
        d.qpos[:] = 0
        for k, v in full.items():
            d.qpos[m.jnt_qposadr[jid[k]]] = v
        mj.mj_kinematics(m, d)
        walk.append(np.concatenate([d.xpos[1:], d.xquat[1:]], axis=1).astype(np.float32))
    walk = np.stack(walk)

    # 地面の高さ：足先の高さの下位10%（接地している足がだいたい地面に乗るように）
    foot = [bodies.index(f"{l}_tarsus5") for l in LEGS]
    fz = walk[:, foot, 2]
    ground = float(np.percentile(fz, 10))
    # 歩く速さ：接地している足が後ろへ動く速さ ≒ 体が前へ進む速さ
    vx = np.diff(walk[:, foot, 0], axis=0) * WALK_FPS
    stance = fz[1:] < np.percentile(fz, 40)
    speed = float(-np.median(vx[stance]))

    # ---------- 手で付けた動き
    def clip(dur, fn):
        return np.stack([pose(fn(k / FPS)) for k in range(int(dur * FPS))])

    def sniff(t):
        s = np.sin(2 * np.pi * 6 * t)
        return {"l_pedicel-l_funiculus-pitch": 0.35 * s, "r_pedicel-r_funiculus-pitch": -0.35 * s,
                "c_head-l_pedicel-yaw": 0.15 * s, "c_head-r_pedicel-yaw": 0.15 * s,
                "c_thorax-c_head-pitch": 0.12 * min(1, t * 4)}

    def tap(t):
        out = {}
        for i, leg in enumerate(["lf", "rf"]):
            ph = np.sin(2 * np.pi * 5 * t + i * np.pi)
            lift = max(0.0, ph)
            out[f"c_thorax-{leg}_coxa-pitch"] = -0.35 * min(1, t * 3)      # 前脚を前へ
            out[f"{leg}_coxa-{leg}_trochanterfemur-pitch"] = -0.45 * lift  # 持ち上げて
            out[f"{leg}_trochanterfemur-{leg}_tibia-pitch"] = 0.5 * lift   # トンと下ろす
        out["c_thorax-c_head-pitch"] = 0.12
        return out

    def drink(t):
        dur = 2.4
        e = min(1, t / 0.4) if t < dur - 0.4 else max(0, (dur - t) / 0.4)  # 伸ばす→保つ→しまう
        pump = 0.08 * np.sin(2 * np.pi * 4 * t) * (e > 0.99)
        return {"c_head-c_rostrum-pitch": -1.25 * e - pump, "c_rostrum-c_haustellum-pitch": -0.9 * e,
                "c_thorax-c_head-pitch": 0.25 * e}

    def takeoff(t):
        spread = min(1, t / 0.15)
        flap = np.sin(2 * np.pi * 14 * t) * (t > 0.15)
        out = {"c_thorax-l_wing-roll": -1.4 * spread, "c_thorax-r_wing-roll": -1.4 * spread,
               "c_thorax-l_wing-yaw": 0.9 * flap, "c_thorax-r_wing-yaw": 0.9 * flap}
        for leg in LEGS:  # 中脚で地面を蹴ったあと、脚をたたむ
            push = 0.5 * np.exp(-((t - 0.12) / 0.06) ** 2) if leg[1] == "m" else 0
            fold = min(1, max(0, (t - 0.2) / 0.3))
            out[f"{leg}_trochanterfemur-{leg}_tibia-pitch"] = -push + 0.6 * fold
        return out

    clips = {
        "walk": {"frames": walk, "loop": True, "real": True, "fps": WALK_FPS},
        "idle": {"frames": clip(1.0, lambda t: {"l_pedicel-l_funiculus-pitch": 0.05 * np.sin(2 * np.pi * t),
                                                "r_pedicel-r_funiculus-pitch": -0.05 * np.sin(2 * np.pi * t)}), "loop": True},
        "sniff": {"frames": clip(1.4, sniff), "loop": False},
        "tap": {"frames": clip(1.6, tap), "loop": False},
        "drink": {"frames": clip(2.4, drink), "loop": False},
        "takeoff": {"frames": clip(1.2, takeoff), "loop": True},
    }
    # 原点を胸部の真下の地面に
    origin = np.array([float(walk[0, 0, 0]), 0.0, ground], dtype=np.float32)
    for c in clips.values():
        c["frames"][:, :, :3] -= origin

    # ---------- 体節の形（体節の座標系で）
    parts = []
    for g in range(m.ngeom):
        if m.geom_type[g] != mj.mjtGeom.mjGEOM_MESH:
            continue
        b = int(m.geom_bodyid[g]) - 1
        mid = m.geom_dataid[g]
        v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].astype(np.float64)
        f = m.mesh_face[m.mesh_faceadr[mid]:m.mesh_faceadr[mid] + m.mesh_facenum[mid]]
        R = np.zeros(9); mj.mju_quat2Mat(R, m.geom_quat[g])
        v = v @ R.reshape(3, 3).T + m.geom_pos[g]
        name = bodies[b]
        kind = next((k for k in ["eye", "wing", "haltere", "arista", "abdomen", "tarsus"] if k in name), "default")
        parts.append({"body": b, "color": COLOR[kind], "alpha": 0.45 if kind == "wing" else 1.0,
                      "pos": b64(np.round(v * 5000).astype(np.int16)),  # 0.2µm 単位
                      "idx": b64(f.astype(np.uint16))})

    out = {
        "source": "NeuroMechFly v2 / flygym (Apache-2.0), Lobato-Rios et al. 2022; Wang-Chen et al. 2024",
        "bodies": bodies, "fps": FPS, "unit": "mm", "walk_speed_mm_s": speed,
        "parts": parts,
        "clips": {k: {"n": len(c["frames"]), "loop": c["loop"], "real": c.get("real", False), "fps": c.get("fps", FPS),
                      "data": b64(c["frames"].astype(np.float32))} for k, c in clips.items()},
    }
    OUT.write_text("window.FLY3D = " + json.dumps(out, separators=(",", ":")) + ";\n")
    print(f"書き出しました: {OUT.relative_to(ROOT)} ({OUT.stat().st_size/1e6:.1f} MB)")
    print(f"  体節 {len(bodies)}、部品 {len(parts)}、歩く速さ {speed:.1f} mm/s（記録から推定）")


if __name__ == "__main__":
    main()
