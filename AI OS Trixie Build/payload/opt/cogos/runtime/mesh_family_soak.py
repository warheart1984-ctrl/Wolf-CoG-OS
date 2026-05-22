"""Mesh family soak — simulate 2–3 device family mesh (Phase C)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from mesh_identity import device_sigil
from reasoning_exchange import ReasoningExchangeNode


PEERS = [
    {"device_id": "soak-family-laptop", "role": "laptop"},
    {"device_id": "soak-family-desktop", "role": "desktop"},
    {"device_id": "soak-family-mini", "role": "mini"},
]

KINDS = ["health_ping", "reasoning_proposal", "creative_handoff", "operator_note"]


def run_soak(*, rounds: int = 1) -> Dict[str, Any]:
    node = ReasoningExchangeNode()
    local = node.identity
    peer_sigils: List[Dict[str, str]] = []
    for peer in PEERS:
        sigil = device_sigil(peer["device_id"])
        node.trust_peer(peer["device_id"], sigil)
        peer_sigils.append({**peer, "device_sigil": sigil})

    admitted = 0
    rejected = 0
    exchanges: List[Dict[str, Any]] = []

    for r in range(rounds):
        for i, sender in enumerate(peer_sigils):
            for kind in KINDS:
                payload = {
                    "round": r,
                    "from_role": sender["role"],
                    "to_mesh": local.family_mesh_id,
                    "note": f"soak-{kind}",
                }
                if kind == "creative_handoff":
                    payload["lane"] = "story_forge"
                    payload["artifact_kind"] = "story_draft"
                raw = {
                    "message_id": f"soak-{r}-{i}-{kind}",
                    "from_sigil": sender["device_sigil"],
                    "to_sigil": local.family_mesh_id,
                    "kind": kind,
                    "payload": payload,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                result = node.receive(raw)
                row = {
                    "kind": kind,
                    "from": sender["role"],
                    "admitted": result.admitted,
                    "reason": result.message.reason,
                }
                exchanges.append(row)
                if result.admitted:
                    admitted += 1
                else:
                    rejected += 1

    expected_good = len(PEERS) * len(KINDS) * rounds

    bad_bypass = node.receive({
        "message_id": "soak-bad-bypass",
        "from_sigil": peer_sigils[0]["device_sigil"],
        "to_sigil": local.family_mesh_id,
        "kind": "reasoning_proposal",
        "payload": {"bypass_governance": True},
    })
    stranger_sigil = device_sigil("soak-untrusted-stranger")
    bad_stranger = node.receive({
        "message_id": "soak-bad-stranger",
        "from_sigil": stranger_sigil,
        "to_sigil": local.family_mesh_id,
        "kind": "health_ping",
        "payload": {"note": "untrusted"},
    })

    report = {
        "ok": admitted >= expected_good and not bad_bypass.admitted and not bad_stranger.admitted,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "peers": len(peer_sigils),
        "rounds": rounds,
        "admitted": admitted,
        "rejected": rejected,
        "expected_good": expected_good,
        "governance_bypass_blocked": not bad_bypass.admitted,
        "untrusted_peer_blocked": not bad_stranger.admitted,
        "trusted_count": node.list_recent().get("trusted_count", 0),
        "sample": exchanges[:8],
    }
    log_path = node.root / "memory" / "mesh" / "soak_report.json"
    log_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
