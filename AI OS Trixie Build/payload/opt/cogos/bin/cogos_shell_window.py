#!/usr/bin/env python3
"""Launch CoGOS windowed shell (native webview or browser fallback)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
PORT = int(os.environ.get("COGOS_DESKTOP_PORT", "8081"))
URL = f"http://127.0.0.1:{PORT}/shell"


def _ensure_desktop() -> None:
    import urllib.request

    try:
        with urllib.request.urlopen(URL, timeout=2) as resp:
            if resp.status == 200:
                return
    except Exception:
        pass
    desktop = ROOT / "bin" / "cogos_desktop.py"
    if not desktop.exists():
        raise SystemExit(f"missing {desktop}")
    env = {**os.environ, "COGOS_ROOT": str(ROOT)}
    subprocess.Popen(
        [sys.executable, str(desktop)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            with urllib.request.urlopen(URL, timeout=1) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.3)
    raise SystemExit("desktop did not start in time")


def main() -> int:
    _ensure_desktop()
    try:
        import webview  # type: ignore

        webview.create_window("Wolf CoG OS Shell", URL, width=1280, height=800)
        webview.start()
        return 0
    except ImportError:
        print(f"pywebview not installed — opening browser: {URL}", flush=True)
        webbrowser.open(URL)
        print("Press Ctrl+C to exit.", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
