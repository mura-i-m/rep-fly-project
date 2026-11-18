# 使っているデータ・ライブラリと、そのライセンス

| 元 | ライセンス | このリポジトリで含まれる場所 |
|---|---|---|
| 雄CNSコネクトーム male CNS v1.0（Berg et al., Cell 2026）https://male-cns.janelia.org/ | CC BY 4.0 | `fly-core/data/*`、`fly-sommelier/web/data/app_data.js`（配線・ニューロンの形・脳の領域のメッシュから作ったもの） |
| DoOR 2.0（Münch & Galizia, Scientific Reports 2016）https://github.com/ropensci/DoOR.data | CC BY-SA 4.0 | 受容体応答から作った部分：`fly-core/data/mb_circuit.json` の `odor_library`、`fly-sommelier/web/data/app_data.js` の `compounds`。これらのファイルは CC BY-SA 4.0 として扱う |
| NeuroMechFly v2 / flygym（Lobato-Rios et al., Nature Methods 2022; Wang-Chen et al., Nature Methods 2024）https://github.com/NeLy-EPFL/flygym | Apache-2.0 | `fly-core/data/fly3d.js`（体の形と歩行の記録から作ったもの）。ライセンス文：`fly-sommelier/web/vendor/LICENSE-NeuroMechFly` |
| Shiu et al., Nature 2024（全脳 LIF モデル） | 論文（定数のみ参照） | `fly-core/js/mb_spiking.js` |
| Three.js r147 | MIT | `fly-sommelier/web/vendor/three.min.js`、`OrbitControls.js`（`vendor/LICENSE`） |
| Lucide アイコン | ISC | `fly-sommelier/web/icons.js`（`vendor/LICENSE-lucide`） |
| Python 標準ライブラリのソースコード | PSF License | `fly-completer/corpus/`（補完の学習・テスト用コーパス） |

生まれつきの好み（`fly-sommelier/data/innate_valence.json`）は、ファイル内に記した各論文の行動実験の結果をもとにした手作りの印。
