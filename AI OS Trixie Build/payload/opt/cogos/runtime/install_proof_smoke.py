"""Smoke checks for install proof bundle (Phase A.1)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from governance_invariant_engine import cogos_root
from install_proof import InstallProofCollector


def main() -> int:
    root = cogos_root()
    collector = InstallProofCollector(root)

    if os.name == "nt":
        bundle = collector.capture_bundle(target="", label="phase-a1-smoke")
    else:
        bundle = collector.capture_bundle(target="/dev/sdz", label="phase-a1-smoke")
    assert bundle.get("ok"), bundle
    assert (root / "memory" / "logs" / "install_proof_bundle.json").exists()

    verify = collector.verify_bundle()
    assert "ok" in verify, verify
    assert isinstance(bundle.get("checklist"), list) and len(bundle["checklist"]) >= 8

    installer = root.parent.parent / "usr" / "local" / "bin" / "cogos-install"
    assert installer.exists(), installer
    text = installer.read_text(encoding="utf-8")
    assert "write_proof" in text and "COGOSDATA" in text

    data = json.loads((root / "memory" / "logs" / "install_proof_bundle.json").read_text(encoding="utf-8-sig"))
    assert data["label"] == "phase-a1-smoke"

    print("install_proof_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
