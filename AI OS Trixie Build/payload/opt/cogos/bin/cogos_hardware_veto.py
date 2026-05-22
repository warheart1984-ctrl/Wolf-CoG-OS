#!/usr/bin/env python3
"""CoGOS Hardware Veto CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
sys.path.insert(0, str(ROOT / "runtime"))

from hardware_veto import HardwareVeto  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CoGOS hardware veto status and proof")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("verify")
    sub.add_parser("proof")
    report = sub.add_parser("report")
    report.add_argument("event")
    report.add_argument("--severity", default="info")
    ns = parser.parse_args(argv)

    veto = HardwareVeto()
    if ns.cmd == "status":
        out = veto.status()
    elif ns.cmd == "verify":
        out = veto.verify_contract()
    elif ns.cmd == "proof":
        out = veto.write_proof()
    elif ns.cmd == "report":
        out = veto.report_event(ns.event, ns.severity)
    else:
        return 2
    print(json.dumps(out, indent=2, sort_keys=True, default=str))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
