"""UL intent schema — K32 semantic plane fields."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Set


class KLayer(IntEnum):
    K1 = 1
    K2 = 2
    K3 = 3
    K4 = 4
    K5 = 5
    K6 = 6
    K7 = 7
    K8 = 8
    K9 = 9
    K10 = 10
    K11 = 11
    K12 = 12
    K13 = 13
    K14 = 14
    K15 = 15
    K16 = 16
    K17 = 17
    K18 = 18
    K19 = 19
    K20 = 20
    K21 = 21
    K22 = 22
    K23 = 23
    K24 = 24
    K25 = 25
    K26 = 26
    K27 = 27
    K28 = 28
    K29 = 29
    K30 = 30
    K31 = 31
    K32 = 32


class KProfilePolicy(str, Enum):
    HIGHEST_CLASS = "highest_class"
    PRIMARY_WINS = "primary_wins"
    EXPLICIT = "explicit"


CLASS_P: Set[int] = set(range(1, 9))
CLASS_R: Set[int] = set(range(9, 17))
CLASS_D: Set[int] = set(range(17, 26))
CLASS_A: Set[int] = set(range(26, 33))

CLASS_ORDER = {"P": 0, "R": 1, "D": 2, "A": 3}


def k_class_of(k: int) -> str:
    if k in CLASS_P:
        return "P"
    if k in CLASS_R:
        return "R"
    if k in CLASS_D:
        return "D"
    if k in CLASS_A:
        return "A"
    raise ValueError(f"Invalid k_layer: {k}")


def effective_k_class(intent: "ULIntent") -> str:
    """Resolve governing class after k_profile_policy."""
    primary = k_class_of(intent.k_layer.value)
    if not intent.k_profile:
        return primary
    if intent.k_profile_policy == KProfilePolicy.PRIMARY_WINS:
        return primary
    profile_classes = {k_class_of(k.value) for k in intent.k_profile}
    if intent.k_profile_policy == KProfilePolicy.EXPLICIT:
        all_classes = profile_classes | {primary}
        if len(all_classes) > 1:
            raise ValueError(f"Explicit policy: intent {intent.name} spans classes {all_classes}")
        return primary
    # highest_class
    best = primary
    for cls in profile_classes:
        if CLASS_ORDER[cls] > CLASS_ORDER[best]:
            best = cls
    return best


class ULIntent:
    def __init__(
        self,
        name: str,
        k_layer: KLayer,
        k_profile: Optional[List[KLayer]] = None,
        k_profile_policy: KProfilePolicy = KProfilePolicy.HIGHEST_CLASS,
        **extra: Any,
    ):
        self.name = name
        self.k_layer = k_layer
        self.k_profile = k_profile or []
        self.k_profile_policy = k_profile_policy
        self.extra = extra
        self._validate_k_profile()

    def _validate_k_profile(self) -> None:
        if not self.k_profile:
            return
        if self.k_profile_policy == KProfilePolicy.PRIMARY_WINS:
            return
        if self.k_profile_policy == KProfilePolicy.EXPLICIT:
            primary_class = k_class_of(self.k_layer.value)
            profile_classes = {k_class_of(k.value) for k in self.k_profile}
            if len(profile_classes | {primary_class}) > 1:
                raise ValueError(
                    f"Explicit policy: intent {self.name} spans classes "
                    f"{profile_classes | {primary_class}}"
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "k_layer": self.k_layer.value,
            "k_profile": [k.value for k in self.k_profile],
            "k_profile_policy": self.k_profile_policy.value,
            "effective_class": effective_k_class(self),
            **self.extra,
        }
