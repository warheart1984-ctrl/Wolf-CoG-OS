"""JSON-line client for UL App Bridge daemon (Wine/Darling backends)."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, Dict, Optional

from governance_invariant_engine import cogos_root

DEFAULT_SOCK = cogos_root() / "memory" / "ul_app_bridge" / "bridge.sock"


def socket_path() -> Path:
    env = os.environ.get("COGOS_UL_BRIDGE_SOCK", "").strip()
    return Path(env) if env else DEFAULT_SOCK


def call_verb(
    verb: str,
    args: Dict[str, Any],
    *,
    caller_pid: Optional[int] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    payload = {
        "verb": verb,
        "args": args,
        "caller_pid": caller_pid if caller_pid is not None else os.getpid(),
    }
    sock = socket_path()
    if not sock.exists():
        from ul_app_bridge.bridge import ULAppBridge

        bridge = ULAppBridge()
        return bridge.dispatch(verb, args, caller_pid=caller_pid)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(timeout)
        conn.connect(str(sock))
        conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
        line = buf.split(b"\n", 1)[0]
        return json.loads(line.decode("utf-8"))
