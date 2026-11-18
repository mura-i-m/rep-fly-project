# 🪰⌨️ fly-completer — ハエにPythonの補完をさせる

ハエのキノコ体（`../fly-core`）に、打ちかけのコードを「匂い」として嗅がせ、続きの単語を当てさせる VSCode 拡張機能。
考えているあいだ、サイドパネルのハエが脳の発火に合わせて前脚でタッピングし、答えが出ると薄い文字で補完が出る。

## インストール

```
node tools/build_extension.js          # ../fly-core の脳の部品と学習済みの結合を vscode/brain/ にコピー
cd vscode && npx @vscode/vsce package  # fly-completer-0.1.0.vsix ができる
code --install-extension fly-completer-0.1.0.vsix
```

または VSCode のコマンドパレット →「VSIX からのインストール」。Python ファイルを開いて `def` などを打ちはじめると動く。
左のアクティビティバーのハエのアイコンでパネルが開く。

## 仕組み

1. 直前4文字を、文字ごとに割り当てた実在の香り分子（DoOR）の「残り香」として混ぜる（新しい文字ほど濃い）
2. キノコ体をスパイクで 200ms（ハエの体感時間）動かす。計算は約40ms
3. MBON を「主にどのドーパミン細胞（タイプ×左右）が入るか」で分けると**ちょうど30区画**。1区画＝1単語
4. 「学習前と比べて入力がいちばん減った割合（＝黙った）区画」の単語が答え
5. 間違えたら、正解の区画のドーパミン細胞で「いま発火した KC → MBON」を弱め、誤答の区画は戻す
6. 一回ごとのぶれは「長期記憶」（ゆっくり追従する重み）でならし、補完にはそちらを使う

## 結果（テスト用コード＝学習に使っていない標準ライブラリのモジュール）

| 予測の単位 | 正解率 |
|---|---|
| 1文字（30文字） | 約12%（最頻値の当てずっぽう 13% と同程度）→ 断念 |
| 30語（先頭1〜3文字から） | **56%**（2文字以上打ったとき 61%） |

`de→def` `ret→return` `(sel→self` `imp→import` `No→None` `Tr→True` `pri→print` `ex→except` は出る。
`fro→from` `whi→while` `lamb→lambda` はまだ出ない（MBON が1〜2個しかない小さな区画に割り当たった単語が苦手）。

### 本物の配線に忠実でない近似（ブログで明記するところ）

- 全脳ではなくキノコ体だけを動かす
- MBON ごとに KC からの入力の総量を揃えた（ホメオスタシスの近似）
- ドーパミンは担当区画の MBON にだけ一様に効かせた（区画の外へのしみ出しは無視）
- ハエの答えが打ちかけの文字と合わないときは補完を出さない

## ファイル

| 場所 | 内容 |
|---|---|
| `js/word_completer.js` | 単語補完の本体 |
| `js/completer.js` | 1文字予測版（断念したもの） |
| `tools/build_alphabet.js` | 文字 → 香り分子、MBON → 30区画の表 |
| `tools/build_words.js` | 30区画に単語を割り当てる |
| `tools/train_words.js` | 学習（`node tools/train_words.js 8000 3`、約4分）→ `data/brain.json` |
| `tools/build_extension.js` | 脳の部品と学習結果を `vscode/brain/` にコピー |
| `vscode/` | 拡張機能。`cd vscode && npx @vscode/vsce package --allow-missing-repository` で .vsix を作る |
| `experiments/` | 読み出し方式の比較実験 |

作り直す順番: `build_alphabet.js` → `build_words.js` → `train_words.js` → `build_extension.js` → パッケージ
