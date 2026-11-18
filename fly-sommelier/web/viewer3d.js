// viewer3d.js — 本物のニューロンの形でハエの嗅覚回路を3Dで描き、発火を光らせる
(function () {
  const COLORS = {
    base: { pn: [0.30, 0.18, 0.38], kc: [0.22, 0.17, 0.19], mbon: [0.34, 0.20, 0.20], dan: [0.18, 0.24, 0.32], apl: [0.16, 0.16, 0.16] },
    pn: [0.85, 0.55, 1.0],
    kc: [1.0, 0.83, 0.30],
    approach: [1.0, 0.42, 0.35],
    avoid: [0.35, 0.66, 1.0],
    pam: [0.45, 1.0, 0.55],
    ppl1: [1.0, 0.31, 0.64],
  };

  function decode(b64, Type) {
    const bin = atob(b64), buf = new ArrayBuffer(bin.length), u8 = new Uint8Array(buf);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return new Type(buf);
  }

  class Viewer3D {
    constructor(container, scene3d, data) {
      this.data = data;
      const w = container.clientWidth, h = container.clientHeight;
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true });
      this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
      this.renderer.setSize(w, h);
      this.renderer.setClearColor(0x0b0608);
      container.appendChild(this.renderer.domElement);

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(35, w / h, 10, 200000);
      this.camera.position.set(0, 300, -9000 * Math.max(1, 1.1 / (w / h)));
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.autoRotate = true;
      this.controls.autoRotateSpeed = 0.6;
      this.controls.addEventListener("start", () => (this.controls.autoRotate = false));

      this.scene.add(new THREE.AmbientLight(0xffffff, 0.7));
      const dl = new THREE.DirectionalLight(0xffffff, 0.6); dl.position.set(0, -1, -1); this.scene.add(dl);

      // 雄CNSの座標（y が腹側向き）を、背側が上になるように反転
      this.root = new THREE.Group();
      this.root.scale.set(1, -1, 1);
      this.scene.add(this.root);

      // ---- 脳の領域
      this.meshes = {};
      for (const [name, m] of Object.entries(scene3d.meshes)) {
        const pos = decode(m.pos, Int16Array), idx = decode(m.idx, Uint32Array);
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.BufferAttribute(Float32Array.from(pos), 3));
        g.setIndex(new THREE.BufferAttribute(idx, 1));
        g.computeVertexNormals();
        const shell = name === "脳の輪郭";
        const mat = new THREE.MeshLambertMaterial({
          color: m.color, transparent: true, opacity: shell ? 0.06 : 0.12,
          depthWrite: false, side: THREE.DoubleSide, emissive: 0x000000,
        });
        const mesh = new THREE.Mesh(g, mat);
        mesh.renderOrder = shell ? 0 : 1;
        this.root.add(mesh);
        this.meshes[name] = mesh;
      }

      // ---- ニューロン（線分）
      const segs = decode(scene3d.segs, Int16Array);
      const nVert = segs.length / 3;
      const lg = new THREE.BufferGeometry();
      this.segPos = Float32Array.from(segs);
      lg.setAttribute("position", new THREE.BufferAttribute(this.segPos, 3));
      this.colors = new Float32Array(nVert * 3);
      lg.setAttribute("color", new THREE.BufferAttribute(this.colors, 3));
      this.lines = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.85, depthWrite: false,
      }));
      this.lines.renderOrder = 2;
      this.root.add(this.lines);

      // 種類と番号 → 線分の範囲
      this.ranges = { pn: {}, kc: {}, mbon: {}, dan: {}, apl: {} };
      // fly-core の3Dデータはニューロンを bodyId で持っているので、このアプリでの番号に対応させる
      const toIdx = { pn: new Map(), kc: new Map(), mbon: new Map(), dan: new Map(), apl: new Map() };
      data.pn_body.forEach((b, i) => toIdx.pn.set(b, i));
      data.kc_body.forEach((b, i) => toIdx.kc.set(b, i));
      data.mbon_types.forEach((m, i) => data.mbon_body[m].forEach((b) => toIdx.mbon.set(b, i)));
      data.dan_types.forEach((d, i) => data.dan_body[d].forEach((b) => toIdx.dan.set(b, i)));
      (data.apl_body || []).forEach((b) => toIdx.apl.set(b, 0));
      for (const [kind, body, start, count] of scene3d.neurons) {
        const idx = toIdx[kind].has(body) ? toIdx[kind].get(body) : "other";   // 対応しないものは暗いまま描く
        (this.ranges[kind][idx] = this.ranges[kind][idx] || []).push([start, count]);
      }
      this.dim();

      new ResizeObserver(() => this.resize(container)).observe(container);
      this.tweens = [];
      this.buildParticles();
      this.label = document.createElement("div");
      this.label.className = "brain-label hidden";
      container.appendChild(this.label);
      this.container = container;
      let last = performance.now();
      const loop = (now) => {
        const dt = Math.min(0.05, ((now || last) - last) / 1000); last = now || last;
        this.tweens = this.tweens.filter((f) => !f(dt));
        this.controls.update(); this.renderer.render(this.scene, this.camera);
        this.placeLabel();
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    }

    resize(container) {
      const w = container.clientWidth, h = container.clientHeight;
      this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h);
    }

    paint(kind, idx, rgb, k = 1) {
      const r = this.ranges[kind][idx]; if (!r) return;
      for (const [start, count] of r) {
        for (let v = start * 2; v < (start + count) * 2; v++) {
          this.colors[v * 3] = rgb[0] * k; this.colors[v * 3 + 1] = rgb[1] * k; this.colors[v * 3 + 2] = rgb[2] * k;
        }
      }
    }
    commit() { this.lines.geometry.attributes.color.needsUpdate = true; }

    dim() {
      const rest = { kc: 0.45, pn: 0.6, mbon: 0.7, dan: 0.7, apl: 0.5 }; // KC は数が多く重なるので暗めに
      for (const kind of Object.keys(this.ranges)) for (const idx of Object.keys(this.ranges[kind])) this.paint(kind, idx, COLORS.base[kind], rest[kind]);
      for (const [name, m] of Object.entries(this.meshes)) {
        m.material.emissive.setRGB(0, 0, 0); m.material.opacity = name === "脳の輪郭" ? 0.06 : 0.12;
      }
      this.commit();
    }

    glowMesh(name, rgb, amount) {
      const m = this.meshes[name]; if (!m) return;
      m.material.emissive.setRGB(rgb[0] * amount, rgb[1] * amount, rgb[2] * amount);
      m.material.opacity = 0.12 + 0.25 * amount;
    }

    showPN(pn) {
      const mx = Math.max(1e-9, ...pn);
      pn.forEach((a, p) => { const k = a / mx; if (k > 0.05) this.paint("pn", p, COLORS.pn, 0.2 + 0.9 * k); });
      this.glowMesh("触角葉", [0.6, 0.3, 0.8], 0.6);
      this.commit();
    }
    showKC(active, innate) {
      for (const k of active) this.paint("kc", k, COLORS.kc, 1.0);
      this.glowMesh("萼", [0.2, 0.8, 0.4], 0.5);
      this.glowMesh("側角", innate >= 0 ? COLORS.approach : COLORS.avoid, 0.25 + 0.75 * Math.abs(innate));
      this.commit();
    }
    showMBON(mbon, sign) {
      mbon.forEach((a, m) => {
        const c = sign[m] > 0 ? COLORS.approach : COLORS.avoid;
        this.paint("mbon", m, c, Math.max(0.15, Math.min(2, 0.2 + 0.9 * a)));
      });
      this.glowMesh("キノコ体の葉", [0.8, 0.25, 0.2], 0.5);
      this.commit();
    }
    showDopamine(dan, isPam) {
      dan.forEach((a, i) => { if (a > 0.02) this.paint("dan", i, isPam[i] ? COLORS.pam : COLORS.ppl1, 0.3 + 1.6 * Math.min(1, a)); });
      this.commit();
    }
  }

  // ---- 学習の見える化
  Object.assign(Viewer3D.prototype, {
    // ある種類のニューロンの「本体（いちばん遠い点）」と「枝の重心」
    anchors(kind, idx) {
      const r = this.ranges[kind][idx]; if (!r) return null;
      const P = this.segPos; let sx = 0, sy = 0, sz = 0, n = 0;
      for (const [st, c] of r) for (let v = st * 2; v < (st + c) * 2; v++) { sx += P[v * 3]; sy += P[v * 3 + 1]; sz += P[v * 3 + 2]; n++; }
      const cen = new THREE.Vector3(sx / n, sy / n, sz / n);
      let far = cen.clone(), fd = 0;
      for (const [st, c] of r) for (let v = st * 2; v < (st + c) * 2; v += 6) {
        const d = (P[v * 3] - cen.x) ** 2 + (P[v * 3 + 1] - cen.y) ** 2 + (P[v * 3 + 2] - cen.z) ** 2;
        if (d > fd) { fd = d; far = new THREE.Vector3(P[v * 3], P[v * 3 + 1], P[v * 3 + 2]); }
      }
      return { cen, far };
    },

    buildParticles() {
      const N = 900;
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(N * 3), 3));
      g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(N * 3), 3));
      this.pts = new THREE.Points(g, new THREE.PointsMaterial({ size: 150, vertexColors: true, transparent: true, opacity: 0.95,
        blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true }));
      this.pts.renderOrder = 3; this.pts.visible = false;
      this.root.add(this.pts);
      this.N = N;
    },

    // ドーパミンの粒：ドーパミン細胞の本体から、キノコ体の区画（枝の重心）へ流れる
    flowDopamine(dan, isPam, ms = 2200) {
      const paths = [];
      dan.forEach((a, i) => {
        if (a < 0.05) return;
        const an = this.anchors("dan", i); if (!an) return;
        const n = Math.round(10 + 40 * Math.min(1, a));
        for (let k = 0; k < n; k++) paths.push({ a: an.far, b: an.cen, c: isPam[i] ? [0.45, 1, 0.55] : [1, 0.31, 0.64], d: Math.random() * 0.45, w: (Math.random() - .5) * 600 });
      });
      const use = paths.slice(0, this.N);
      const pos = this.pts.geometry.attributes.position, col = this.pts.geometry.attributes.color;
      for (let i = 0; i < this.N; i++) col.setXYZ(i, 0, 0, 0);
      use.forEach((p, i) => col.setXYZ(i, ...p.c));
      col.needsUpdate = true;
      this.pts.visible = true;
      let t = 0;
      const tmp = new THREE.Vector3();
      this.tweens.push((dt) => {
        t += dt * 1000 / ms;
        use.forEach((p, i) => {
          const u = Math.min(1, Math.max(0, (t - p.d) / 0.55));
          const e = u * u * (3 - 2 * u);
          tmp.copy(p.a).lerp(p.b, e);
          tmp.y += Math.sin(e * Math.PI) * p.w;   // 少し弧を描いて
          pos.setXYZ(i, tmp.x, tmp.y, tmp.z);
          const fade = u >= 1 ? Math.max(0, 1 - (t - p.d - 0.55) * 4) : 1;
          col.setXYZ(i, p.c[0] * fade, p.c[1] * fade, p.c[2] * fade);
        });
        pos.needsUpdate = true; col.needsUpdate = true;
        if (t > 1.3) { this.pts.visible = false; return true; }
        return false;
      });
    },

    // 結合が弱まる：さっき発火した KC が暗くなり、ドーパミンが届いた区画の出力が変わる
    weaken(active, mbonBefore, mbonAfter, sign, ms = 1800) {
      let t = 0;
      this.tweens.push((dt) => {
        t = Math.min(1, t + dt * 1000 / ms);
        for (const k of active) this.paint("kc", k, [1.0 - 0.6 * t, 0.83 - 0.6 * t, 0.30 - 0.15 * t], 1.0);
        mbonAfter.forEach((a, m) => {
          const v = mbonBefore[m] + (a - mbonBefore[m]) * t;
          const c = sign[m] > 0 ? [1.0, 0.42, 0.35] : [0.35, 0.66, 1.0];
          this.paint("mbon", m, c, Math.max(0.15, Math.min(2, 0.2 + 0.9 * v)));
        });
        this.commit();
        return t >= 1;
      });
    },

    // 3D の点に吹き出しを付ける
    showLabel(point, html) { this.labelPoint = point; this.label.innerHTML = html; this.label.classList.remove("hidden"); },
    hideLabel() { this.labelPoint = null; this.label.classList.add("hidden"); },
    placeLabel() {
      if (!this.labelPoint) return;
      const v = this.labelPoint.clone(); this.root.localToWorld(v); v.project(this.camera);
      const w = this.container.clientWidth, h = this.container.clientHeight;
      this.label.style.transform = `translate(${(v.x * 0.5 + 0.5) * w}px, ${(-v.y * 0.5 + 0.5) * h}px)`;
    },
    // 指定した MBON たちの枝の重心
    mbonCenter(list) {
      const c = new THREE.Vector3(); let n = 0;
      for (const m of list) { const a = this.anchors("mbon", m); if (a) { c.add(a.cen); n++; } }
      return n ? c.divideScalar(n) : null;
    },
  });

  window.Viewer3D = Viewer3D;
  window.VIEWER_COLORS = COLORS;
})();
