"""Smoke: .exe auto-launcher and MIME bindings."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from ul_app_bridge.bridge import ULAppBridge  # noqa: E402


def main() -> int:
    launcher = ROOT / "bin" / "cogos-win-launcher"
    desktop = ROOT.parent.parent / "usr" / "share" / "applications" / "cogos-win-launcher.desktop"
    mime_xml = ROOT.parent.parent / "usr" / "share" / "mime" / "packages" / "wolf-exe.xml"
    mimeapps = ROOT.parent.parent / "etc" / "xdg" / "mimeapps.list"

    assert launcher.exists(), launcher
    assert desktop.exists(), desktop
    assert mime_xml.exists(), mime_xml
    assert mimeapps.exists(), mimeapps
    assert "application/x-msdownload" in desktop.read_text(encoding="utf-8")
    assert "*.exe" in mime_xml.read_text(encoding="utf-8")
    assert "cogos-win-launcher.desktop" in mimeapps.read_text(encoding="utf-8")

    policy = ULAppBridge().policy
    assert "win.default.safe" in policy.get("profiles", {})

    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"MZ" + b"\x00" * 64)
        fake_exe = tmp.name

    env = os.environ.copy()
    env["COGOS_ROOT"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, str(launcher), "--dry-run", "--json", fake_exe],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=20,
    )
    try:
        os.unlink(fake_exe)
    except OSError:
        pass

    assert proc.returncode == 0, proc.stderr or proc.stdout
    result = json.loads(proc.stdout)
    assert result.get("ok"), result
    assert result.get("profile_id") == "win.default.safe", result

    print("win_launcher_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
