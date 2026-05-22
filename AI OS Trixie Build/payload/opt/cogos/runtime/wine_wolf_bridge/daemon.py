"""UL App Bridge UNIX socket daemon for Wine/Darling clients."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from typing import Any, Dict

from governance_invariant_engine import cogos_root
from ul_app_bridge.bridge import ULAppBridge
from wine_wolf_bridge.client import socket_path


def serve(*, foreground: bool = True) -> None:
    bridge = ULAppBridge()
    sock_path = socket_path()
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    if sock_path.exists():
        sock_path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    try:
        os.chmod(sock_path, 0o666)
    except OSError:
        pass
    server.listen(32)
    pid_file = cogos_root() / "memory" / "ul_app_bridge" / "bridge_daemon.pid"
    pid_file.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    if foreground:
        print(f"wine-wolf-bridge daemon on {sock_path}", flush=True)
    while True:
        conn, _ = server.accept()
        with conn:
            buf = b""
            while b"\n" not in buf:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf += chunk
            if not buf.strip():
                continue
            req = json.loads(buf.split(b"\n", 1)[0].decode("utf-8"))
            result = bridge.dispatch(
                req.get("verb", ""),
                req.get("args") or {},
                caller_pid=req.get("caller_pid"),
            )
            conn.sendall((json.dumps(result) + "\n").encode("utf-8"))


def main() -> int:
    serve(foreground="--foreground" in sys.argv or "-f" in sys.argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
