"""Smoke: physical mesh file-drop roundtrip."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from mesh_transport import physical_roundtrip_proof  # noqa: E402


def main() -> int:
    report = physical_roundtrip_proof(
        peers=["smoke-laptop", "smoke-desktop", "smoke-mini"],
    )
    assert report.get("ok"), report
    assert (report.get("imported") or {}).get("admitted", 0) >= 3
    print("mesh_physical_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
