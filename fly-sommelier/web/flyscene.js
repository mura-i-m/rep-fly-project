// flyscene.js — NeuroMechFly の体で、ワインの雫に近づいて嗅ぎ、飲むか逃げるかを演じる
(function () {
  const WALK_SLOWMO = 0.35;   // 歩行はスロー再生（実際は 1秒に約10歩）
  const ACT_SLOWMO = 0.6;     // そのほかの動き
  const START_DIST = 9;       // 雫からどれだけ離れて歩き始めるか（mm）
  const STOP_DIST = 1.9;      // 胸部の中心が雫からこの距離で止まる（頭の先が雫に届く）

  function decode(b64, Type) {
    const bin = atob(b64), buf = new ArrayBuffer(bin.length), u8 = new Uint8Array(buf);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return new Type(buf);
  }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  class FlyScene {
    constructor(container, fly) {
      this.fly = fly;
      const w = container.clientWidth, h = container.clientHeight;
      const r = (this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }));
      r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
      r.setSize(w, h);
      r.shadowMap.enabled = true;
      r.shadowMap.type = THREE.PCFSoftShadowMap;
      container.appendChild(r.domElement);

      const scene = (this.scene = new THREE.Scene());
      scene.background = new THREE.Color(0xd9cbb9);
      scene.fog = new THREE.Fog(0xd9cbb9, 30, 120);
      this.camera = new THREE.PerspectiveCamera(32, w / h, 0.1, 500);
      this.controls = new THREE.OrbitControls(this.camera, r.domElement);
      this.controls.enableDamping = true;
      this.controls.maxPolarAngle = Math.PI * 0.49;
      this.controls.minDistance = 1.5; this.controls.maxDistance = 60;
      this.controls.addEventListener("start", () => (this.camGoal = null)); // 触ったら自動カメラは止める

      scene.add(new THREE.HemisphereLight(0xfff6ec, 0xb89f86, 0.62));
      const sun = new THREE.DirectionalLight(0xffffff, 0.9);
      sun.position.set(-12, 30, 14); sun.castShadow = true;
      sun.shadow.mapSize.set(2048, 2048);
      Object.assign(sun.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15, near: 1, far: 80 });
      sun.shadow.radius = 4;
      scene.add(sun);
      this.sun = sun;

      // テーブル
      const table = new THREE.Mesh(new THREE.CircleGeometry(160, 64),
        new THREE.MeshStandardMaterial({ color: 0xbfa98f, roughness: 0.85 }));
      table.rotation.x = -Math.PI / 2; table.receiveShadow = true;
      scene.add(table);

      // ワインの雫
      this.dropMat = new THREE.MeshPhysicalMaterial({ color: 0x5c0418, roughness: 0.06, clearcoat: 1, clearcoatRoughness: 0.05, transparent: true, opacity: 0.95 });
      const drop = new THREE.Mesh(new THREE.SphereGeometry(1.25, 48, 24), this.dropMat);
      drop.scale.set(0.001, 0.001, 0.001); drop.position.set(0, 0.12, 0);  // ボトルを選ぶまでは空 drop.castShadow = true; drop.receiveShadow = true;
      scene.add(drop);
      this.drop = drop;

      this.tweens = [];
      this.buildSugar();
      this.buildGrid();

      // 奥のワイングラス（大きさは本物どおり。ハエから見ると巨大）
      const prof = [[0, 0], [32, 0], [33, 1.2], [4, 3], [3, 8], [2.5, 60], [6, 66], [28, 80], [38, 105], [40, 130], [38, 165], [37.5, 165.2], [39.3, 130], [37.3, 105], [27.5, 81], [0.5, 70]]
        .map(([x, y]) => new THREE.Vector2(x, y));
      const glass = new THREE.Mesh(new THREE.LatheGeometry(prof, 64), new THREE.MeshPhysicalMaterial({
        color: 0xffffff, roughness: 0.05, transmission: 0.9, transparent: true, opacity: 0.25, side: THREE.DoubleSide }));
      glass.position.set(-30, 0, -60); scene.add(glass);
      const wine = new THREE.Mesh(new THREE.CylinderGeometry(34, 26, 30, 64), new THREE.MeshStandardMaterial({ color: 0x5a0a1e, roughness: 0.2, transparent: true, opacity: 0.85 }));
      wine.position.set(-30, 96, -60); scene.add(wine);

      // ハエ：MuJoCo の座標（z が上）を three.js（y が上）に合わせる
      this.root = new THREE.Group();              // テーブル上の位置と向き
      const zup = new THREE.Group(); zup.rotation.x = -Math.PI / 2;
      this.root.add(zup); scene.add(this.root);
      this.segs = fly.bodies.map(() => { const o = new THREE.Object3D(); zup.add(o); return o; });
      for (const p of fly.parts) {
        const pos = decode(p.pos, Int16Array), idx = decode(p.idx, Uint16Array);
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.BufferAttribute(Float32Array.from(pos, (v) => v / 5000), 3));
        g.setIndex(new THREE.BufferAttribute(idx, 1));
        g.computeVertexNormals();
        const mat = new THREE.MeshStandardMaterial({ color: p.color, roughness: p.alpha < 1 ? 0.2 : 0.55, metalness: 0.05,
          transparent: p.alpha < 1, opacity: p.alpha, side: p.alpha < 1 ? THREE.DoubleSide : THREE.FrontSide });
        const mesh = new THREE.Mesh(g, mat);
        mesh.castShadow = true;
        this.segs[p.body].add(mesh);
      }
      this.clips = {};
      for (const [name, c] of Object.entries(fly.clips)) {
        this.clips[name] = { ...c, frames: decode(c.data, Float32Array) };
      }

      this.B = fly.bodies.length;
      this.heading = 0;   // ハエが向いている方向（ラジアン、+x が 0）
      this.cur = { name: "idle", t: 0, rate: ACT_SLOWMO };
      this.motion = null; // 体全体の移動 { vx, vz, vy, turn, until }
      this.placeAt(-START_DIST, 0, 0);
      this.resetCamera();
      this.applyClip();

      new ResizeObserver(() => this.resize(container)).observe(container);
      // 電気ショックの瞬間に画面ごと青白く光らせる
      this.flashEl = document.createElement("div");
      this.flashEl.style.cssText = "position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .08s;background:radial-gradient(ellipse at 42% 50%,rgba(170,220,255,.75),rgba(110,170,255,.3) 55%,rgba(80,140,255,.08))";
      container.appendChild(this.flashEl);
      this.last = performance.now();
      const loop = (now) => {
        const dt = Math.min(0.05, (now - this.last) / 1000); this.last = now;
        this.tick(dt);
        this.controls.update();
        r.render(scene, this.camera);
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    }

    resize(container) {
      const w = container.clientWidth, h = container.clientHeight;
      this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h);
    }

    // 雫と、歩き始めの位置の両方が入るように
    resetCamera() {
      const t = new THREE.Vector3(-4.4, 0.6, 1.2);
      this.camera.position.set(-3.4, 9.5, 21.0).sub(t).multiplyScalar(this.narrow()).add(t);
      this.controls.target.copy(t);
    }

    placeAt(x, z, heading) {
      this.root.position.set(x, 0, z); this.root.rotation.set(0, heading, 0); this.heading = heading;
      this.root.visible = true;
    }

    // いまのクリップの時刻 t の姿勢を、前後のフレームから補間して当てる
    applyClip() {
      const c = this.clips[this.cur.name], B = this.B, F = c.frames;
      let f = this.cur.t * c.fps;
      if (c.loop) f = f % c.n; else f = Math.min(f, c.n - 1);
      const i0 = Math.floor(f), i1 = c.loop ? (i0 + 1) % c.n : Math.min(i0 + 1, c.n - 1), a = f - i0;
      const qa = new THREE.Quaternion(), qb = new THREE.Quaternion();
      for (let b = 0; b < B; b++) {
        const o0 = (i0 * B + b) * 7, o1 = (i1 * B + b) * 7, s = this.segs[b];
        s.position.set(F[o0] + (F[o1] - F[o0]) * a, F[o0 + 1] + (F[o1 + 1] - F[o0 + 1]) * a, F[o0 + 2] + (F[o1 + 2] - F[o0 + 2]) * a);
        qa.set(F[o0 + 4], F[o0 + 5], F[o0 + 6], F[o0 + 3]); qb.set(F[o1 + 4], F[o1 + 5], F[o1 + 6], F[o1 + 3]);
        s.quaternion.copy(qa).slerp(qb, a);
      }
    }

    // カメラをなめらかに寄せる
    cameraTo(pos, target) {
      const t = new THREE.Vector3(...target), p = new THREE.Vector3(...pos);
      p.sub(t).multiplyScalar(this.narrow()).add(t);   // 縦長の画面では少し引く
      this.camGoal = { pos: p, target: t };
    }
    narrow() { return Math.max(1, 1.55 / this.camera.aspect); }

    tick(dt) {
      if (this.camGoal) {
        this.camera.position.lerp(this.camGoal.pos, 0.04); this.controls.target.lerp(this.camGoal.target, 0.04);
        if (this.camera.position.distanceTo(this.camGoal.pos) < 0.02) this.camGoal = null;
      }
      this.tweens = this.tweens.filter((f) => !f(dt));   // true を返したら終わり
      if (this.dropT !== undefined && this.dropT < 1) {   // 雫がぽたっと広がる
        this.dropT = Math.min(1, this.dropT + dt * 2.2);
        const e = 1 - Math.pow(1 - this.dropT, 3);
        this.drop.scale.set(e, 0.3 * (0.4 + 0.6 * e) * (1 + 0.4 * Math.sin(this.dropT * 9) * (1 - this.dropT)), e);
      }
      this.cur.t += dt * this.cur.rate;
      this.applyClip();
      const m = this.motion;
      if (m) {
        if (m.turn) { this.heading += m.turn * dt; this.root.rotation.y = this.heading; }
        const sp = m.speed * dt;
        // three.js では、ハエの前方（MuJoCo の +x）は回転 heading で x→(cos, -sin)
        this.root.position.x += Math.cos(this.heading) * sp;
        this.root.position.z += -Math.sin(this.heading) * sp;
        this.root.position.y += (m.climb || 0) * dt;
        if (m.follow && this.root.position.y > 1) {  // 飛び立ったら少し目で追う
          this.controls.target.lerp(new THREE.Vector3(this.root.position.x, this.root.position.y * 0.5, this.root.position.z), 0.03);
        }
      }
    }

    play(name, rate) { this.cur = { name, t: 0, rate: rate || (name === "walk" ? WALK_SLOWMO : ACT_SLOWMO) }; }
    clipSeconds(name) { const c = this.clips[name]; return (c.n / c.fps) / (name === "walk" ? WALK_SLOWMO : ACT_SLOWMO); }

    // ---- ふるまい
    async approach() {
      this.placeAt(-START_DIST, 0.4 * (Math.random() - 0.5), 0);
      this.play("walk");
      const speed = this.fly.walk_speed_mm_s * WALK_SLOWMO;
      this.motion = { speed, follow: true };
      const dist = START_DIST - STOP_DIST;
      await sleep((dist / speed) * 1000);
      this.motion = null;
      this.play("idle");
    }
    // 頭にぐっと寄る（このあと脳の中へ）
    diveToHead() { const x = this.root.position.x; this.cameraTo([x + 1.25, 1.05, 0.95], [x + 0.75, 0.75, 0]); }
    // 行動が見えるところまで引く
    actionView() { const x = this.root.position.x; this.cameraTo([x + 1.6, 3.2, 7.4], [x + 1.0, 0.5, 0.3]); }

    // ボトルを選んだら一滴たらす（色はワインの色）
    pour(color) {
      const c = { 白: 0xb9a35a, 赤: 0x5c0418, 泡: 0xc2ad66 }[color] || 0x5c0418;
      this.dropMat.color.setHex(c);
      this.dropMat.opacity = color === "赤" ? 0.95 : 0.55;
      this.dropT = 0;
    }
    async sniff() { this.play("sniff"); await sleep(this.clipSeconds("sniff") * 1000); this.play("idle"); }
    async tapAndDrink() {
      this.play("tap"); await sleep(this.clipSeconds("tap") * 1000);
      this.play("drink"); await sleep(this.clipSeconds("drink") * 1000);
      this.play("idle");
    }
    async flyAway() {
      this.play("takeoff");
      this.cameraTo([-2, 8, 16], [-3, 2, 0]);
      this.motion = { speed: -2, climb: 7, turn: 2.2, follow: true };
      await sleep(2600);
      this.motion = null; this.root.visible = false;
    }
    // ---- 学習：匂いと一緒に、ごほうび（砂糖）か罰（電気ショック）を与える
    // 本物のハエの学習実験と同じ組み合わせ（匂い＋砂糖、匂い＋床からの電気ショック）
    buildSugar() {
      const g = (this.sugar = new THREE.Group());
      const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.35, emissive: 0x332a10, transparent: true });
      this.sugarMat = mat;
      this.grains = [];
      for (let i = 0; i < 26; i++) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, 0.15), mat);
        m.castShadow = true; g.add(m); this.grains.push(m);
      }
      const sp = new THREE.BufferGeometry();
      sp.setAttribute("position", new THREE.BufferAttribute(new Float32Array(40 * 3), 3));
      this.sparkle = new THREE.Points(sp, new THREE.PointsMaterial({ color: 0xfff3b0, size: 0.09, transparent: true, opacity: 0, depthWrite: false }));
      g.add(this.sparkle);
      g.visible = false; this.scene.add(g);
    }
    buildGrid() {
      // 床の電極（銅の細い線を並べた格子）
      this.gridMat = new THREE.MeshStandardMaterial({ color: 0xb87333, metalness: 0.7, roughness: 0.3, transparent: true, opacity: 0, emissive: 0x000000 });
      this.grid = new THREE.Group();
      const bar = new THREE.BoxGeometry(8, 0.025, 0.05);
      for (let i = -14; i <= 14; i++) { const m = new THREE.Mesh(bar, this.gridMat); m.position.set(0, 0.013, i * 0.28); m.receiveShadow = true; this.grid.add(m); }
      this.grid.visible = false; this.scene.add(this.grid);
      // 火花：細い芯と、ぼんやり光る外側の2重の管
      this.arcMat = new THREE.MeshBasicMaterial({ color: 0x2fa8ff, transparent: true, opacity: 0 });
      this.arcGlow = new THREE.MeshBasicMaterial({ color: 0x8fd3ff, transparent: true, opacity: 0, depthWrite: false });
      this.arcs = new THREE.Group(); this.arcs.visible = false; this.scene.add(this.arcs);
      this.flash = new THREE.PointLight(0x9fd8ff, 0, 8); this.scene.add(this.flash);
    }

    // ハエを雫のそばに戻す（逃げたあとでも、同じ匂いのそばで学習させる）
    backToDrop() {
      this.motion = null;
      this.placeAt(-STOP_DIST, 0, 0); this.play("idle"); this.actionView();
    }

    async reward() {
      // 頭の前、雫の手前（カメラ側）に小さな山になるように
      const x0 = this.root.position.x + 0.75, z0 = 0.5;
      this.sugar.visible = true; this.sugarMat.opacity = 1;
      const fall = this.grains.map((m, i) => {
        const a = Math.random() * Math.PI * 2, r = Math.sqrt(Math.random()) * 0.32;
        m.position.set(x0 + Math.cos(a) * r, 2.5 + Math.random() * 1.5, z0 + Math.sin(a) * r);
        m.rotation.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
        m.scale.setScalar(0.7 + Math.random() * 0.6);
        return { m, vy: 0, floor: 0.07 + (0.32 - r) * 0.5 };   // 真ん中ほど高く積もる
      });
      this.tweens.push((dt) => {           // ぱらぱらと落ちてくる
        let done = true;
        for (const f of fall) {
          if (f.m.position.y > f.floor) { f.vy -= 30 * dt; f.m.position.y = Math.max(f.floor, f.m.position.y + f.vy * dt); done = false; }
        }
        return done;
      });
      let tt = 0;
      const pos = this.sparkle.geometry.attributes.position;
      this.tweens.push((dt) => {           // きらきら
        tt += dt;
        for (let i = 0; i < 40; i++) pos.setXYZ(i, x0 + (Math.random() - .5) * .8, Math.random() * .55, z0 + (Math.random() - .5) * .8);
        pos.needsUpdate = true;
        this.sparkle.material.opacity = Math.max(0, Math.sin(Math.min(tt, 3.2) / 3.2 * Math.PI)) * 0.9;
        return tt > 3.2;
      });
      await sleep(900);
      this.play("drink");                  // 口吻を伸ばして舐める
      const dur = this.clipSeconds("drink");
      let et = 0;
      this.tweens.push((dt) => {           // 舐めるにつれて減っていく
        et += dt; const k = Math.max(0, 1 - et / dur);
        this.grains.forEach((m, i) => m.scale.setScalar(Math.max(0.001, k * (0.7 + (i % 5) * 0.12))));
        return et >= dur;
      });
      await sleep(dur * 1000);
      this.sugar.visible = false; this.play("idle");
    }

    async shock() {
      const x = this.root.position.x;
      this.grid.position.set(x + 0.5, 0, 0); this.grid.visible = true;
      let t = 0;
      this.tweens.push((dt) => { t += dt; this.gridMat.opacity = Math.min(0.85, t * 3); return t > 0.35; });
      await sleep(500);
      for (let k = 0; k < 3; k++) {        // バチッ×3
        this.arcs.children.forEach((m) => m.geometry.dispose()); this.arcs.clear();
        for (let a = 0; a < 10; a++) {     // 床から脚へ、ギザギザの火花
          let px = x + (Math.random() - 0.35) * 2.4, pz = (Math.random() - 0.5) * 1.8, py = 0.02;
          const pts = [new THREE.Vector3(px, py, pz)];
          for (let j = 0; j < 5; j++) {
            px += (x - px) * 0.22 + (Math.random() - .5) * .22; py += 0.1; pz = pz * 0.78 + (Math.random() - .5) * .22;
            pts.push(new THREE.Vector3(px, py, pz));
          }
          const curve = new THREE.CatmullRomCurve3(pts, false, "chordal", 0.1);
          this.arcs.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 16, 0.02, 5), this.arcMat));
          this.arcs.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 16, 0.06, 6), this.arcGlow));
        }
        this.arcs.visible = true; this.arcMat.opacity = 1; this.arcGlow.opacity = 0.35;
        this.gridMat.emissive.setHex(0x9fd8ff); this.flash.position.set(x, 0.6, 0); this.flash.intensity = 3;
        this.flashEl.style.opacity = 1;
        // ビクッ：跳ねて、脚をばたつかせる
        this.play("takeoff", 1.4);
        const jitter = (Math.random() - .5) * 0.5;
        let jt = 0;
        this.tweens.push((dt) => {
          jt += dt; const h = Math.max(0, Math.sin(Math.min(1, jt / 0.25) * Math.PI)) * 0.35;
          this.root.position.y = h; this.root.rotation.y = this.heading + jitter * (1 - jt / 0.25);
          return jt >= 0.25;
        });
        await sleep(220);
        this.arcMat.opacity = 0; this.arcGlow.opacity = 0; this.flash.intensity = 0; this.gridMat.emissive.setHex(0x000000); this.flashEl.style.opacity = 0;
        await sleep(260);
        this.root.position.y = 0; this.root.rotation.y = this.heading; this.play("idle");
        await sleep(380);
      }
      this.arcs.visible = false;
      t = 0;
      this.tweens.push((dt) => { t += dt; this.gridMat.opacity = Math.max(0, 0.85 - t * 2); if (t > 0.45) this.grid.visible = false; return t > 0.45; });
      await sleep(500);
    }

    // 次のワインに備えて、スタート地点に戻ってくる
    comeBack() { this.placeAt(-START_DIST, 0, 0); this.play("idle"); this.overview(); }
    overview() { this.cameraTo([-3.4, 9.5, 21.0], [-4.4, 0.6, 1.2]); }
    async walkAway() {
      this.overview();
      this.play("walk");
      this.motion = { speed: this.fly.walk_speed_mm_s * WALK_SLOWMO * 0.6, turn: 2.6, follow: true };
      await sleep(1200);
      this.motion.turn = 0;
      await sleep(1600);
      this.motion = null; this.play("idle");
    }
  }

  window.FlyScene = FlyScene;
})();
