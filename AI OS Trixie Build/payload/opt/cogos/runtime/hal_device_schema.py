"""HAL device K-threshold / K-ceiling schema (devices do not own K-layers)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ul.ul_intent_schema import KLayer, ULIntent


@dataclass
class HALDevicePolicy:
    hal_class: str
    k_threshold: Optional[int] = None
    k_ceiling: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hal_class": self.hal_class,
            "k_threshold": self.k_threshold,
            "k_ceiling": self.k_ceiling,
        }


@dataclass
class HALDevice:
    id: str
    policy: HALDevicePolicy
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "policy": self.policy.to_dict(), "raw": self.raw or {}}


def can_device_handle_intent(device: HALDevice, intent: ULIntent) -> bool:
    k = intent.k_layer.value
    if device.policy.k_ceiling is not None and k > device.policy.k_ceiling:
        return False
    return True


def requires_operator_for_device(device: HALDevice, intent: ULIntent) -> bool:
    if device.policy.k_threshold is None:
        return False
    return intent.k_layer.value >= device.policy.k_threshold
