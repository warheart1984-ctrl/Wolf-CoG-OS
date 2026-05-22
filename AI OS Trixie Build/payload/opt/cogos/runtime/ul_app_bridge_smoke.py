"""Smoke: UL App Bridge v0 proof loop (no Wine required)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from ul_app_bridge.bridge import ULAppBridge  # noqa: E402


def main() -> int:
    bridge = ULAppBridge()
    smoke_dir = Path(tempfile.gettempdir()) / "cogos_ul_bridge_smoke"
    for profile in bridge.policy.get("profiles", {}).values():
        profile.setdefault("allowed_path_prefixes", []).append(str(smoke_dir))
    pid = 43210
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
        tmp.write(b"MZ" + b"\x00" * 64)
        fake_exe = tmp.name

    admit = bridge.admit_foreign_exec(fake_exe, pid=pid)
    assert admit.get("ok") and admit.get("sigil"), admit

    hs = bridge.dispatch(
        "ul.handshake",
        {"client": "wine", "client_version": "9.0", "ul_version": "1.0.0"},
        caller_pid=pid,
    )
    assert hs.get("ok"), hs
    assert hs.get("sigil") == admit["sigil"]

    deny = bridge.dispatch(
        "ul.fs.read",
        {"path": "/etc/shadow"},
        caller_pid=pid,
    )
    assert not deny.get("ok"), deny
    assert deny.get("error") == "ERR_POLICY_DENY"
    assert deny.get("mapped_os_error") == "EACCES"

    home = smoke_dir
    home.mkdir(parents=True, exist_ok=True)
    doc = home / "ul_bridge_smoke.txt"
    doc.write_text("governed", encoding="utf-8")

    allow = bridge.dispatch(
        "ul.fs.read",
        {"path": str(doc)},
        caller_pid=pid,
    )
    assert allow.get("ok"), allow
    assert "governed" in str(allow.get("data", ""))

    verify = bridge.provenance.verify()
    assert verify.get("ok"), verify

    summary = bridge.governance_summary(sigil=admit["sigil"])
    assert summary.get("verify", {}).get("ok")

    try:
        os.unlink(fake_exe)
    except OSError:
        pass

    print("ul_app_bridge_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
