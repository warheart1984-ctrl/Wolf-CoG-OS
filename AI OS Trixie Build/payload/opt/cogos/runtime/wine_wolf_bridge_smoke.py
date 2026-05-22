"""Smoke: wine-wolf-bridge governed path (no real Wine required)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from ul_app_bridge.bridge import ULAppBridge  # noqa: E402
from wine_wolf_bridge.launcher import ensure_daemon, launch_windows_app  # noqa: E402
from wine_wolf_bridge import wine_hooks  # noqa: E402
from wine_wolf_bridge.path_map import wine_to_linux  # noqa: E402


def main() -> int:
    ensure_daemon()
    mapped = wine_to_linux(r"C:\Users\Jon\Documents\report.txt")
    assert "Documents" in mapped or "documents" in mapped.lower()

    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"MZ" + b"\x00" * 64)
        fake = tmp.name

    report = launch_windows_app(fake, dry_run=True)
    assert report.get("ok"), report
    assert report.get("sigil"), report
    assert report.get("handshake", {}).get("ok"), report

    pid = os.getpid()
    bridge = ULAppBridge()
    smoke_dir = Path(tempfile.gettempdir()) / "cogos_wine_bridge_smoke"
    for profile in bridge.policy.get("profiles", {}).values():
        profile.setdefault("allowed_path_prefixes", []).append(str(smoke_dir))
    bridge.admit_foreign_exec(fake, pid=pid)
    deny = wine_hooks.create_file(r"C:\Windows\System32\config\SAM", access="read", caller_pid=pid)
    assert not deny.get("ok"), deny

    home_doc = smoke_dir / "wine_bridge_smoke.txt"
    home_doc.parent.mkdir(parents=True, exist_ok=True)
    home_doc.write_text("ok", encoding="utf-8")
    allow = wine_hooks.create_file(
        str(home_doc),
        access="read",
        caller_pid=pid,
    )
    assert allow.get("ok"), allow

    try:
        os.unlink(fake)
    except OSError:
        pass

    print("wine_wolf_bridge_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
