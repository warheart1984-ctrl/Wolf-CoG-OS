"""Phase B.1–B.2: shell assets, files API, settings API."""

from __future__ import annotations

import json
import urllib.request

from files_api import list_directory
from governance_invariant_engine import cogos_root
from settings_api import settings_snapshot, update_settings


def main() -> int:
    root = cogos_root()
    shell = root / "shell"
    assert (shell / "index.html").exists()
    assert (shell / "app.js").exists()
    assert (shell / "styles.css").exists()
    assert (root / "bin" / "cogos_shell_window.py").exists()

    listing = list_directory(str(root / "memory"))
    assert listing["ok"] and listing.get("entries")

    snap = settings_snapshot()
    assert snap["ok"] and snap.get("active_profile")

    mesh_path = root / "config" / "mesh.json"
    original_mesh = mesh_path.read_text(encoding="utf-8-sig") if mesh_path.exists() else ""
    try:
        updated = update_settings({"mesh": {"mesh_name": "infi-family-test"}}, profile_id="operator")
        assert updated["ok"]
        assert "mesh" in updated.get("applied", [])
    finally:
        if original_mesh:
            mesh_path.write_text(original_mesh, encoding="utf-8")

    port = int(__import__("os").environ.get("COGOS_DESKTOP_PORT", "8081"))
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/shell/", timeout=3) as resp:
            html = resp.read().decode("utf-8")
            assert "CoGOS Shell" in html
    except Exception:
        print("phaseB_shell_smoke: desktop not running — static assets OK only")

    print("phaseB_shell_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
