// Service worker — relays enabled/disabled state changes to content scripts.
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ enabled: true, serverUrl: "ws://localhost:8765" });
});
