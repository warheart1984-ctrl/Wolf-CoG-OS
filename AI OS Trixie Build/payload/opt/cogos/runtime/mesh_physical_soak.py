"""Physical family mesh proof — file-drop transport (2–3 boxes via USB/shared folder)."""

from __future__ import annotations

from mesh_transport import physical_roundtrip_proof


def run_physical_soak(*, peers: list | None = None) -> dict:
    return physical_roundtrip_proof(peers=peers)
