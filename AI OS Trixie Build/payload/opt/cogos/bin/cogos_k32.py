#!/usr/bin/env python3
"""CoGOS K32 semantic control plane CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(RUNTIME / "ul"))

from k32_router import K32ExecutionContext, K32RuntimeRouter  # noqa: E402
from k32_userspace_shim import cog_k32  # noqa: E402
from ul.ul_intent_schema import KLayer, ULIntent, k_class_of  # noqa: E402
from automatic_gate import auto_decide, gate_intent  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CoGOS K32 semantic plane")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    sub.add_parser("table")
    sub.add_parser("forward-status")
    fwd = sub.add_parser("forward-start")
    fwd.add_argument("--foreground", action="store_true")

    call = sub.add_parser("call")
    call.add_argument("k_layer", type=int)
    call.add_argument("--op-code", type=int, default=0x0001)
    call.add_argument("--device-id", default="")
    call.add_argument("--profile", default="operator")

    gate = sub.add_parser("gate")
    gate.add_argument("k_layer", type=int)
    gate.add_argument("--profile", default="operator")

    args = parser.parse_args()

    if args.cmd == "status":
        print(json.dumps(K32RuntimeRouter().status(), indent=2))
        return 0
    if args.cmd == "forward-status":
        from k32_forward_daemon import daemon_status  # noqa: E402

        print(json.dumps(daemon_status(), indent=2))
        return 0
    if args.cmd == "forward-start":
        import subprocess

        script = ROOT / "bin" / "cogos_k32_forward.py"
        cmd = [sys.executable, str(script), "start"]
        if args.foreground:
            cmd.append("--foreground")
            return subprocess.call(cmd)
        subprocess.Popen(cmd, cwd=str(ROOT), env={**os.environ, "COGOS_ROOT": str(ROOT)}, start_new_session=True)
        print(json.dumps({"ok": True, "started": True}, indent=2))
        return 0
    if args.cmd == "table":
        table = ROOT / "config" / "k32_kernel_table.json"
        print(table.read_text(encoding="utf-8-sig"))
        return 0
    if args.cmd == "gate":
        intent = ULIntent(name="cli-gate", k_layer=KLayer(args.k_layer))
        print(json.dumps({"decision": auto_decide(intent), "gate": gate_intent(intent, operator_present=args.profile == "operator")}, indent=2))
        return 0
    if args.cmd == "call":
        payload = {"op_code": args.op_code, "size": 32}
        if args.device_id:
            payload["device_id"] = args.device_id
        rc = cog_k32(args.k_layer, payload, profile_id=args.profile)
        print(json.dumps({"returncode": rc, "k_layer": args.k_layer, "payload": payload}, indent=2))
        return 0 if rc == 0 else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
