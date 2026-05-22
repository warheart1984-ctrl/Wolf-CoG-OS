"""
mesh_transport.py — file-drop transport for family mesh across 2–3 physical boxes.

No network stack required: export outbox JSON to a shared folder or USB,
copy to peer `mesh_drop/inbox/`, run `import-drop` on each receiver.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root
from mesh_identity import LAMBDA_SIGIL_SHA256, MeshIdentityStore, device_sigil, family_mesh_id
from reasoning_exchange import ReasoningExchangeNode


def _drop_root(custom: Optional[Path] = None) -> Path:
    if custom:
        return Path(custom)
    env = __import__("os").environ.get("COGOS_MESH_DROP", "").strip()
    if env:
        return Path(env)
    root = cogos_root()
    for candidate in (
        Path("/mnt/cogosdata/mesh_drop"),
        root / "memory" / "mesh" / "drop",
    ):
        if candidate.exists() or candidate.parent.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    path = root / "memory" / "mesh" / "drop"
    path.mkdir(parents=True, exist_ok=True)
    return path


def peer_identity_bundle(device_id: str) -> Dict[str, Any]:
    sigil = device_sigil(device_id)
    return {
        "device_id": device_id,
        "device_sigil": sigil,
        "family_mesh_id": family_mesh_id(sigil),
        "lambda_anchor": LAMBDA_SIGIL_SHA256,
        "hostname": device_id,
    }


def export_identity_bundle(output: Optional[Path] = None) -> Dict[str, Any]:
    bundle = MeshIdentityStore().export_exchange_bundle()
    out = output or (_drop_root() / "identity" / f"{bundle['device_id']}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(out), "bundle": bundle}


def export_peer_identity_bundle(device_id: str, output: Path) -> Dict[str, Any]:
    bundle = peer_identity_bundle(device_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(output), "bundle": bundle}


def import_peer_bundles(directory: Optional[Path] = None) -> Dict[str, Any]:
    node = ReasoningExchangeNode()
    drop = directory or (_drop_root() / "identity")
    trusted: List[Dict[str, Any]] = []
    if not drop.is_dir():
        return {"ok": False, "reason": f"no identity dir: {drop}"}
    for path in sorted(drop.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            trusted.append({"path": str(path), "ok": False, "error": str(exc)})
            continue
        device_id = str(data.get("device_id", path.stem))
        sigil = str(data.get("device_sigil", ""))
        row = node.trust_peer(device_id, sigil or None)
        trusted.append({"ok": True, "path": str(path), **row})
    return {"ok": True, "trusted": trusted, "count": len(trusted)}


def export_outbox_drop(*, drop_root: Optional[Path] = None, limit: int = 50) -> Dict[str, Any]:
    node = ReasoningExchangeNode()
    out_dir = (drop_root or _drop_root()) / "outbox"
    out_dir.mkdir(parents=True, exist_ok=True)
    exported: List[str] = []
    if not node.outbox.exists():
        return {"ok": True, "exported": 0, "paths": [], "drop": str(out_dir)}
    lines = node.outbox.read_text(encoding="utf-8").strip().splitlines()[-limit:]
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = f"{row.get('from_sigil', 'unknown')[:8]}_{row.get('message_id', 'msg')}.json"
        dest = out_dir / name
        dest.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
        exported.append(str(dest))
    return {"ok": True, "exported": len(exported), "paths": exported, "drop": str(out_dir)}


def import_inbox_drop(*, drop_root: Optional[Path] = None, execute_creative: bool = True) -> Dict[str, Any]:
    node = ReasoningExchangeNode()
    inbox_dir = (drop_root or _drop_root()) / "inbox"
    results: List[Dict[str, Any]] = []
    if not inbox_dir.is_dir():
        return {"ok": False, "reason": f"no inbox dir: {inbox_dir}"}
    for path in sorted(inbox_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            results.append({"path": str(path), "ok": False, "error": str(exc)})
            continue
        result = node.receive(raw)
        row = {
            "path": str(path),
            "admitted": result.admitted,
            "kind": raw.get("kind"),
            "reason": result.message.reason,
        }
        if result.admitted and execute_creative and raw.get("kind") == "creative_handoff":
            row["creative"] = _execute_creative_handoff(raw.get("payload", {}))
        results.append(row)
        archive = inbox_dir / "processed" / path.name
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(archive))
    admitted = sum(1 for r in results if r.get("admitted"))
    return {
        "ok": admitted > 0 or len(results) == 0,
        "imported": len(results),
        "admitted": admitted,
        "results": results,
        "inbox": str(inbox_dir),
    }


def _execute_creative_handoff(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from creative_modules import run_creative

        lane = str(payload.get("lane", "story_forge"))
        verb = str(payload.get("verb", "draft"))
        prompt = str(payload.get("prompt", payload.get("note", "mesh handoff")))
        return run_creative(lane=lane, verb=verb, prompt=prompt, profile_id="operator")
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


def physical_roundtrip_proof(*, peers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Simulates physical mesh on one host using drop folders per peer role.
    For true 2–3 box proof, use export/import between machines instead.
    """
    peers = peers or ["family-laptop", "family-desktop", "family-mini"]
    node = ReasoningExchangeNode()
    drop = _drop_root() / "physical_proof"
    if drop.exists():
        shutil.rmtree(drop, ignore_errors=True)
    drop.mkdir(parents=True, exist_ok=True)

    for device_id in peers:
        export_peer_identity_bundle(device_id, drop / "identity" / f"{device_id}.json")
    import_peer_bundles(drop / "identity")

    admitted = 0
    exchanges: List[Dict[str, Any]] = []
    for device_id in peers:
        sigil = device_sigil(device_id)
        for kind in ("health_ping", "reasoning_proposal", "creative_handoff"):
            payload = {"from": device_id, "note": f"physical-{kind}"}
            if kind == "creative_handoff":
                payload.update({"lane": "story_forge", "verb": "draft", "prompt": "family mesh"})
            raw = {
                "message_id": f"phys-{device_id}-{kind}",
                "from_sigil": sigil,
                "to_sigil": node.identity.family_mesh_id,
                "kind": kind,
                "payload": payload,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            inbox_file = drop / "inbox" / f"{device_id}_{kind}.json"
            inbox_file.parent.mkdir(parents=True, exist_ok=True)
            inbox_file.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")

    imported = import_inbox_drop(drop_root=drop, execute_creative=True)
    admitted = imported.get("admitted", 0)
    report = {
        "ok": bool(imported.get("ok")) and admitted >= len(peers),
        "mode": "file_drop_physical_proof",
        "peers": peers,
        "drop": str(drop),
        "imported": imported,
        "note": "Copy drop/ between boxes: identity/ → trust, inbox/ → import-drop",
    }
    log_path = cogos_root() / "memory" / "mesh" / "physical_proof_report.json"
    log_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
