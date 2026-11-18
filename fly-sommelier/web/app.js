// app.js — 2つのページ
//   しつける：ボトル＋「砂糖／電気」を選ぶ → 匂いと一緒に与える → 脳で学習（本物の実験の訓練と同じ）
//   当ててもらう：ボトルを選ぶ → ハエが嗅いで判断・行動する（学習しない）→ 好みと合っていたか答え合わせ
(function () {
  const DATA = window.APP_DATA;
  const STORE = "fly-sommelier.v3";
  const $ = (s) => document.querySelector(s);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const V = DATA.wine.varieties;
  const nPam = DATA.dan_types.filter((d) => d.startsWith("PAM")).length;
  const nPpl1 = DATA.dan_types.length - nPam;

  // ---------- アイコン
  const setIcon = (el, name, label = "", size = 20) => { el.innerHTML = icon(name, size) + (label ? `<span>${label}</span>` : ""); };
  const toolIcons = { history: "list", lab: "flask-conical", about: "info" };
  document.querySelectorAll("#hud-tools [data-drawer]").forEach((b) => setIcon(b, toolIcons[b.dataset.drawer]));
  setIcon($("#view-reset"), "rotate-ccw");
  setIcon($("#brain-size"), "maximize-2", "", 16);
  document.querySelectorAll(".close").forEach((b) => setIcon(b, "x", "", 18));
  setIcon($('#mode [data-mode="train"]'), "graduation-cap", "しつける", 18);
  setIcon($('#mode [data-mode="test"]'), "target", "当ててもらう", 18);
  setIcon($('#answer [data-ok="1"]'), "check", "合っていた", 26);
  setIcon($('#answer [data-ok="0"]'), "x", "違った", 26);
  setIcon($("#to-train"), "graduation-cap", "このワインをしつける", 18);
  const usIcon = (r, size = 14) => (r > 0 ? `<span class="mark sugar">${icon("candy", size)}</span>` : `<span class="mark zap">${icon("zap", size)}</span>`);

  // ---------- 保存（ブラウザの中だけ）
  function loadState() {
    try {
      const v3 = JSON.parse(localStorage.getItem(STORE));
      if (v3) return v3;
      const v2 = JSON.parse(localStorage.getItem("fly-sommelier.v2")); // 前のバージョンの評価は、しつけとして引き継ぐ
      if (v2) return { ...v2, trainings: (v2.ratings || []).filter((r) => r.r !== 0), tests: [] };
    } catch (e) { /* 読めなければ最初から */ }
    return null;
  }
  const state = Object.assign({ trainings: [], tests: [], random: false, gluExcites: true, mode: "test" }, loadState() || {});
  delete state.ratings;
  function saveState() {
    try { localStorage.setItem(STORE, JSON.stringify(state, (k, v) => (k === "active" ? undefined : v))); } catch (e) { /* 保存できない環境 */ }
  }

  // ---------- 脳：しつけの記録だけで学び直す
  let brain;
  const keyOf = (w) => w.variety + "|" + [...(w.notes || [])].sort().join(",");
  function rebuild() {
    brain = new FlyBrain(DATA, { randomWiring: state.random, glutamateExcites: state.gluExcites });
    for (const t of state.trainings) {
      const smell = brain.sniff(brain.mixture(t.variety, t.notes));
      t.active = smell.active;
      brain.learn(smell, t.r);
    }
  }

  // ソムリエのレベル：テストで好みと合っていた割合（直近15回）
  function renderLevel() {
    const ts = state.tests.slice(-15), ok = ts.filter((t) => t.ok).length, n = ts.length, acc = n ? ok / n : 0;
    const lv = 1 + [[3, 0.5], [6, 0.6], [10, 0.7], [15, 0.8]].filter(([m, a]) => n >= m && acc >= a).length;
    $("#level").innerHTML = `<span class="lv">Lv ${lv}</span>` + (n ? `テストの的中率 ${Math.round(acc * 100)}%（${ok}/${n}）` : "まだテストしていません");
  }

  // ---------- 3D
  let viewer = null, flyScene = null, runId = 0;
  window.startViewer = () => {
    try { viewer = window.brainViewer = new Viewer3D($("#brain-pane"), window.SCENE3D, DATA); $("#brain-pane .loading").remove(); }
    catch (e) { $("#brain-pane .loading").textContent = "脳の3D表示を開けませんでした（" + e.message + "）"; }
  };
  window.startFly = () => {
    try { flyScene = window.flyScene = new FlyScene($("#scene"), window.FLY3D); $("#scene .loading").remove(); idleCaption(); }
    catch (e) { $("#scene .loading").textContent = "ハエの3D表示を開けませんでした（" + e.message + "）"; }
  };
  const brainWin = $("#brain-win");
  function brainFull(on) {
    brainWin.classList.toggle("full", on); brainWin.classList.toggle("mini", !on);
    setIcon($("#brain-size"), on ? "minimize-2" : "maximize-2", "", 16);
  }
  $("#brain-size").onclick = () => brainFull(!brainWin.classList.contains("full"));
  const brainStep = (title, sub) => { $("#brain-step").innerHTML = `<b>${title}</b><span>${sub}</span>`; };
  $("#view-reset").onclick = () => {
    if (viewer) { viewer.camera.position.set(0, 300, -9000 * Math.max(1, 1.1 / viewer.camera.aspect)); viewer.controls.target.set(0, 0, 0); viewer.controls.autoRotate = true; }
    flyScene && flyScene.overview();
  };
  const caption = (main, sub = "") => { $("#caption").innerHTML = main ? main + (sub ? `<small>${sub}</small>` : "") : ""; };
  const idleCaption = () => state.mode === "train"
    ? caption("しつけるワインを選んでください", "匂いと一緒に、砂糖（ごほうび）か電気ショック（罰）を与えます")
    : caption("ハエに嗅がせるワインを選んでください", "ハエが脳で判断して、飲むか逃げるかを見せます");

  // ---------- 言葉
  function word(v) {
    if (v > 0.5) return "大好き"; if (v > 0.15) return "好き"; if (v > -0.15) return "どちらでもない";
    if (v > -0.5) return "苦手"; return "大嫌い";
  }
  const label = (w) => w.name || (V[w.variety] ? V[w.variety].label : "品種不明のワイン");
  const bar = (v) => `<div class="bar"><i style="left:${(Math.max(-1, Math.min(1, v)) + 1) * 50}%"></i></div>`;
  const bars = (s) => `<div class="bars">
      <span>生まれつき（側角）</span>${bar(s.innate)}
      <span>しつけ（キノコ体）</span>${bar(s.learned)}
      <span><b>総合</b></span>${bar(brain.overall(s))}
      <div class="scale"><span>苦手</span><span>ふつう</span><span>好き</span></div></div>`;

  // 共通：匂いが届いてケニオン細胞が光るまで（①②）
  async function showSmell(smell, alive) {
    brainStep("① 触角葉に匂いが届く", `${DATA.glomeruli.length}個の糸球体から、投射ニューロンへ信号が流れます`);
    brainFull(true);
    await wait(500); viewer && viewer.showPN(smell.pn);
    await wait(1800); if (!alive()) return false;
    viewer && viewer.showKC(smell.active, smell.innate);
    brainStep(`② ケニオン細胞 ${smell.active.length}個が発火`, `同時に側角では、生まれつきの好み：${word(smell.innate)}`);
    await wait(2000);
    return alive();
  }
  function busy(on) { $("#shelf").classList.toggle("busy", on); $("#mode").classList.toggle("locked", on); }

  // ========== しつける ==========
  async function train(wine, r) {
    const id = ++runId, alive = () => id === runId;
    closePops(); busy(true); viewer && viewer.dim(); brainFull(false);
    const smell = brain.sniff(brain.mixture(wine.variety, wine.notes));
    flyScene && flyScene.pour(V[wine.variety] ? V[wine.variety].color : "赤");
    flyScene && flyScene.backToDrop();
    caption(`${label(wine)} の匂いと一緒に、${r > 0 ? "砂糖をあげます" : "床から弱い電気ショック"}`,
      "本物のハエの学習実験と同じ組み合わせです（匂い＋砂糖／匂い＋電気ショック）");
    await wait(1100); if (!alive()) return;
    if (flyScene) { await flyScene.sniff(); if (!alive()) return; await (r > 0 ? flyScene.reward() : flyScene.shock()); }
    if (!alive()) return;
    caption("");

    // 脳の中：匂い（①②）→ ドーパミン（③）→ 結合が変わる（④）
    if (!(await showSmell(smell, alive))) return;
    const res = brain.learn(smell, r);
    const t = { id: Date.now(), name: wine.name, variety: wine.variety, notes: wine.notes, r, active: smell.active };
    state.trainings.push(t); saveState(); renderAll();
    const kind = r > 0 ? "ごほうび" : "罰";
    const ratio = res.surprise / (r > 0 ? nPam : nPpl1);
    brainStep(`③ ${kind}のドーパミンが流れる（量 ${res.surprise.toFixed(1)}）`,
      (r > 0 ? "ごほうび担当（PAM）から、キノコ体の区画へ" : "罰担当（PPL1）から、キノコ体の区画へ") +
      (ratio < 0.65 ? "。もう覚えかけているので控えめ" : "。まだ予想していなかったので、たくさん"));
    viewer && viewer.showDopamine(res.dan, brain.isPam);
    viewer && viewer.flowDopamine(res.dan, brain.isPam);
    await wait(2600); if (!alive()) return;

    const outSum = (M, sgn) => M.reduce((s, x, m) => s + (DATA.mbon_sign[m] === sgn ? brain.mbonSize[m] * x : 0), 0);
    const a0 = outSum(smell.mbon, 1), a1 = outSum(res.mbonAfter, 1), v0 = outSum(smell.mbon, -1), v1 = outSum(res.mbonAfter, -1);
    const pct = (x0, x1) => `${x1 >= x0 ? "+" : ""}${Math.round((x1 / x0 - 1) * 100)}%`;
    const target = DATA.mbon_sign.map((sg, m) => (sg === (r > 0 ? -1 : 1) && res.da[m] > 0.2 ? m : -1)).filter((m) => m >= 0);
    const where = viewer && viewer.mbonCenter(target);
    viewer && viewer.weaken(smell.active, smell.mbon, res.mbonAfter, DATA.mbon_sign);
    where && viewer.showLabel(where, r > 0
      ? `<b>「避ける」出力への結合が弱まる</b>いま光ったケニオン細胞からの結合だけ <span class="down">${pct(v0, v1)}</span>`
      : `<b>「近づく」出力への結合が弱まる</b>いま光ったケニオン細胞からの結合だけ <span class="down">${pct(a0, a1)}</span>`);
    brainStep("④ 結合が書き換わった", `<span class="outs">
        <span class="k">近づく出力</span><span class="ar">しつけ前 → 後</span><span class="appr">${pct(a0, a1)}</span>
        <span class="k">避ける出力</span><span class="ar">しつけ前 → 後</span><span class="avoid">${pct(v0, v1)}</span></span><br>` +
      (r > 0 ? "この匂いを次に嗅いだら「近づく」が勝ちやすくなる" : "この匂いを次に嗅いだら「避ける」が勝ちやすくなる"));
    await wait(3400); if (!alive()) return;
    viewer && viewer.hideLabel();
    brainFull(false);
    caption(`しつけました。${label(wine)} の好き度：${word(res.before)} → ${word(res.after)}`,
      "「当ててもらう」で、ハエが本当に覚えたか確かめられます");
    flyScene && flyScene.comeBack();
    busy(false);
  }

  // ========== 当ててもらう ==========
  let pending = null;
  async function test(wine) {
    const id = ++runId, alive = () => id === runId;
    closePops(); busy(true); $("#answer").classList.add("hidden");
    const smell = brain.sniff(brain.mixture(wine.variety, wine.notes));
    const decision = brain.overall(smell);
    viewer && viewer.dim(); brainFull(false);
    flyScene && flyScene.pour(V[wine.variety] ? V[wine.variety].color : "赤");
    caption(`${label(wine)} を一滴`, "ハエが歩いてきます。歩き方は本物のハエの関節の動きの記録（スロー再生）");
    await wait(600); if (!alive()) return;
    if (flyScene) await flyScene.approach(); if (!alive()) return;

    caption("触角で嗅いでいます");
    const sniffing = flyScene ? flyScene.sniff() : wait(1500);
    flyScene && flyScene.diveToHead();
    await wait(700); if (!alive()) return;
    caption("");
    if (!(await showSmell(smell, alive))) return;
    viewer && viewer.showMBON(smell.mbon, DATA.mbon_sign);
    const act = decision > 0.15 ? "drink" : decision < -0.15 ? "flee" : "leave";
    brainStep(`③ 判断：${word(decision)}`, act === "drink" ? "近づく側の出力が強い → 味見して飲む"
      : act === "flee" ? "避ける側の出力が強い → 逃げる" : "決めきれない → 少し離れる");
    await wait(2000); if (!alive()) return;
    await sniffing;

    brainFull(false);
    flyScene && flyScene.actionView();
    caption(act === "drink" ? "前脚でトントン味見して、口吻を伸ばして飲みます" : act === "flee" ? "飛んで逃げました" : "少し離れていきます");
    await wait(700); if (!alive()) return;
    const acting = flyScene ? (act === "drink" ? flyScene.tapAndDrink() : act === "flee" ? flyScene.flyAway() : flyScene.walkAway()) : wait(1500);
    await Promise.race([acting, wait(act === "flee" ? 2600 : 6500)]); if (!alive()) return;

    // 答え合わせ（学習はしない）
    pending = { ...wine, decision, trained: state.trainings.some((t) => keyOf(t) === keyOf(wine)) };
    caption("");
    $("#answer .q").textContent = `ハエの答え：${label(wine)} は「${word(decision)}」` +
      (act === "drink" ? "（飲みました）" : act === "flee" ? "（逃げました）" : "（離れました）");
    $("#pred").innerHTML = bars(smell);
    $("#to-train").classList.add("hidden");
    document.querySelectorAll("#answer .rate button").forEach((b) => (b.disabled = false));
    $("#answer").classList.remove("hidden");
    busy(false);
  }
  document.querySelectorAll("#answer .rate button").forEach((b) => {
    b.onclick = () => {
      if (!pending) return;
      const w = pending, ok = b.dataset.ok === "1";
      state.tests.push({ id: Date.now(), name: w.name, variety: w.variety, notes: w.notes, decision: w.decision, ok, trained: w.trained });
      saveState(); renderAll();
      if (ok) { finishTest("当たりです"); return; }
      // 外れたら、そのまましつけに移れる
      document.querySelectorAll("#answer .rate button").forEach((x) => (x.disabled = true));
      $("#to-train").classList.remove("hidden");
      $("#to-train").onclick = () => { const wine = { name: w.name, variety: w.variety, notes: w.notes }; finishTest(""); setMode("train"); openWine(wine); };
    };
  });
  function finishTest(msg) {
    pending = null; ++runId;
    $("#answer").classList.add("hidden");
    msg ? caption(msg, "次のワインを選んでください") : idleCaption();
    flyScene && flyScene.comeBack();
  }
  $("#skip").onclick = () => finishTest("");

  // ---------- ページの切り替え
  function setMode(m) {
    state.mode = m; saveState();
    document.body.classList.toggle("train", m === "train"); document.body.classList.toggle("test", m === "test");
    document.querySelectorAll("#mode button").forEach((b) => b.classList.toggle("on", b.dataset.mode === m));
    $("#shelf-main").textContent = m === "train" ? "しつけるワインを選ぶ" : "ハエに嗅がせるワインを選ぶ";
    $("#shelf-hint").textContent = m === "train" ? "ボトルを押すと、香りと「砂糖／電気」を選べます" : "香りのアイコンで、ラベルにある香りを足せます";
    closePops();
    if (!pending && !$("#shelf").classList.contains("busy")) idleCaption();
  }
  document.querySelectorAll("#mode button").forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));

  // ---------- ボトル棚
  const thin = new Set(Object.entries(DATA.compounds).filter(([, c]) => c.measured < 10).map(([n]) => n));
  const bottleSvg = (color) => {
    const fill = { 白: "#d9c56a", 赤: "#5c0418", 泡: "#e4d27e" }[color];
    return `<svg class="b" viewBox="0 0 40 100"><path d="M16 4h8v22c0 4 9 8 9 18v50a4 4 0 0 1-4 4H11a4 4 0 0 1-4-4V44c0-10 9-14 9-18z" fill="${color === "赤" ? "#2c2a25" : "#6f7f5c"}" opacity=".9"/>
      <path d="M8 56h24v30H8z" fill="${fill}" opacity=".95"/><rect x="11" y="60" width="18" height="14" rx="2" fill="#f6efe3"/>
      <rect x="15.5" y="1" width="9" height="6" rx="1.5" fill="${color === "泡" ? "#c9a64a" : "#7b1e3a"}"/></svg>`;
  };
  function renderShelf() {
    const box = $("#bottles"); box.innerHTML = "";
    const order = ["泡", "白", "赤"];
    for (const id of Object.keys(V).sort((a, b) => order.indexOf(V[a].color) - order.indexOf(V[b].color))) {
      const el = document.createElement("div");
      el.className = "bottle"; el.dataset.id = id;
      el.innerHTML = `${bottleSvg(V[id].color)}<div class="name">${V[id].label}</div><button class="notes-btn" title="香りを足す">${icon("sliders-horizontal", 14)}</button>`;
      el.onclick = (e) => {
        const wine = { variety: id, notes: [], name: "" };
        if (e.target.closest(".notes-btn") || state.mode === "train") openWine(wine); else test(wine);
      };
      box.appendChild(el);
    }
    renderShelfMarks();
  }
  function renderShelfMarks() {   // そのボトルに最後にしたしつけ
    document.querySelectorAll(".bottle").forEach((el) => {
      el.querySelector(".mark") && el.querySelector(".mark").remove();
      const last = [...state.trainings].reverse().find((t) => t.variety === el.dataset.id);
      if (last) el.insertAdjacentHTML("afterbegin", usIcon(last.r));
    });
  }

  // ワインのパネル（香り・名前と、ページに応じたボタン）
  for (const [w, comp] of Object.entries(DATA.wine.descriptors)) {
    const c = document.createElement("span");
    c.className = "chip"; c.dataset.word = w; c.textContent = w;
    if (Object.keys(comp).every((n) => thin.has(n))) c.innerHTML += `<span class="thin">（データ少）</span>`;
    c.onclick = () => c.classList.toggle("on");
    $("#aroma-chips").appendChild(c);
  }
  function openWine(wine) {
    closePops();
    $("#aroma-title").textContent = V[wine.variety].label;
    $("#aroma-name").value = wine.name || "";
    document.querySelectorAll("#aroma-chips .chip").forEach((c) => c.classList.toggle("on", (wine.notes || []).includes(c.dataset.word)));
    const read = () => ({ variety: wine.variety, name: $("#aroma-name").value.trim(),
      notes: [...document.querySelectorAll("#aroma-chips .chip.on")].map((c) => c.dataset.word) });
    const box = $("#aroma-actions"); box.innerHTML = "";
    const btn = (cls, ic, text, fn) => { const b = document.createElement("button"); b.className = "primary " + cls; setIcon(b, ic, text, 18); b.onclick = fn; box.appendChild(b); };
    if (state.mode === "train") {
      btn("", "candy", "砂糖をあげる（好き）", () => train(read(), 1));
      btn("shock", "zap", "電気を流す（苦手）", () => train(read(), -1));
    } else {
      btn("", "droplet", "この香りで嗅がせる", () => test(read()));
    }
    $("#aroma").classList.remove("hidden");
  }
  $("#aroma .close").onclick = () => $("#aroma").classList.add("hidden");

  // ---------- 引き出し（記録・実験・この脳について）
  const drawerTitles = { history: "記録", lab: "実験", about: "この脳について" };
  function closePops() { $("#aroma").classList.add("hidden"); $("#drawer").classList.add("hidden"); }
  document.querySelectorAll("#hud-tools [data-drawer]").forEach((b) => {
    b.onclick = () => {
      const k = b.dataset.drawer, d = $("#drawer");
      const open = !d.classList.contains("hidden") && d.dataset.on === k;
      closePops(); if (open) return;
      d.dataset.on = k; $("#drawer-title").textContent = drawerTitles[k];
      d.querySelectorAll("section").forEach((s) => s.classList.toggle("on", s.dataset.panel === k));
      d.classList.remove("hidden");
      if (k === "lab") drawDA();
    };
  });
  $("#drawer .close").onclick = () => $("#drawer").classList.add("hidden");

  function renderHistory() {
    const sub = (w) => [V[w.variety] ? V[w.variety].label : "", ...(w.notes || [])].filter(Boolean).join("・");
    const ulT = $("#history-train");
    ulT.innerHTML = state.trainings.length ? "" : `<li class="muted">まだありません。「しつける」でワインを教えてください。</li>`;
    for (const t of [...state.trainings].reverse()) {
      const li = document.createElement("li");
      li.innerHTML = `${usIcon(t.r, 16)}<span class="meta">${label(t)}<small>${sub(t)}・${t.r > 0 ? "砂糖" : "電気"}</small></span><button class="del" title="消す">${icon("trash-2", 16)}</button>`;
      li.querySelector(".del").onclick = () => { state.trainings = state.trainings.filter((x) => x.id !== t.id); saveState(); rebuild(); renderAll(); };
      ulT.appendChild(li);
    }
    const ulX = $("#history-test");
    ulX.innerHTML = state.tests.length ? "" : `<li class="muted">まだありません。</li>`;
    for (const x of [...state.tests].reverse()) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="mark">${icon(x.ok ? "check" : "x", 16)}</span><span class="meta">${label(x)} <span class="${x.ok ? "ok" : "ng"}">${x.ok ? "合っていた" : "違った"}</span>
        <small>${sub(x)}・ハエの答え「${word(x.decision)}」${x.trained ? "" : "・しつけていないワイン"}</small></span>`;
      ulX.appendChild(li);
    }
  }

  function drawDA() {
    const c = $("#c-da"), dpr = window.devicePixelRatio || 1, w = c.clientWidth || 360, h = 150;
    c.width = w * dpr; c.height = h * dpr; c.style.height = h + "px";
    const ctx = c.getContext("2d"); ctx.scale(dpr, dpr); ctx.clearRect(0, 0, w, h);
    const hs = brain.history.map((x, i) => ({ ...x, i }));
    if (!hs.length) { ctx.fillStyle = "#7a6a6f"; ctx.font = "12px sans-serif"; ctx.fillText("まだデータがありません", 8, 20); }
    const mx = Math.max(16, ...hs.map((x) => x.surprise)), step = w / Math.max(1, hs.length);
    for (const x of hs) {
      const bh = (x.surprise / mx) * (h - 16);
      ctx.fillStyle = x.r > 0 ? "#2fae4f" : "#d63a83";
      ctx.fillRect(x.i * step + 1, h - bh, Math.max(3, step - 2), bh);
    }
    const pos = hs.filter((x) => x.r > 0).map((x) => x.surprise);
    const avg = (a) => a.reduce((s, x) => s + x, 0) / (a.length || 1);
    $("#x-stats").textContent = `いまの設定：配線＝${state.random ? "ランダム" : "本物（雄CNS）"}、グルタミン酸＝${state.gluExcites ? "興奮" : "抑制"}` +
      (pos.length >= 4 ? `　｜　ごほうびのドーパミン：最初3回の平均 ${avg(pos.slice(0, 3)).toFixed(1)} → 直近3回 ${avg(pos.slice(-3)).toFixed(1)}` : "");
  }
  $("#x-glu").checked = state.gluExcites;
  $("#x-random").checked = state.random;
  $("#x-glu").onchange = (e) => { state.gluExcites = e.target.checked; saveState(); rebuild(); renderAll(); };
  $("#x-random").onchange = (e) => { state.random = e.target.checked; saveState(); rebuild(); renderAll(); };
  $("#x-reset").onclick = () => { state.trainings = []; state.tests = []; saveState(); rebuild(); renderAll(); };
  $("#x-reset").textContent = "しつけとテストの記録をすべて消す";
  $("#x-source").innerHTML = `配線：${DATA.source.connectome}<br>受容体の応答：${DATA.source.odor}<br>
    糸球体 ${DATA.glomeruli.length} → 投射ニューロン ${DATA.n_pn} → ケニオン細胞 ${DATA.n_kc} → MBON ${DATA.mbon_types.length}タイプ、
    ドーパミン細胞 ${DATA.dan_types.length}タイプ、側角 ${DATA.lh_types.length}タイプ`;

  function renderAll() { renderLevel(); renderHistory(); renderShelfMarks(); drawDA(); }
  rebuild(); renderShelf(); setMode(state.mode); renderAll();
  if (window.SCENE3D) window.startViewer();
  if (window.FLY3D) window.startFly();
})();
