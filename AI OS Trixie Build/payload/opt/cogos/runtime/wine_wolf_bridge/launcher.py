"""Auto-governed Wine launch — no compatibility toggle."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root
from ul_app_bridge.bridge import ULAppBridge
from wine_wolf_bridge import wine_hooks
from wine_wolf_bridge.client import socket_path


def _wine_binary() -> Optional[str]:
    for name in ("wine", "wine64", "wine-stable"):
        path = shutil.which(name)
        if path:
            return path
    return None


def ensure_daemon() -> Dict[str, Any]:
    pid_file = cogos_root() / "memory" / "ul_app_bridge" / "bridge_daemon.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return {"ok": True, "running": True, "pid": pid}
        except (OSError, ValueError):
            pid_file.unlink(missing_ok=True)
    if socket_path().exists():
        socket_path().unlink(missing_ok=True)
    runtime = cogos_root() / "runtime"
    proc = subprocess.Popen(
        [sys.executable, str(runtime / "wine_wolf_bridge" / "daemon.py"), "--foreground"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(20):
        if socket_path().exists():
            return {"ok": True, "started": True, "pid": proc.pid}
        time.sleep(0.1)
    return {"ok": False, "reason": "daemon_start_timeout", "pid": proc.pid}


def launch_windows_app(
    exe_path: str,
    args: Optional[List[str]] = None,
    *,
    profile_id: str = "win.default.safe",
    dry_run: bool = False,
) -> Dict[str, Any]:
    exe = str(Path(exe_path).resolve())
    bridge = ULAppBridge()
    ensure_daemon()
    admit = bridge.admit_foreign_exec(exe, pid=os.getpid(), profile_id=profile_id)
    if not admit.get("ok"):
        return admit

    hs = wine_hooks.handshake(caller_pid=os.getpid())
    if not hs.get("ok"):
        return {"ok": False, "stage": "handshake", "result": hs}

    wine = _wine_binary()
    report: Dict[str, Any] = {
        "ok": True,
        "exe": exe,
        "sigil": admit.get("sigil"),
        "profile_id": admit.get("profile_id"),
        "handshake": hs,
        "governance_summary": "Windows app admitted under UL App Bridge",
    }

    shim = cogos_root() / "lib" / "libcogos_wine_preload.so"
    env = os.environ.copy()
    env["COGOS_UL_BRIDGE_SOCK"] = str(socket_path())
    env["COGOS_WINE_SIGIL"] = str(admit.get("sigil", ""))
    if shim.is_file():
        env["LD_PRELOAD"] = f"{shim}:{env.get('LD_PRELOAD', '')}".strip(":")

    wine_hooks.log_app(
        f"app.{admit.get('sigil', 'wine')}",
        f"Launch {Path(exe).name}",
        caller_pid=os.getpid(),
    )

    if dry_run or not wine:
        report["mode"] = "governed_stub" if not wine else "dry_run"
        report["wine"] = wine
        return report

    cmd = [wine, exe] + (args or [])
    if dry_run:
        report["cmd"] = cmd
        return report

    proc = subprocess.Popen(cmd, env=env)
    parent_rec = bridge.registry.lookup(os.getpid())
    if parent_rec:
        caps = parent_rec.caps
    else:
        prof = (bridge.policy.get("profiles") or {}).get(
            str(admit.get("profile_id", profile_id)), {}
        )
        caps = list(prof.get("caps") or [])
    bridge.registry.register(
        proc.pid,
        profile_id=str(admit.get("profile_id", profile_id)),
        bridge_class="foreign_app_ul_bridge",
        backend="wine",
        caps=caps,
        sigil=str(admit.get("sigil")),
        parent_sigil=str(admit.get("sigil")),
        spawn_mode="inherit",
        binary_hint=Path(exe).name,
    )
    report["mode"] = "wine_exec"
    report["wine_pid"] = proc.pid
    report["cmd"] = cmd
    return report
