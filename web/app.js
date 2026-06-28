// VSign Detect web control panel.
// Runs the SAME MediaPipe "Victory" gesture detector in the browser (Tasks for
// Web) for two zones, with per-zone camera selection + parameters + live trigger
// indicators. The debounce/trigger logic mirrors the Python engine
// (src/trigger_agent.py) so settings here map 1:1 to config.yaml.

import {
  GestureRecognizer,
  FilesetResolver,
  DrawingUtils,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35";

const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/" +
  "gesture_recognizer/float16/1/gesture_recognizer.task";
const WASM_URL =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm";

const DEFAULTS = { minScore: 0.6, holdMs: 350, cooldownS: 3.0, releaseMs: 250 };
const PROC_FPS = 30; // cap processing rate to spare CPU

const statusEl = document.getElementById("status");
const enableBtn = document.getElementById("enableBtn");
const globalTrigger = document.getElementById("globalTrigger");
const zonesEl = document.querySelector(".zones");
const tmpl = document.getElementById("zoneTemplate");
const logEl = document.getElementById("log");
const configYamlEl = document.getElementById("configYaml");
const driveRelayEl = document.getElementById("driveRelay");
const relayStatusEl = document.getElementById("relayStatus");

let apiAvailable = false;
let visionFileset = null;
let permissionGranted = false;
let devicechangeBound = false;
const zones = [];

// ----- per-zone debounce, mirrors TriggerAgent -----
class Trigger {
  constructor(params, onFire) {
    this.p = params;
    this.onFire = onFire;
    this.victorySince = null;
    this.falseSince = null;
    this.armed = true;
    this.lastFire = -Infinity;
  }
  submit(isVictory, conf, now) {
    if (isVictory) {
      if (this.victorySince === null) this.victorySince = now;
      this.falseSince = null;
    } else {
      this.victorySince = null;
      if (this.falseSince === null) this.falseSince = now;
      if (!this.armed && now - this.falseSince >= this.p.releaseMs) this.armed = true;
    }
    const held = this.victorySince !== null && now - this.victorySince >= this.p.holdMs;
    const active = this.armed && held;
    if (active && now - this.lastFire >= this.p.cooldownS * 1000) {
      this.lastFire = now;
      this.armed = false; // require release before re-arming
      this.onFire(conf);
    }
  }
}

class Zone {
  constructor(name) {
    this.name = name;
    this.params = loadParams(name);
    this.deviceId = localStorage.getItem(`vsign.cam.${name}`) || null;
    this.stream = null;
    this.recognizer = null;
    this.lastVideoTime = -1;
    this.lastProc = 0;
    this.frames = 0;
    this.fpsT = performance.now();
    this.trigger = new Trigger(this.params, (c) => this.fire(c));
    this._buildDom();
  }

  _buildDom() {
    const node = tmpl.content.firstElementChild.cloneNode(true);
    this.el = node;
    node.querySelector(".zname").textContent = this.name;
    this.video = node.querySelector(".video");
    this.canvas = node.querySelector(".overlay");
    this.ctx = this.canvas.getContext("2d");
    this.draw = new DrawingUtils(this.ctx);
    this.badge = node.querySelector(".badge");
    this.fpsEl = node.querySelector(".fps");
    this.confBar = node.querySelector(".conf-bar");
    this.zoneTrigger = node.querySelector(".zone-trigger");
    this.camSelect = node.querySelector(".camSelect");
    this._setPlaceholder();
    this.camSelect.addEventListener("change", () => this.setCamera(this.camSelect.value));

    for (const key of Object.keys(DEFAULTS)) {
      const input = node.querySelector("." + key);
      const label = node.querySelector(".v-" + key);
      input.value = this.params[key];
      label.textContent = this.params[key];
      input.addEventListener("input", () => {
        this.params[key] = parseFloat(input.value);
        label.textContent = input.value;
        saveParams(this.name, this.params);
        renderConfig();
      });
    }
    zonesEl.appendChild(node);
  }

  _setPlaceholder() {
    this.camSelect.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "— click “Enable cameras” —";
    this.camSelect.appendChild(opt);
  }

  async ensureRecognizer() {
    if (this.recognizer || !visionFileset) return;
    this.recognizer = await GestureRecognizer.createFromOptions(visionFileset, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
      runningMode: "VIDEO",
      numHands: 1,
    });
  }

  async setCamera(deviceId) {
    if (!deviceId) return;
    this.deviceId = deviceId;
    localStorage.setItem(`vsign.cam.${this.name}`, deviceId);
    if (this.stream) this.stream.getTracks().forEach((t) => t.stop());

    const constraints = {
      video: { deviceId: { exact: deviceId }, width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    };
    try {
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      console.warn(`zone ${this.name}: exact deviceId failed (${e.name}); retrying loose`, e);
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId }, audio: false });
      } catch (e2) {
        setStatus(`Zone ${this.name}: ${e2.name} — ${e2.message}`, "err");
        return;
      }
    }

    this.video.srcObject = this.stream;
    this.video.addEventListener("loadedmetadata", () => {
      this.canvas.width = this.video.videoWidth || 640;
      this.canvas.height = this.video.videoHeight || 480;
    }, { once: true });
    await this.video.play().catch(() => {});
    await this.ensureRecognizer();
    if (!this._looping) { this._looping = true; this.loop(); }
  }

  loop() {
    requestAnimationFrame(() => this.loop());
    const v = this.video;
    if (!this.recognizer || v.readyState < 2) return;

    const now = performance.now();
    if (now - this.lastProc < 1000 / PROC_FPS) return; // throttle
    this.lastProc = now;
    if (v.currentTime === this.lastVideoTime) return;   // no new frame
    this.lastVideoTime = v.currentTime;

    let result;
    try {
      result = this.recognizer.recognizeForVideo(v, now);
    } catch { return; }

    // parse: is this a Victory above threshold?
    let isVictory = false, conf = 0;
    if (result.gestures && result.gestures.length) {
      const top = result.gestures[0][0];
      if (top && top.categoryName === "Victory") {
        conf = top.score;
        if (conf >= this.params.minScore) isVictory = true;
      }
    }

    this._render(result, isVictory, conf);
    this.trigger.submit(isVictory, conf, now);

    // fps
    this.frames++;
    if (now - this.fpsT >= 1000) {
      this.fpsEl.textContent = `${this.frames} fps`;
      this.frames = 0; this.fpsT = now;
    }
  }

  _render(result, isVictory, conf) {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    if (result.landmarks) {
      for (const lm of result.landmarks) {
        this.draw.drawConnectors(lm, GestureRecognizer.HAND_CONNECTIONS,
          { color: isVictory ? "#36d399" : "#7790a8", lineWidth: 4 });
        this.draw.drawLandmarks(lm, { color: "#e7edf3", lineWidth: 1, radius: 3 });
      }
    }
    this.badge.textContent = isVictory ? "VICTORY" : "idle";
    this.badge.className = "badge " + (isVictory ? "victory" : "idle");
    this.confBar.style.width = `${Math.round(conf * 100)}%`;
  }

  fire(conf) {
    flash(this.zoneTrigger);
    flashGlobal();
    addLog(this.name, conf);
    relayFire(this.name, conf);
  }
}

