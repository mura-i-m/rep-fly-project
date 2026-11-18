# fly-core — ハエの脳の共通部品

rep-fly-project のアプリ（fly-sommelier・fly-completer）が共通に使う部品。コネクトームはすべてここから読む。

## 中身

| ファイル | 内容 |
|---|---|
| `pipeline/mcns.py` | 雄CNS と DoOR のダウンロード・読み込み（`raw/` に保存して使い回す）。糸球体 → PN → KC の選び方 `olfactory_front()`、香り分子 → 糸球体の応答 `odor_vector()` |
| `pipeline/build_mb.py` | キノコ体の配線を**ニューロン1個ずつ**取り出す → `data/mb_circuit.json`（2.7MB） |
| `pipeline/build_scene3d.py` | 嗅覚経路のニューロンの形（bodyId つき）と脳の領域のメッシュ → `data/scene3d.js` |
| `pipeline/build_fly_body.py` | ハエの体（NeuroMechFly）と動き → `data/fly3d.js`（flygym が必要） |
| `js/mb_spiking.js` | スパイクで動くキノコ体。Node でもブラウザでも動く |

## 回路

```
匂い → 糸球体 47 → PN 254（ポアソン発火）
     → KC 3,763（LIF）⇄ APL 2（KC 全体へのブレーキ）
     → MBON 97（LIF）
ドーパミン細胞 332（PAM / PPL1）＝先生役：発火すると、その区画で「いま発火した KC → MBON」の結合を弱める
```

- ニューロンの式と定数は Shiu et al. (2024) の全脳 LIF モデルと同じ（1シナプス 0.275 mV、τm 20ms、τs 5ms）
- 全脳ではなくキノコ体だけを動かす
- 匂いは DoOR 2.0 の受容体応答。受容体の測定が多い 182 分子を「香りの図書館」として収録
- 50ms 嗅がせるのに約 10ms（Node、M系Mac相当）

## 調整つまみ（`new MushroomBody(data, opt)`）

| つまみ | 意味 | 補完で使っている値 |
|---|---|---|
| `pnGain` / `pnMax` | 糸球体の反応 → PN の発火の強さ／上限 Hz | 3 / 300 |
| `kcGain` | PN → KC の強さ | 1.2 |
| `aplKCGain` | APL のブレーキの強さ（KC の発火の少なさを決める） | 4（KC の約2.5%が発火） |
| `mbonDrive` | KC → MBON の強さ（MBON ごとに入力の総量を揃えたうえでの倍率） | 2000 |
| `lr` / `lrUp` | ドーパミン1回あたりの結合の減り方／戻り方 | 調整中 |

## データを作り直す

```
pip install -r requirements.txt
python pipeline/build_mb.py        # 初回は約570MBをダウンロードして raw/ に保存。メモリ6GB程度
python pipeline/build_scene3d.py   # 骨格約4,500本とメッシュを raw/ に保存
python pipeline/build_fly_body.py  # pip install "flygym @ git+https://github.com/NeLy-EPFL/flygym.git"
```

出典: male CNS v1.0 (Berg et al., Cell 2026, CC BY 4.0) / DoOR 2.0 (Münch & Galizia, Sci Rep 2016, CC BY-SA 4.0) / Shiu et al. (Nature 2024) / NeuroMechFly v2 (Apache-2.0)。詳しくは ../THIRD_PARTY.md
