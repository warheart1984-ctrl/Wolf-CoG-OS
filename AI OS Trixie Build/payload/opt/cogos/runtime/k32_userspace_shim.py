"""
Userspace cog_k32 shim — kernel transport contract without a custom kernel module.

On Linux live ISO, this is the implementation behind cog_k32. A future kernel
module would validate signature + forward to this handler via netlink or device node.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from k32_router import K32ExecutionContext, K32RuntimeRouter

EPERM = -1
EINVAL = -22
EDEFER = -512


def _use_forward() -> bool:
    v = os.environ.get("COGOS_K32_FORWARD", "").strip().lower()
    if v in ("0", "false", "no"):
        return False
    if v in ("1", "true", "yes"):
        return True
    from k32_forward_protocol import DEFAULT_SOCK

    return DEFAULT_SOCK.exists()


def cog_k32(k_layer: int, payload: Dict[str, Any], *, profile_id: str = "operator") -> int:
    """
    Returns POSIX-style errno negative on failure, 0 on success.
    EDEFER when sentinel escalates (check pattern ledger).
    """
    if _use_forward():
        try:
            from k32_forward_daemon import client_call

            return client_call(k_layer, payload, profile_id=profile_id)
        except OSError:
            if os.environ.get("COGOS_K32_FORWARD", "").strip().lower() in ("1", "true", "yes"):
                return EINVAL

    router = K32RuntimeRouter()
    ctx = K32ExecutionContext(
        operator_present=profile_id == "operator" or os.environ.get("COGOS_OPERATOR", "") == "1",
        profile_id=profile_id,
        pid=os.getpid(),
    )
    out = router.handle_k32_call(k_layer, payload, ctx)
    status = out.get("status", "einval")
    if status == "ok":
        if out.get("decision") == "sentinel":
            return EDEFER
        return 0
    if status == "eperm":
        return EPERM
    return EINVAL
