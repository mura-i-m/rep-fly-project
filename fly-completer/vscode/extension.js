// extension.js — ハエの補完（VSCode 拡張機能）
//
// 拡張機能の中で、ハエのキノコ体（スパイクモデル）をそのまま動かす。
//   1. Python を打つと、打ちかけの単語の匂いをハエが嗅ぐ
//   2. サイドパネルで、ハエが前脚でタッピングしながら考える（脳の発火に合わせて動く）
//   3. 答えが出たら、薄い文字で補完が出る（Tab で確定）
//   4. 打ち終えた単語から、その場で学習する（ドーパミン）
const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const FlyWordCompleter = require("./brain/word_completer.js");

let fly = null;
let view = null;
let status = null;
let personalPath = null;
let saveTimer = null;
let lastKey = "", lastResult = null;

const cfg = () => vscode.workspace.getConfiguration("flyCompleter");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const post = (msg) => { if (view) view.webview.postMessage(msg); };

function loadFly(context) {
  const dir = path.join(context.extensionPath, "brain");
  const read = (f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf8"));
  const brain = read("brain.json");
  fly = new FlyWordCompleter(read("mb_circuit.json"), read("alphabet.json"), brain.opt || {});
  fly.load(brain);
  personalPath = path.join(context.globalStorageUri.fsPath, "brain-personal.json");
  if (fs.existsSync(personalPath)) {
    try { fly.load(JSON.parse(fs.readFileSync(personalPath, "utf8"))); } catch (e) { /* 壊れていたら初期の脳のまま */ }
  }
}

function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fs.mkdirSync(path.dirname(personalPath), { recursive: true });
    fs.writeFileSync(personalPath, JSON.stringify(fly.save()));
  }, 5000);
}

/** 嗅いでいるあいだの発火を 5ms ごとにまとめる（タッピングのリズムになる） */
function think(text) {
  const frames = [];
  let kc = 0, mbon = 0, n = 0;
  const res = fly.complete(text, (t, mb) => {
    for (let i = 0; i < mb.nKC; i++) kc += mb.kc.spk[i];
    for (let i = 0; i < mb.nM; i++) mbon += mb.mbon.spk[i];
    if (++n % 10 === 0) { frames.push([kc, mbon]); kc = 0; mbon = 0; }
  });
  return { ...res, frames };
}

const provider = {
  async provideInlineCompletionItems(doc, pos, _ctx, token) {
    if (!cfg().get("enabled") || !fly) return;
    const line = doc.lineAt(pos.line).text.slice(0, pos.character);
    if (!/(^|[^A-Za-z0-9_.])[A-Za-z_]+$/.test(line)) return; // 単語の打ちかけのときだけ（属性の途中は除く）
    const text = "\n" + line;
    await sleep(120); // 打っている最中は待つ
    if (token.isCancellationRequested) return;

    let r;
    if (text.slice(-12) === lastKey) r = lastResult;
    else {
      r = think(text);
      lastKey = text.slice(-12); lastResult = r;
      const p = r.prediction;
      post({ type: "thinking", prefix: r.prefix, context: fly.context(text).join(""), odors: p.odors, frames: r.frames, ms: cfg().get("thinkingTime") });
      status.text = "$(loading~spin) 🪰 クンクン…";
      const wait = cfg().get("thinkingTime");
      const t0 = Date.now();
      while (Date.now() - t0 < wait) {
        if (token.isCancellationRequested) { status.text = "🪰"; post({ type: "cancel" }); lastKey = ""; return; }
        await sleep(30);
      }
      post({ type: "answer", prefix: r.prefix, word: p.word, suffix: r.suffix, ranking: p.ranking });
    }
    status.text = r.suffix ? `🪰 ${r.prefix}${r.suffix}?` : "🪰 …わからない";
    if (!r.suffix) return;
    const item = new vscode.InlineCompletionItem(r.suffix, new vscode.Range(pos, pos));
    item.command = { command: "flyCompleter.accepted", title: "", arguments: [r.prefix + r.suffix] };
    return [item];
  },
};

/** 打ち終えた単語（区切り文字が来た直前の単語）から学習する */
function learnFromTyping(e) {
  if (!cfg().get("learnWhileTyping") || !fly || e.document.languageId !== "python") return;
  for (const ch of e.contentChanges) {
    if (ch.text.length !== 1 || /[A-Za-z0-9_]/.test(ch.text)) continue;
    const pos = ch.range.start;
    const before = e.document.lineAt(pos.line).text.slice(0, pos.character);
    const m = before.match(/(^|[^A-Za-z0-9_.])([A-Za-z_]+)$/);
    if (!m || !fly.wordToUnit.has(m[2])) continue;
    const word = m[2];
    const head = "\n" + before.slice(0, before.length - word.length);
    setImmediate(() => {
      let miss = 0;
      for (let L = 1; L <= Math.min(3, word.length - 1); L++) {
        const r = fly.train(head + word.slice(0, L), word);
        if (r && !r.ok) miss++;
      }
      post({ type: "learned", word, miss });
      lastKey = "";
      scheduleSave();
    });
  }
}

class FlyViewProvider {
  constructor(context) { this.context = context; }
  resolveWebviewView(webviewView) {
    view = webviewView;
    const media = vscode.Uri.joinPath(this.context.extensionUri, "media");
    webviewView.webview.options = { enableScripts: true, localResourceRoots: [media] };
    const uri = (f) => webviewView.webview.asWebviewUri(vscode.Uri.joinPath(media, f));
    const nonce = Math.random().toString(36).slice(2);
    webviewView.webview.html = `<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webviewView.webview.cspSource}; script-src 'nonce-${nonce}';">
<link rel="stylesheet" href="${uri("fly.css")}"></head><body>
<div id="app"></div>
<script nonce="${nonce}" src="${uri("fly.js")}"></script></body></html>`;
    webviewView.onDidDispose(() => { view = null; });
    const s = fly.stats;
    setTimeout(() => post({ type: "hello", words: fly.units.map((u) => u.word), learned: s.seen }), 300);
  }
}

function activate(context) {
  loadFly(context);
  status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  status.text = "🪰"; status.tooltip = "ハエの補完"; status.command = "flyCompleter.show"; status.show();
  context.subscriptions.push(
    status,
    vscode.languages.registerInlineCompletionItemProvider({ language: "python" }, provider),
    vscode.window.registerWebviewViewProvider("flyCompleter.view", new FlyViewProvider(context)),
    vscode.workspace.onDidChangeTextDocument(learnFromTyping),
    vscode.commands.registerCommand("flyCompleter.show", () => vscode.commands.executeCommand("flyCompleter.view.focus")),
    vscode.commands.registerCommand("flyCompleter.accepted", (word) => post({ type: "accepted", word })),
    vscode.commands.registerCommand("flyCompleter.toggle", async () => {
      const on = !cfg().get("enabled");
      await cfg().update("enabled", on, vscode.ConfigurationTarget.Global);
      status.text = on ? "🪰" : "🪰(お休み)";
    }),
    vscode.commands.registerCommand("flyCompleter.reset", () => {
      if (fs.existsSync(personalPath)) fs.renameSync(personalPath, personalPath + ".bak");
      loadFly(context); lastKey = "";
      vscode.window.showInformationMessage("ハエが、あなたから覚えたことを忘れました（最初に学習した状態に戻りました）");
    }),
  );
}

function deactivate() {
  if (fly && personalPath) {
    fs.mkdirSync(path.dirname(personalPath), { recursive: true });
    fs.writeFileSync(personalPath, JSON.stringify(fly.save()));
  }
}

module.exports = { activate, deactivate };
