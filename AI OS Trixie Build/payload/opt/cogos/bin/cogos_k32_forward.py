#!/usr/bin/env python3
"""Start/status CoGOS K32 forward daemon (kernel transport peer)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
sys.path.insert(0, str(ROOT / "runtime"))

from k32_forward_daemon import daemon_status, serve_forever  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CoGOS K32 forward daemon")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    start = sub.add_parser("start")
    start.add_argument("--foreground", action="store_true")
    args = parser.parse_args()

    if args.cmd == "status":
        print(json.dumps(daemon_status(), indent=2))
        return 0
    if args.cmd == "start":
        if args.foreground:
            serve_forever()
            return 0
        script = ROOT / "runtime" / "k32_forward_daemon.py"
        subprocess.Popen(
            [sys.executable, str(script), "start"],
            cwd=str(ROOT),
            env={**os.environ, "COGOS_ROOT": str(ROOT)},
            start_new_session=True,
        )
        print(json.dumps({"ok": True, "started": True}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
