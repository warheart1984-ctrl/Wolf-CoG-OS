#!/usr/bin/env python3
"""CLI: UL App Bridge — governed foreign app compatibility membrane."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from ul_app_bridge.bridge import ULAppBridge  # noqa: E402
from ul_app_bridge.classifier import classify_binary  # noqa: E402
from ul_app_bridge.schema import UL_BRIDGE_VERSION  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Wolf CoG OS UL App Bridge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="UL bridge schema version")
    p_class = sub.add_parser("classify", help="Classify binary as foreign/native")
    p_class.add_argument("path")

    p_admit = sub.add_parser("admit", help="Exec admission: assign sigil + register PID")
    p_admit.add_argument("path")
    p_admit.add_argument("--pid", type=int, default=None)

    p_verb = sub.add_parser("invoke", help="Invoke UL verb for caller PID")
    p_verb.add_argument("verb")
    p_verb.add_argument("--pid", type=int, default=None)
    p_verb.add_argument("--args", default="{}")

    p_sum = sub.add_parser("summary", help="Governance summary for sigil")
    p_sum.add_argument("--sigil", default=None)

    sub.add_parser("verify-ledger", help="Verify hash-chained provenance")
    sub.add_parser("seccomp-spec", help="Print governed seccomp v0 spec")

    args = parser.parse_args()
    bridge = ULAppBridge()

    if args.cmd == "version":
        print(UL_BRIDGE_VERSION)
        return 0
    if args.cmd == "classify":
        print(json.dumps(classify_binary(args.path), indent=2))
        return 0
    if args.cmd == "admit":
        print(json.dumps(bridge.admit_foreign_exec(args.path, pid=args.pid), indent=2))
        return 0
    if args.cmd == "invoke":
        payload = json.loads(args.args)
        print(json.dumps(bridge.dispatch(args.verb, payload, caller_pid=args.pid), indent=2))
        return 0
    if args.cmd == "summary":
        print(json.dumps(bridge.governance_summary(sigil=args.sigil), indent=2))
        return 0
    if args.cmd == "verify-ledger":
        print(json.dumps(bridge.provenance.verify(), indent=2))
        return 0
    if args.cmd == "seccomp-spec":
        from ul_app_bridge.seccomp_v0 import profile_spec

        print(json.dumps(profile_spec(), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
