"""Enrich HAL/device inventory with K-threshold and K-ceiling bounds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root
from hal_device_schema import HALDevice, HALDevicePolicy


def _defaults() -> Dict[str, Dict[str, Any]]:
    path = cogos_root() / "config" / "hal_k32_defaults.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")).get("defaults", {})
    except Exception:
        return {}


def _infer_hal_class(device: Dict[str, Any]) -> str:
    cls = str(device.get("class", "")).lower()
    transport = str(device.get("transport", "")).lower()
    if cls == "removable" or "usb" in transport:
        return "sensory_input" if device.get("model", "").lower().find("camera") >= 0 else "storage_block"
    if cls == "network" or device.get("name", "").startswith(("eth", "wlan", "en", "wl")):
        return "network_iface"
    if cls == "display" or "drm" in transport:
        return "display_gpu"
    if "audio" in cls or "snd" in transport:
        return "audio"
    if cls == "payload":
        return "payload_volume"
    if cls == "fixed" or cls == "system":
        return "storage_block"
    return "generic_pci"


def policy_for_device(device: Dict[str, Any], rule: Optional[Dict[str, Any]] = None) -> HALDevicePolicy:
    defaults = _defaults()
    hal_class = (rule or {}).get("hal_class") or _infer_hal_class(device)
    base = defaults.get(hal_class, defaults.get("generic_pci", {}))
    k_threshold = (rule or {}).get("k_threshold", base.get("k_threshold"))
    k_ceiling = (rule or {}).get("k_ceiling", base.get("k_ceiling"))
    return HALDevicePolicy(
        hal_class=hal_class,
        k_threshold=int(k_threshold) if k_threshold is not None else None,
        k_ceiling=int(k_ceiling) if k_ceiling is not None else None,
    )


def enrich_inventory_devices(devices: List[Dict[str, Any]], rules: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    rules = rules or []
    out = []
    for dev in devices:
        rule = None
        for r in rules:
            match = r.get("match", {})
            ok = True
            for key, expected in match.items():
                if str(dev.get(key, "")).lower() != str(expected).lower():
                    ok = False
                    break
            if ok:
                rule = r
                break
        policy = policy_for_device(dev, rule)
        row = {**dev, "hal_class": policy.hal_class, "k_threshold": policy.k_threshold, "k_ceiling": policy.k_ceiling}
        out.append(row)
    return out


def list_hal_devices() -> List[HALDevice]:
    try:
        from device_storage_manager import DeviceStorageManager
        from driver_policy import DriverPolicyEngine

        inv = DeviceStorageManager().inventory()
        rules = DriverPolicyEngine()._load_policy().get("rules", [])
        enriched = enrich_inventory_devices(inv.get("devices", []), rules)
    except Exception:
        enriched = []
    devices: List[HALDevice] = []
    for row in enriched:
        policy = HALDevicePolicy(
            hal_class=row.get("hal_class", "generic_pci"),
            k_threshold=row.get("k_threshold"),
            k_ceiling=row.get("k_ceiling"),
        )
        devices.append(HALDevice(id=str(row.get("path") or row.get("name")), policy=policy, raw=row))
    return devices


def get_device(device_id: str) -> Optional[HALDevice]:
    for dev in list_hal_devices():
        if dev.id == device_id or dev.raw and dev.raw.get("name") == device_id:
            return dev
    return None