// ----- web -> relay bridge -----
async function refreshRelayStatus() {
  try {
    const r = await fetch("/api/status", { cache: "no-store" });
    if (!r.ok) throw new Error("no api");
    const j = await r.json();
    apiAvailable = true;
    if (!driveRelayEl.dataset.init) {
      driveRelayEl.disabled = false;
      driveRelayEl.checked = localStorage.getItem("vsign.driveRelay") === "1";
      driveRelayEl.dataset.init = "1";
    }
    const c = j.serial_connected;
    relayStatusEl.dataset.state = c ? "ok" : "off";
    relayStatusEl.title = c
      ? "relay: Arduino connected"
      : "bridge up, Arduino not connected (check serial port / flashing)";
  } catch {
    apiAvailable = false;
    driveRelayEl.disabled = true;
    driveRelayEl.checked = false;
    relayStatusEl.dataset.state = "na";
    relayStatusEl.title = "bridge not running — serve with: python -m src.bridge";
  }
}

async function relayFire(zone, conf) {
  if (!apiAvailable || !driveRelayEl.checked) return;
  try {
    await fetch("/api/fire", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zone, confidence: conf }),
    });
  } catch (e) {
    console.warn("[VSign Detect] relay fire failed:", e);
  }
}

// ----- helpers -----
function setStatus(msg, cls = "") { statusEl.textContent = msg; statusEl.className = "status " + cls; }

function loadParams(name) {
  try {
    const saved = JSON.parse(localStorage.getItem(`vsign.params.${name}`));
    if (saved) return { ...DEFAULTS, ...saved };
  } catch {}
  return { ...DEFAULTS };
}
function saveParams(name, p) { localStorage.setItem(`vsign.params.${name}`, JSON.stringify(p)); }

function flash(el) { el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 450); }
function flashGlobal() {
  globalTrigger.classList.add("fire");
  clearTimeout(flashGlobal._t);
  flashGlobal._t = setTimeout(() => globalTrigger.classList.remove("fire"), 450);
}
function addLog(zone, conf) {
  const li = document.createElement("li");
  const t = new Date().toLocaleTimeString();
  li.innerHTML = `<b>✌ FIRE</b> &nbsp; zone <b>${zone}</b> &nbsp; conf ${conf.toFixed(2)} ` +
    `<span class="t">— ${t}</span>`;
  logEl.prepend(li);
  while (logEl.children.length > 30) logEl.lastChild.remove();
}

