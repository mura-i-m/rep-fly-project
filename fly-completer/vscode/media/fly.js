// fly.js — サイドパネルのハエ（Webview）
(function () {
  const app = document.getElementById("app");
  app.innerHTML = `
  <div class="stage">
    <svg class="fly" viewBox="0 0 120 150" aria-label="ハエ">
      <g transform="rotate(180 60 75)">
      <g class="legs">
        <path class="leg" d="M50 78 Q34 76 24 86"/><path class="leg" d="M70 78 Q86 76 96 86"/>
        <path class="leg" d="M50 88 Q36 96 30 112"/><path class="leg" d="M70 88 Q84 96 90 112"/>
        <path class="leg tap tapL" d="M53 60 Q40 50 38 30 L36 16"/>
        <path class="leg tap tapR" d="M67 60 Q80 50 82 30 L84 16"/>
      </g>
      <path class="wing wingL" d="M54 64 Q20 70 22 116 Q40 120 56 84 Z"/>
      <path class="wing wingR" d="M66 64 Q100 70 98 116 Q80 120 64 84 Z"/>
      <ellipse class="body" cx="60" cy="92" rx="11" ry="24"/>
      <ellipse class="body" cx="60" cy="64" rx="10" ry="9"/>
      <circle class="body" cx="60" cy="48" r="9"/>
      <ellipse class="eye" cx="53" cy="46" rx="4.5" ry="5.5"/>
      <ellipse class="eye" cx="67" cy="46" rx="4.5" ry="5.5"/>
      <path class="leg" d="M57 39 Q55 33 51 30 M63 39 Q65 33 69 30" style="stroke-width:1.2"/>
      </g>
    </svg>
    <div class="code" id="code"></div>
  </div>
  <div class="msg" id="msg">Python を打つと、ハエが匂いを嗅ぎにきます</div>
  <div class="odors" id="odors"></div>
  <div><div class="label">脳の発火（ケニオン細胞 3,763個 / MBON 97個）</div><canvas id="spikes" width="300" height="40"></canvas></div>
  <div><div class="label">どの区画が黙ったか（＝ハエの答えの候補）</div><div class="rank" id="rank"></div></div>
  <div class="foot" id="foot"></div>`;

  const $ = (id) => document.getElementById(id);
  const flyEl = document.querySelector(".fly");
  const taps = [document.querySelector(".tapL"), document.querySelector(".tapR")];
  const cv = $("spikes"), g = cv.getContext("2d");
  let timer = null, chars = [], vocab = [];

  const css = (v) => getComputedStyle(document.body).getPropertyValue(v).trim() || "#888";
  const show = (c) => (c === " " ? "␣" : c === "\n" ? "↵" : c);

  function drawSpikes(frames, upto) {
    g.clearRect(0, 0, cv.width, cv.height);
    if (!frames) return;
    const w = cv.width / frames.length;
    const maxK = Math.max(1, ...frames.map((f) => f[0]));
    const maxM = Math.max(1, ...frames.map((f) => f[1]));
    for (let i = 0; i < Math.min(upto, frames.length); i++) {
      const [k, m] = frames[i];
      g.fillStyle = css("--vscode-textLink-foreground");
      g.fillRect(i * w, cv.height - (k / maxK) * 24, Math.max(1, w - 1), (k / maxK) * 24);
      g.fillStyle = "#c8473b";
      g.fillRect(i * w, 0, Math.max(1, w - 1), (m / maxM) * 12);
    }
  }

  function setCode(context, suffix) {
    chars = [...context];
    $("code").innerHTML = chars.map((c, i) => {
      const fade = Math.pow(0.45, chars.length - 1 - i);
      return `<span class="ch old" style="--fade:${Math.max(0.25, fade)}">${show(c)}<i class="ripple"></i></span>`;
    }).join("") + (suffix ? `<span class="suffix">${suffix}</span>` : "");
  }

  function rank(list) {
    if (!list || !list.length) { $("rank").innerHTML = ""; return; }
    const mx = Math.max(1e-6, list[0][1]);
    $("rank").innerHTML = list.map(([w, s], i) =>
      `<span>${w}</span><div class="bar ${i ? "" : "top"}" style="width:${Math.max(2, (s / mx) * 100)}%"></div>`).join("");
  }

  function thinking(m) {
    clearInterval(timer);
    flyEl.classList.remove("happy"); flyEl.classList.add("buzz");
    setCode(m.context, "");
    $("msg").textContent = `クンクン…「${m.prefix}」の匂いを嗅いでいる`;
    $("odors").innerHTML = m.odors.map(([c, n]) => `<b>${show(c)}</b> ${n}`).join(" ・ ");
    rank([]);
    const frames = m.frames;
    const thr = frames.reduce((a, f) => a + f[0], 0) / frames.length; // 平均より強く発火したらタップ
    const step = Math.max(16, m.ms / frames.length);
    let i = 0, side = 0;
    const els = $("code").querySelectorAll(".ch");
    timer = setInterval(() => {
      if (i >= frames.length) { clearInterval(timer); return; }
      drawSpikes(frames, i + 1);
      if (frames[i][0] > thr) {
        const leg = taps[side ^= 1];
        leg.classList.add("down");
        setTimeout(() => leg.classList.remove("down"), Math.min(90, step * 0.8));
        const el = els[Math.floor(Math.random() * els.length)];
        if (el) { el.classList.remove("hit"); void el.offsetWidth; el.classList.add("hit"); }
      }
      i++;
    }, step);
  }

  function answer(m) {
    clearInterval(timer);
    flyEl.classList.remove("buzz");
    if (m.suffix) {
      flyEl.classList.add("happy");
      setCode(chars.join(""), m.suffix);
      $("msg").innerHTML = `わかった！ <b>${m.prefix}${m.suffix}</b>（Tab で確定）`;
    } else {
      $("msg").innerHTML = `…わからない（「${m.word}」の区画が反応したけど、打ちかけと合わない）`;
    }
    rank(m.ranking);
  }

  window.addEventListener("message", (e) => {
    const m = e.data;
    if (m.type === "hello") {
      vocab = m.words;
      $("foot").innerHTML = `覚えられる単語（30区画＝30語）: ${vocab.join(", ")}`;
    } else if (m.type === "thinking") thinking(m);
    else if (m.type === "answer") answer(m);
    else if (m.type === "cancel") { clearInterval(timer); flyEl.classList.remove("buzz"); }
    else if (m.type === "accepted") {
      $("msg").innerHTML = `<span class="dopa">✦ 正解！ごほうびのドーパミン ✦</span> ${m.word}`;
      flyEl.classList.add("happy");
    } else if (m.type === "learned") {
      $("msg").innerHTML = m.miss
        ? `<span class="dopa">✦</span> 「${m.word}」を覚え直した（ドーパミン ${m.miss} 回）`
        : `「${m.word}」は覚えていた`;
    }
  });
})();
