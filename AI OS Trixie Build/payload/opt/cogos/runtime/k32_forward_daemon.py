"""Userspace peer for cog_k32 — listens on /run/cogos/k32.sock and forwards to CoGOS runtime."""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict

from governance_invariant_engine import cogos_root
from k32_forward_protocol import (
    COG_K32_IOCTL_CALL,
    COG_K32_IOCTL_STATUS,
    DEFAULT_SOCK,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)
from k32_router import K32RuntimeRouter
from k32_userspace_shim import cog_k32


def _pid_file() -> Path:
    return cogos_root() / "run" / "k32_forward.pid"


def _log(row: Dict[str, Any]) -> None:
    path = cogos_root() / "memory" / "traces" / "k32_forward.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def handle_message(data: bytes) -> bytes:
    k_layer, payload, profile_id, ioctl = decode_request(data)
    if ioctl == COG_K32_IOCTL_STATUS:
        detail = K32RuntimeRouter().status()
        return encode_response(0, detail)
    rc = cog_k32(k_layer, payload, profile_id=profile_id)
    _log({"event": "forward_call", "k_layer": k_layer, "rc": rc, "op_code": payload.get("op_code")})
    return encode_response(rc, {"k_layer": k_layer, "payload": payload})


def serve_forever(sock_path: Path = DEFAULT_SOCK) -> None:
    sock_path = Path(sock_path)
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    if sock_path.exists():
        try:
            sock_path.unlink()
        except OSError:
            pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    os.chmod(sock_path, 0o660)
    srv.listen(8)
    _pid_file().parent.mkdir(parents=True, exist_ok=True)
    _pid_file().write_text(str(os.getpid()), encoding="utf-8")
    _log({"event": "daemon_start", "socket": str(sock_path), "pid": os.getpid()})
    try:
        while True:
            conn, _ = srv.accept()
            with conn:
                chunks = []
                while True:
                    part = conn.recv(65536)
                    if not part:
                        break
                    chunks.append(part)
                if not chunks:
                    continue
                try:
                    resp = handle_message(b"".join(chunks))
                except Exception as exc:
                    resp = encode_response(-22, {"error": str(exc)})
                conn.sendall(resp)
    finally:
        srv.close()
        try:
            sock_path.unlink()
        except OSError:
            pass
        if _pid_file().exists():
            _pid_file().unlink(missing_ok=True)


def client_call(
    k_layer: int,
    payload: Dict[str, Any],
    *,
    profile_id: str = "operator",
    sock_path: Path = DEFAULT_SOCK,
    timeout: float = 2.0,
) -> int:
    """Forward cog_k32 through running daemon; raises OSError if daemon absent."""
    req = encode_request(k_layer, payload, profile_id=profile_id)
    cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    cli.settimeout(timeout)
    cli.connect(str(sock_path))
    try:
        cli.sendall(req)
        chunks = []
        while True:
            part = cli.recv(65536)
            if not part:
                break
            chunks.append(part)
        rc, _detail = decode_response(b"".join(chunks))
        return rc
    finally:
        cli.close()


def daemon_status(sock_path: Path = DEFAULT_SOCK) -> Dict[str, Any]:
    sock_path = Path(sock_path)
    pid = None
    pf = _pid_file()
    if pf.exists():
        try:
            pid = int(pf.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = None
    alive = bool(pid and _pid_alive(pid))
    if alive:
        try:
            req = encode_request(0, {}, profile_id="operator", ioctl=COG_K32_IOCTL_STATUS)
            cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            cli.settimeout(1.0)
            cli.connect(str(sock_path))
            cli.sendall(req)
            chunks = []
            while True:
                part = cli.recv(65536)
                if not part:
                    break
                chunks.append(part)
            cli.close()
            rc, detail = decode_response(b"".join(chunks))
            return {"ok": True, "running": True, "pid": pid, "socket": str(sock_path), "router": detail if rc == 0 else {}}
        except OSError as exc:
            return {"ok": False, "running": False, "pid": pid, "socket": str(sock_path), "error": str(exc)}
    return {"ok": sock_path.exists(), "running": False, "pid": pid, "socket": str(sock_path)}


def _pid_alive(pid: int) -> bool:
    if os.name != "posix":
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: k32_forward_daemon.py start|status", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "status":
        print(json.dumps(daemon_status(), indent=2))
        return 0
    if cmd == "start":
        serve_forever()
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
