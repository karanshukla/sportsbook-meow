/**
 * sportsbook-meow content script
 *
 * For every <video> on the page:
 *   1. Creates a transparent overlay canvas positioned exactly over it
 *   2. Samples frames at ~10 fps and sends JPEG bytes to the local server
 *   3. Draws a random cat image over each detected bounding box
 *
 * All cat images are bundled with the extension in extension/cats/.
 */

const DEFAULT_SERVER = "ws://localhost:8765";
const SAMPLE_FPS = 10;
const SAMPLE_INTERVAL_MS = 1000 / SAMPLE_FPS;
// JPEG encode quality (0–1). Lower = faster transfer, good enough for detection.
const JPEG_QUALITY = 0.7;
// Scale frames down to this width before sending (keeps inference fast).
const INFER_MAX_WIDTH = 640;

// ── cat image pool ────────────────────────────────────────────────────────────

const catImages = [];
let catsLoaded = false;

function loadCats() {
  if (catsLoaded) return;
  catsLoaded = true;
  // The extension bundles up to 30 cat images; load whichever exist.
  const attempts = Array.from({ length: 30 }, (_, i) =>
    chrome.runtime.getURL(`cats/cat_${String(i + 1).padStart(3, "0")}.jpg`)
  );
  for (const url of attempts) {
    const img = new Image();
    img.onload = () => catImages.push(img);
    img.onerror = () => {}; // not all 30 slots are filled — that's fine
    img.src = url;
  }
}

// ── WebSocket connection (shared across all overlays on the page) ─────────────

let ws = null;
let wsUrl = DEFAULT_SERVER;
let enabled = true;
let pendingCallbacks = []; // resolvers waiting for the next server response

function wsConnect() {
  if (ws && ws.readyState <= WebSocket.OPEN) return;

  ws = new WebSocket(wsUrl);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    document.dispatchEvent(new CustomEvent("sbm:status", { detail: "connected" }));
  };

  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      const cb = pendingCallbacks.shift();
      if (cb) cb(data.detections || []);
    } catch (_) {}
  };

  ws.onclose = () => {
    document.dispatchEvent(new CustomEvent("sbm:status", { detail: "disconnected" }));
    pendingCallbacks.forEach((cb) => cb([]));
    pendingCallbacks = [];
    // Retry after 3 s
    setTimeout(wsConnect, 3000);
  };

  ws.onerror = () => ws.close();
}

/**
 * Send a JPEG blob to the server; returns a Promise<detection[]>.
 * If the socket isn't ready, resolves immediately with [].
 */
function sendFrame(blob) {
  return new Promise((resolve) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      resolve([]);
      return;
    }
    pendingCallbacks.push(resolve);
    blob.arrayBuffer().then((buf) => ws.send(buf));
  });
}

// ── per-video overlay ─────────────────────────────────────────────────────────

class VideoOverlay {
  constructor(video) {
    this.video = video;
    this.detections = [];
    this.lastSampleTime = 0;
    this.inflight = false;
    this.destroyed = false;

    // Offscreen canvas used for capturing frames at reduced resolution
    this.offscreen = document.createElement("canvas");

    // Visible overlay canvas — sits on top of the video
    this.canvas = document.createElement("canvas");
    this.canvas.style.cssText = [
      "position:fixed",
      "pointer-events:none",
      "z-index:2147483647",
      "top:0",
      "left:0",
    ].join(";");
    document.documentElement.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d");

    // Keep overlay in sync with video position
    this._ro = new ResizeObserver(() => this._sync());
    this._ro.observe(video);
    this._onScroll = () => this._sync();
    window.addEventListener("scroll", this._onScroll, { passive: true });
    window.addEventListener("resize", this._onScroll, { passive: true });

    // Handle fullscreen transitions
    this._onFullscreen = () => this._sync();
    document.addEventListener("fullscreenchange", this._onFullscreen);

    this._sync();
    this._loop(0);
  }

  _sync() {
    if (this.destroyed) return;
    const r = this.video.getBoundingClientRect();
    this.canvas.style.left = `${r.left}px`;
    this.canvas.style.top = `${r.top}px`;
    this.canvas.width = r.width;
    this.canvas.height = r.height;
    this._draw();
  }

