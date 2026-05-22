#!/usr/bin/env python3
"""CoGOS billing hooks CLI (Phase C scaffold)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
sys.path.insert(0, str(ROOT / "runtime"))

from billing_hooks import export_usage, reset_usage, status  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CoGOS billing hooks")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("export")
    sub.add_parser("reset")
    args = parser.parse_args()

    if args.cmd == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if args.cmd == "export":
        print(json.dumps(export_usage(), indent=2))
        return 0
    if args.cmd == "reset":
        print(json.dumps(reset_usage(), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
