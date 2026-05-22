#!/usr/bin/env python3
"""wine-wolf-bridge CLI — daemon, launch, status."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from wine_wolf_bridge.launcher import ensure_daemon, launch_windows_app  # noqa: E402
from wine_wolf_bridge import wine_hooks  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Wolf CoG OS wine-wolf-bridge")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("daemon", help="Run bridge socket daemon (foreground)")
    sub.add_parser("ensure-daemon", help="Start daemon if needed")
    p_run = sub.add_parser("run", help="Launch Windows .exe under governance")
    p_run.add_argument("exe")
    p_run.add_argument("args", nargs="*")
    p_run.add_argument("--profile", default="win.default.safe")
    p_run.add_argument("--dry-run", action="store_true")
    p_hook = sub.add_parser("hook-test", help="Simulate CreateFile via UL")
    p_hook.add_argument("win_path")
    p_hook.add_argument("--write", action="store_true")
    sub.add_parser("status", help="Daemon + policy status")

    args = p.parse_args()
    if args.cmd == "daemon":
        from wine_wolf_bridge.daemon import serve
        serve(foreground=True)
        return 0
    if args.cmd == "ensure-daemon":
        print(json.dumps(ensure_daemon(), indent=2))
        return 0
    if args.cmd == "run":
        print(json.dumps(launch_windows_app(args.exe, args.args, profile_id=args.profile, dry_run=args.dry_run), indent=2))
        return 0
    if args.cmd == "hook-test":
        if args.write:
            r = wine_hooks.create_file(args.win_path, access="write", data="wolf-bridge-test")
        else:
            r = wine_hooks.create_file(args.win_path, access="read")
        print(json.dumps(r, indent=2))
        return 0 if r.get("ok") else 1
    if args.cmd == "status":
        from governance_invariant_engine import cogos_root
        from ul_app_bridge.bridge import ULAppBridge
        import json as _json

        cfg = _json.loads((cogos_root() / "config" / "wine_wolf_bridge.json").read_text(encoding="utf-8-sig"))
        print(_json.dumps({"daemon": ensure_daemon(), "policy": cfg, "ledger": ULAppBridge().provenance.verify()}, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
