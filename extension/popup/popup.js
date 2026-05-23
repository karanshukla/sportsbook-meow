const dot        = document.getElementById("dot");
const statusText = document.getElementById("status-text");
const toggle     = document.getElementById("toggle");
const toggleLabel= document.getElementById("toggle-label");
const serverInput= document.getElementById("server-url");
const saveBtn    = document.getElementById("save-btn");
const countEl    = document.getElementById("count");

// ── load saved settings ───────────────────────────────────────────────────────

chrome.storage.local.get(["enabled", "serverUrl", "replaceCount"], (prefs) => {
  toggle.checked = prefs.enabled !== false;
  toggleLabel.textContent = toggle.checked ? "Cats enabled" : "Cats disabled";
  serverInput.value = prefs.serverUrl || "ws://localhost:8765";
  countEl.textContent = prefs.replaceCount ?? 0;
});

// ── probe server status ───────────────────────────────────────────────────────

function probeServer(url) {
  try {
    const ws = new WebSocket(url);
    ws.onopen = () => {
      setStatus("connected");
      ws.close();
    };
    ws.onerror = () => setStatus("disconnected");
    ws.onclose = () => {};
    setTimeout(() => { if (ws.readyState !== WebSocket.OPEN) setStatus("disconnected"); }, 2500);
  } catch (_) {
    setStatus("disconnected");
  }
}

function setStatus(state) {
  dot.className = `dot ${state}`;
  statusText.textContent = state === "connected" ? "Server connected" : "Server offline";
}

chrome.storage.local.get(["serverUrl"], (p) => probeServer(p.serverUrl || "ws://localhost:8765"));

// ── toggle ────────────────────────────────────────────────────────────────────

toggle.addEventListener("change", () => {
  chrome.storage.local.set({ enabled: toggle.checked });
  toggleLabel.textContent = toggle.checked ? "Cats enabled" : "Cats disabled";
});

// ── save server URL ───────────────────────────────────────────────────────────

saveBtn.addEventListener("click", () => {
  const url = serverInput.value.trim() || "ws://localhost:8765";
  chrome.storage.local.set({ serverUrl: url });
  probeServer(url);
  saveBtn.textContent = "Saved ✓";
  setTimeout(() => (saveBtn.textContent = "Save"), 1500);
});