function renderConfig() {
  const lines = ["cameras:"];
  for (const z of zones) {
    const label = z.camSelect.selectedOptions[0]?.textContent || "(unset)";
    lines.push(`  - zone: "${z.name}"          # ${label}`);
    lines.push(`    index: 0                 # set OpenCV index on the engine machine`);
    lines.push(`    width: 640`);
    lines.push(`    height: 480`);
    lines.push(`    fps: 30`);
  }
  const p = zones[0]?.params || DEFAULTS;
  lines.push("");
  lines.push("detection:");
  lines.push(`  classifier: gesture_recognizer`);
  lines.push(`  min_score: ${p.minScore}`);
  lines.push(`  num_hands: 1`);
  lines.push("");
  lines.push("trigger:");
  lines.push(`  mode: time`);
  lines.push(`  hold_ms: ${p.holdMs}`);
  lines.push(`  cooldown_s: ${p.cooldownS}`);
  lines.push(`  require_release: true`);
  lines.push(`  release_ms: ${p.releaseMs}`);
  configYamlEl.textContent = lines.join("\n");
}

async function listVideoInputs() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.filter((d) => d.kind === "videoinput");
  } catch (e) {
    setStatus("enumerateDevices failed: " + e.message, "err");
    return [];
  }
}

async function populateCameras({ autostart = true } = {}) {
  const cams = await listVideoInputs();
  console.log("[VSign Detect] video inputs:",
    cams.map((c, i) => ({ i, label: c.label || "(no label)", id: c.deviceId })));

  if (!cams.length) {
    setStatus("No cameras found — check Windows camera privacy settings", "err");
    return;
  }
  if (!cams[0].deviceId) {
    setStatus("Cameras detected but blocked — allow camera access and click Refresh", "err");
  }

  zones.forEach((z, zi) => {
    const prev = z.camSelect.value;
    z.camSelect.innerHTML = "";
    cams.forEach((c, i) => {
      const opt = document.createElement("option");
      opt.value = c.deviceId;
      opt.textContent = c.label || `Camera ${i + 1}`;
      z.camSelect.appendChild(opt);
    });
    const saved = localStorage.getItem(`vsign.cam.${z.name}`);
    const wanted = [prev, saved, cams[Math.min(zi, cams.length - 1)].deviceId]
      .find((id) => id && cams.some((c) => c.deviceId === id));
    if (wanted) z.camSelect.value = wanted;
  });

  if (cams[0].deviceId) {
    setStatus(`${cams.length} camera(s) found`, "ok");
    if (autostart) for (const z of zones) if (z.camSelect.value) z.setCamera(z.camSelect.value);
  }
  renderConfig();
}

async function requestPermission() {
  // Permission is usually granted even if the *default* device can't start
  // (common when a virtual cam is the default) — so we tolerate the error and
  // still enumerate, which will now include real labels.
  try {
    const tmp = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    tmp.getTracks().forEach((t) => t.stop());
    permissionGranted = true;
    return;
  } catch (e) {
    console.warn("[VSign Detect] default getUserMedia:", e.name, e.message);
  }
  // Fallback: try each known device id until one grants permission.
  for (const c of await listVideoInputs()) {
    if (!c.deviceId) continue;
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: c.deviceId } }, audio: false });
      s.getTracks().forEach((t) => t.stop());
      permissionGranted = true;
      return;
    } catch (e2) {
      console.warn("[VSign Detect] device permission failed:", c.label || c.deviceId, e2.name);
    }
  }
}

async function enable() {
  enableBtn.disabled = true;
  setStatus("requesting camera permission…");
  await requestPermission();
  await populateCameras();
  enableBtn.textContent = "Refresh cameras";
  enableBtn.disabled = false;
  if (!devicechangeBound && navigator.mediaDevices.addEventListener) {
    navigator.mediaDevices.addEventListener("devicechange", () => {
      console.log("[VSign Detect] device change detected — refreshing list");
      populateCameras({ autostart: false });
    });
    devicechangeBound = true;
  }
}

async function init() {
  zones.push(new Zone("A"), new Zone("B"));
  renderConfig();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setStatus("This browser/origin can't access cameras — use http://localhost", "err");
  }

  try {
    visionFileset = await FilesetResolver.forVisionTasks(WASM_URL);
    setStatus("model ready — click “Enable cameras”", "ok");
    enableBtn.disabled = false;
  } catch (e) {
    setStatus("Failed to load MediaPipe: " + e.message, "err");
  }

  enableBtn.addEventListener("click", enable);
  document.getElementById("copyCfg").addEventListener("click", () => {
    navigator.clipboard.writeText(configYamlEl.textContent);
  });
  driveRelayEl.addEventListener("change", () => {
    localStorage.setItem("vsign.driveRelay", driveRelayEl.checked ? "1" : "0");
  });

  // Detect the bridge (if the panel is served by src.bridge) and poll status.
  refreshRelayStatus();
  setInterval(refreshRelayStatus, 2500);
}

init();