  _loop(ts) {
    if (this.destroyed) return;

    // Remove overlay if video was removed from DOM
    if (!document.contains(this.video)) {
      this.destroy();
      return;
    }

    this._draw();

    if (
      enabled &&
      !this.inflight &&
      !this.video.paused &&
      this.video.readyState >= 2 &&
      ts - this.lastSampleTime >= SAMPLE_INTERVAL_MS
    ) {
      this.lastSampleTime = ts;
      this._sample();
    }

    requestAnimationFrame((t) => this._loop(t));
  }

  _sample() {
    const vw = this.video.videoWidth;
    const vh = this.video.videoHeight;
    if (!vw || !vh) return;

    const scale = Math.min(1, INFER_MAX_WIDTH / vw);
    const ow = Math.round(vw * scale);
    const oh = Math.round(vh * scale);
    this.offscreen.width = ow;
    this.offscreen.height = oh;

    const octx = this.offscreen.getContext("2d");
    octx.drawImage(this.video, 0, 0, ow, oh);

    this.inflight = true;
    this.offscreen.toBlob(
      (blob) => {
        if (!blob) { this.inflight = false; return; }
        sendFrame(blob).then((dets) => {
          this.detections = dets;
          this.inflight = false;
        });
      },
      "image/jpeg",
      JPEG_QUALITY
    );
  }

  _draw() {
    const { width: cw, height: ch } = this.canvas;
    this.ctx.clearRect(0, 0, cw, ch);
    if (!enabled || !this.detections.length || !catImages.length) return;

    for (let i = 0; i < this.detections.length; i++) {
      const d = this.detections[i];
      const x = d.x1 * cw;
      const y = d.y1 * ch;
      const w = (d.x2 - d.x1) * cw;
      const h = (d.y2 - d.y1) * ch;
      if (w < 2 || h < 2) continue;
      // Pick a consistent cat per detection index so it doesn't flicker
      const cat = catImages[i % catImages.length];
      this.ctx.drawImage(cat, x, y, w, h);
    }
  }

  destroy() {
    this.destroyed = true;
    this._ro.disconnect();
    window.removeEventListener("scroll", this._onScroll);
    window.removeEventListener("resize", this._onScroll);
    document.removeEventListener("fullscreenchange", this._onFullscreen);
    this.canvas.remove();
  }
}

// ── video discovery ───────────────────────────────────────────────────────────

const overlays = new WeakMap();

function attachIfNeeded(video) {
  if (!(video instanceof HTMLVideoElement)) return;
  if (overlays.has(video)) return;
  // Skip tiny invisible or picture-in-picture videos
  if (video.width < 100 && video.offsetWidth < 100) return;
  const overlay = new VideoOverlay(video);
  overlays.set(video, overlay);
}

function scanVideos() {
  document.querySelectorAll("video").forEach(attachIfNeeded);
}

// Watch for videos added dynamically (SPAs, lazy-loaded players)
const mo = new MutationObserver((mutations) => {
  for (const m of mutations) {
    for (const node of m.addedNodes) {
      if (node.nodeName === "VIDEO") attachIfNeeded(node);
      if (node.querySelectorAll) node.querySelectorAll("video").forEach(attachIfNeeded);
    }
  }
});
mo.observe(document.documentElement, { childList: true, subtree: true });

// ── init ──────────────────────────────────────────────────────────────────────

chrome.storage.local.get(["enabled", "serverUrl"], (prefs) => {
  enabled = prefs.enabled !== false;
  wsUrl = prefs.serverUrl || DEFAULT_SERVER;
  loadCats();
  wsConnect();
  scanVideos();
});

// Keep enabled/serverUrl in sync when user changes settings in the popup
chrome.storage.onChanged.addListener((changes) => {
  if (changes.enabled !== undefined) enabled = changes.enabled.newValue;
  if (changes.serverUrl !== undefined) {
    wsUrl = changes.serverUrl.newValue || DEFAULT_SERVER;
    if (ws) ws.close(); // reconnect with new URL
  }
});
