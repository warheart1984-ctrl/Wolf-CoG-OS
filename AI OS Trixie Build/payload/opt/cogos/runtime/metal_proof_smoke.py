"""Smoke: metal_proof bundle structure (dev host; no full eval or disk scan)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from install_proof import InstallProofCollector  # noqa: E402
from metal_proof import capture_full_metal_proof  # noqa: E402


def main() -> int:
    import os

    if os.name != "nt":
        out = capture_full_metal_proof(label="smoke", run_eval=False, idle_minutes=0)
        assert out.get("merged_bundle_path"), out
    else:
        bundle = InstallProofCollector().capture_bundle(label="smoke-win")
        path = Path(bundle["bundle_path"])
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("checklist")
    print("metal_proof_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
