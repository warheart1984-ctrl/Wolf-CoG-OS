"""K32 forward transport — Unix socket protocol (kernel chardev / netlink userspace peer)."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any, Dict, Tuple

# Matches kernel/cog_k32_chardev_stub.c ioctl numbers (out-of-tree module contract).
COG_K32_IOCTL_CALL = 0xC0320001
COG_K32_IOCTL_STATUS = 0xC0320002

DEFAULT_SOCK = Path("/run/cogos/k32.sock")
HDR = struct.Struct("!II")  # k_layer, payload_len


def encode_request(
    k_layer: int,
    payload: Dict[str, Any],
    *,
    profile_id: str = "operator",
    ioctl: int = COG_K32_IOCTL_CALL,
) -> bytes:
    body = json.dumps(
        {"payload": payload, "profile_id": profile_id, "ioctl": ioctl},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return HDR.pack(int(k_layer), len(body)) + body


def decode_request(data: bytes) -> Tuple[int, Dict[str, Any], str, int]:
    if len(data) < HDR.size:
        raise ValueError("truncated k32 forward header")
    k_layer, plen = HDR.unpack_from(data)
    body = data[HDR.size : HDR.size + plen]
    meta = json.loads(body.decode("utf-8"))
    return k_layer, dict(meta.get("payload") or {}), str(meta.get("profile_id") or "operator"), int(
        meta.get("ioctl") or COG_K32_IOCTL_CALL
    )


def encode_response(returncode: int, detail: Dict[str, Any] | None = None) -> bytes:
    body = json.dumps({"rc": int(returncode), "detail": detail or {}}, separators=(",", ":")).encode("utf-8")
    return HDR.pack(0, len(body)) + body


def decode_response(data: bytes) -> Tuple[int, Dict[str, Any]]:
    if len(data) < HDR.size:
        raise ValueError("truncated k32 forward response")
    _, plen = HDR.unpack_from(data)
    meta = json.loads(data[HDR.size : HDR.size + plen].decode("utf-8"))
    return int(meta.get("rc", -22)), dict(meta.get("detail") or {})
