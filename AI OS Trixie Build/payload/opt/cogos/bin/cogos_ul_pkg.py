#!/usr/bin/env python3
"""CoGOS UL package manager (Phase C)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("COGOS_ROOT", "/opt/cogos"))
sys.path.insert(0, str(ROOT / "runtime"))

from ul_package_manager import (  # noqa: E402
    install_ul_package,
    list_ul_packages,
    remove_ul_package,
    verify_catalog,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="CoGOS UL packages")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("verify")
    inst = sub.add_parser("install")
    inst.add_argument("package_id")
    inst.add_argument("--profile", default="operator")
    rem = sub.add_parser("remove")
    rem.add_argument("package_id")
    rem.add_argument("--profile", default="operator")
    args = parser.parse_args()

    if args.cmd == "list":
        print(json.dumps(list_ul_packages(), indent=2))
        return 0
    if args.cmd == "verify":
        out = verify_catalog()
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "install":
        out = install_ul_package(args.package_id, profile_id=args.profile)
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "remove":
        out = remove_ul_package(args.package_id, profile_id=args.profile)
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
