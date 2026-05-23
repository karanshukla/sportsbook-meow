"""
System-tray launcher for the sportsbook-meow inference server.

Works on WSL (WSLg), Linux, and macOS.
Run via:  ./start-tray.sh   or   make tray
"""

import subprocess
import sys
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw
import pystray

REPO_DIR = Path(__file__).parent
LOG_PATH = REPO_DIR / "server.log"
WS_PORT = 8765


# ── icon drawing ──────────────────────────────────────────────────────────────

def _make_icon(running: bool) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (46, 204, 113) if running else (149, 165, 166)  # green / gray

    # Cat head
    d.ellipse([10, 16, 54, 58], fill=color)
    # Left ear
    d.polygon([(10, 22), (4, 4), (24, 15)], fill=color)
    # Right ear
    d.polygon([(54, 22), (60, 4), (40, 15)], fill=color)

    return img


# ── tray app ──────────────────────────────────────────────────────────────────

class ServerTray:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._icon: pystray.Icon | None = None

    # ── process management ────────────────────────────────────────────────────

    def _running(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def _start(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return
            log_fh = open(LOG_PATH, "a")
            self._proc = subprocess.Popen(
                [sys.executable, "src/serve/server.py"],
                stdout=log_fh,
                stderr=log_fh,
                cwd=REPO_DIR,
            )
        self._refresh()

    def _stop(self) -> None:
        with self._lock:
            if self._proc is None:
                return
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        self._refresh()

    def _toggle(self, icon, item) -> None:  # noqa: ARG002
        if self._running():
            self._stop()
        else:
            self._start()

    # ── icon / menu ───────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if self._icon:
            self._icon.icon = _make_icon(self._running())

    def _status_text(self, item) -> str:  # noqa: ARG002
        if self._running():
            return f"● ws://localhost:{WS_PORT}"
        return "○ Server stopped"

    def _toggle_text(self, item) -> str:  # noqa: ARG002
        return "Stop server" if self._running() else "Start server"

    def _open_logs(self, icon, item) -> None:  # noqa: ARG002
        import os
        if sys.platform == "darwin":
            os.system(f"open '{LOG_PATH}'")  # noqa: S605
        else:
            os.system(f"xdg-open '{LOG_PATH}'")  # noqa: S605

    def _quit(self, icon, item) -> None:  # noqa: ARG002
        self._stop()
        icon.stop()

    # ── poll loop (detects unexpected server exit) ────────────────────────────

    def _poll(self) -> None:
        while True:
            time.sleep(2)
            if self._icon is None:
                continue
            changed = False
            with self._lock:
                if self._proc is not None and self._proc.poll() is not None:
                    self._proc = None
                    changed = True
            if changed:
                self._refresh()

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self) -> None:
        threading.Thread(target=self._poll, daemon=True).start()

        menu = pystray.Menu(
            pystray.MenuItem(self._status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self._toggle_text, self._toggle, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("View logs", self._open_logs),
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon(
            name="sportsbook-meow",
            icon=_make_icon(False),
            title="sportsbook-meow",
            menu=menu,
        )
        self._icon.run()


if __name__ == "__main__":
    ServerTray().run()
