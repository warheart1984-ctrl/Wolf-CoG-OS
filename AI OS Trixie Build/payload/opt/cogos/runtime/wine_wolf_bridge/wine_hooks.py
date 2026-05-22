"""Wine Win32-style operations → UL verbs (thin hook surface)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from wine_wolf_bridge.client import call_verb
from wine_wolf_bridge.path_map import wine_to_linux


def handshake(*, client_version: str = "9.0", caller_pid: Optional[int] = None) -> Dict[str, Any]:
    return call_verb(
        "ul.handshake",
        {
            "client": "wine",
            "client_version": client_version,
            "ul_version": "1.0.0",
        },
        caller_pid=caller_pid,
    )


def create_file(
    win_path: str,
    *,
    access: str = "read",
    data: bytes | str = b"",
    caller_pid: Optional[int] = None,
) -> Dict[str, Any]:
    linux_path = wine_to_linux(win_path)
    if access == "read":
        return call_verb("ul.fs.read", {"path": linux_path}, caller_pid=caller_pid)
    return call_verb(
        "ul.fs.write",
        {"path": linux_path, "data": data, "mode": "create_or_overwrite"},
        caller_pid=caller_pid,
    )


def list_directory(win_path: str, *, caller_pid: Optional[int] = None) -> Dict[str, Any]:
    return call_verb("ul.fs.list", {"path": wine_to_linux(win_path)}, caller_pid=caller_pid)


def http_request(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    body: str = "",
    caller_pid: Optional[int] = None,
) -> Dict[str, Any]:
    return call_verb(
        "ul.net.request",
        {"method": method, "url": url, "headers": headers or {}, "body": body},
        caller_pid=caller_pid,
    )


def spawn_process(
    command: str,
    args: Optional[List[str]] = None,
    *,
    spawn_mode: str = "inherit",
    caller_pid: Optional[int] = None,
) -> Dict[str, Any]:
    return call_verb(
        "ul.proc.spawn",
        {"command": command, "args": args or [], "spawn_mode": spawn_mode},
        caller_pid=caller_pid,
    )


def log_app(channel: str, message: str, *, level: str = "info", caller_pid: Optional[int] = None) -> Dict[str, Any]:
    return call_verb(
        "ul.log.write",
        {"channel": channel, "level": level, "message": message},
        caller_pid=caller_pid,
    )
