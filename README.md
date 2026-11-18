# rep-fly-project

本物のハエの脳の配線（雄CNSコネクトーム）を使った個人開発のモノレポ。
コネクトームの読み込みと共通データは `fly-core` に集め、各アプリはそこから使う。

```
rep-fly-project/
├── fly-core/        共通部品：コネクトーム・受容体データの読み込み、キノコ体モデル、3D用データ
├── fly-sommelier/   ハエのワインソムリエ（Webアプリ）
└── fly-completer/   ハエのPython補完（VSCode 拡張機能）
```

## fly-core（共通部品）

| もの | 中身 | 使っているアプリ |
|---|---|---|
| `pipeline/mcns.py` | 雄CNS と DoOR のダウンロード・読み込み。糸球体 → PN → KC の選び方（`olfactory_front`）と香り分子 → 糸球体の応答（`odor_vector`）| すべて |
| `pipeline/build_mb.py` → `data/mb_circuit.json` | キノコ体の配線をニューロン1個ずつ（MBON・ドーパミン細胞・APL を含む）＋香りの図書館 182 分子 | fly-completer |
| `js/mb_spiking.js` | スパイクで動くキノコ体（Shiu et al. 2024 と同じ LIF 定数） | fly-completer |
| `pipeline/build_scene3d.py` → `data/scene3d.js` | 嗅覚経路のニューロン約4,500本の形（bodyId つき）と脳の領域のメッシュ | fly-sommelier |
| `pipeline/build_fly_body.py` → `data/fly3d.js` | ハエの体（NeuroMechFly）と動き（歩行は本物の記録） | fly-sommelier |

ダウンロードしたコネクトーム（約570MB）は `fly-core/raw/` にまとめて保存し、どのアプリのデータ作りでも使い回す（git には入れない）。

## すぐ動かす

- **ワインソムリエ**：`fly-sommelier/web/index.html` をブラウザで開く（サーバー不要）
- **Python補完**：`cd fly-completer && node tools/build_extension.js` のあと `vscode/` を VSIX にパッケージしてインストール（詳しくは fly-completer/README.md）

## データを作り直す

```
pip install -r fly-core/requirements.txt
python fly-core/pipeline/build_mb.py          # → fly-core/data/mb_circuit.json
python fly-core/pipeline/build_scene3d.py     # → fly-core/data/scene3d.js
python fly-core/pipeline/build_fly_body.py    # → fly-core/data/fly3d.js（flygym が必要）
python fly-sommelier/pipeline/build_data.py   # → fly-sommelier/web/data/app_data.js
```

## ライセンス

- このリポジトリのコード：MIT（`LICENSE`）
- データやそこから作ったファイルは、それぞれの元のライセンスに従う → `THIRD_PARTY.md`
