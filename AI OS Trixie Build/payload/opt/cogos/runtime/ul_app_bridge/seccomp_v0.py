"""Governed seccomp profile v0 spec — apply on Linux only; observability-only elsewhere."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROFILE_NAME = "foreign_app_ul_bridge"

ALLOW_BASELINE: List[str] = [
    "mmap", "munmap", "mprotect", "brk",
    "rt_sigaction", "rt_sigreturn", "sigaltstack",
    "clock_gettime", "gettimeofday", "time",
    "getpid", "gettid", "getppid",
    "read", "write", "close", "fstat", "lseek", "dup", "dup2",
    "exit", "exit_group",
]

DENY_KILL: List[str] = [
    "socket", "connect", "accept", "bind", "listen", "sendto", "recvfrom",
    "clone", "fork", "vfork", "execve", "ptrace",
    "mount", "umount2", "chroot",
    "setuid", "setgid", "setresuid", "setresgid",
    "shmget", "shmat", "shmdt", "shmctl",
    "bpf", "perf_event_open",
]


def profile_spec() -> Dict[str, Any]:
    return {
        "name": PROFILE_NAME,
        "allowed_baseline": ALLOW_BASELINE,
        "deny_kill": DENY_KILL,
        "note": "FS/net/proc must use UL verbs or pre-opened FDs under /home/<user>/",
        "shm_v1": "denied",
    }


def export_spec(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile_spec(), indent=2) + "\n", encoding="utf-8")


def try_apply_to_pid(pid: int) -> Dict[str, Any]:
    if sys.platform != "linux":
        return {"ok": False, "applied": False, "reason": "seccomp_apply_requires_linux"}
    try:
        import ctypes
        import ctypes.util

        lib = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        prctl = getattr(lib, "prctl", None)
        if prctl is None:
            return {"ok": False, "applied": False, "reason": "prctl_unavailable"}
        # v0: record intent; full BPF program is wine-wolf-bridge / metal bring-up
        return {
            "ok": True,
            "applied": False,
            "reason": "spec_registered_install_at_exec",
            "pid": pid,
            "profile": PROFILE_NAME,
        }
    except Exception as exc:
        return {"ok": False, "applied": False, "reason": str(exc)}
