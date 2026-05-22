#!/usr/bin/env python3
"""CLI for CoGOS install + persistence proof bundles (Phase A.1)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
RUNTIME = ROOT / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from install_proof import InstallProofCollector, METAL_CHECKLIST  # noqa: E402
from metal_proof import capture_full_metal_proof, idle_soak  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CoGOS install proof collector")
    sub = parser.add_subparsers(dest="cmd", required=True)

    cap = sub.add_parser("capture", help="Capture proof bundle")
    cap.add_argument("--target", default="", help="Install target e.g. /dev/sdX")
    cap.add_argument("--label", default="capture")
    cap.add_argument("--output", default="", help="Output directory")
    cap.add_argument("--full", action="store_true", help="Full metal proof: eval + pid1 + RAID + backup + recovery")
    cap.add_argument("--idle-minutes", type=int, default=0, help="Optional idle soak duration (e.g. 30)")

    full = sub.add_parser("capture-full", help="Full metal proof bundle (checklist #5)")
    full.add_argument("--target", default="")
    full.add_argument("--label", default="metal")
    full.add_argument("--output", default="")
    full.add_argument("--no-eval", action="store_true")
    full.add_argument("--idle-minutes", type=int, default=0)

    soak = sub.add_parser("idle-soak", help="30-minute idle corridor/ledger soak")
    soak.add_argument("--minutes", type=int, default=30)
    soak.add_argument("--interval", type=int, default=60)

    sub.add_parser("verify", help="Verify latest or bundled proof")
    ver = sub.add_parser("verify-bundle")
    ver.add_argument("bundle", nargs="?", default="")

    chk = sub.add_parser("checklist", help="Print metal validation checklist")
    chk.add_argument("--json", action="store_true")

    plan = sub.add_parser("plan")
    plan.add_argument("--target", required=True)
    val = sub.add_parser("validate")
    val.add_argument("--target", required=True)

    ns = parser.parse_args(argv)
    collector = InstallProofCollector()

    if ns.cmd == "capture":
        if getattr(ns, "full", False) or getattr(ns, "idle_minutes", 0):
            out = capture_full_metal_proof(
                target=ns.target,
                label=ns.label,
                output_dir=Path(ns.output) if ns.output else None,
                run_eval=not getattr(ns, "no_eval", False),
                idle_minutes=getattr(ns, "idle_minutes", 0),
            )
        else:
            out = collector.capture_bundle(
                target=ns.target,
                label=ns.label,
                output_dir=Path(ns.output) if ns.output else None,
            )
    elif ns.cmd == "capture-full":
        out = capture_full_metal_proof(
            target=ns.target,
            label=ns.label,
            output_dir=Path(ns.output) if ns.output else None,
            run_eval=not ns.no_eval,
            idle_minutes=ns.idle_minutes,
        )
    elif ns.cmd == "idle-soak":
        out = idle_soak(minutes=ns.minutes, interval_sec=ns.interval)
    elif ns.cmd == "verify":
        out = collector.verify_bundle()
    elif ns.cmd == "verify-bundle":
        path = Path(ns.bundle) if ns.bundle else None
        out = collector.verify_bundle(path)
    elif ns.cmd == "checklist":
        checks = collector.auto_checks()
        rows = collector.build_checklist(checks)
        out = {"ok": True, "checklist": rows, "catalog": METAL_CHECKLIST}
        if not ns.json:
            for row in rows:
                mark = "?" if row.get("passed") is None else ("PASS" if row["passed"] else "FAIL")
                print(f"[{mark}] {row['id']}: {row['label']}")
            return 0
    elif ns.cmd == "plan":
        out = collector.install_plan(ns.target)
    elif ns.cmd == "validate":
        out = collector.install_validate(ns.target)
    else:
        return 2

    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
