"""op_code → UL intent mapping for cog_k32."""

from __future__ import annotations

from typing import Dict, List, Tuple

from ul.ul_intent_schema import KLayer, KProfilePolicy

# (lo, hi, k_layer, policy, name_prefix)
OP_TABLE: List[Tuple[int, int, KLayer, KProfilePolicy, str]] = [
    # Class P — perception / readiness (K1–K8)
    (0x0001, 0x000F, KLayer.K1, KProfilePolicy.PRIMARY_WINS, "baseline"),
    (0x0010, 0x001F, KLayer.K2, KProfilePolicy.PRIMARY_WINS, "attention"),
    (0x0020, 0x002F, KLayer.K3, KProfilePolicy.PRIMARY_WINS, "observe"),
    (0x0030, 0x003F, KLayer.K4, KProfilePolicy.PRIMARY_WINS, "proximity"),
    (0x0040, 0x004F, KLayer.K5, KProfilePolicy.PRIMARY_WINS, "recognition"),
    (0x0050, 0x005F, KLayer.K6, KProfilePolicy.PRIMARY_WINS, "readiness"),
    (0x0060, 0x006F, KLayer.K7, KProfilePolicy.PRIMARY_WINS, "resistance"),
    (0x0070, 0x007F, KLayer.K8, KProfilePolicy.PRIMARY_WINS, "permission"),
    # Class R — relation / orientation (K9–K16)
    (0x0080, 0x008F, KLayer.K9, KProfilePolicy.HIGHEST_CLASS, "anchor"),
    (0x0090, 0x009F, KLayer.K10, KProfilePolicy.HIGHEST_CLASS, "calibrate"),
    (0x0100, 0x010F, KLayer.K11, KProfilePolicy.HIGHEST_CLASS, "attest"),
    (0x0110, 0x011F, KLayer.K12, KProfilePolicy.HIGHEST_CLASS, "prioritize"),
    (0x0120, 0x012F, KLayer.K13, KProfilePolicy.HIGHEST_CLASS, "fixate"),
    (0x0130, 0x013F, KLayer.K14, KProfilePolicy.HIGHEST_CLASS, "context"),
    (0x0140, 0x014F, KLayer.K15, KProfilePolicy.HIGHEST_CLASS, "align_hint"),
    (0x0150, 0x015F, KLayer.K16, KProfilePolicy.HIGHEST_CLASS, "attune"),
    # Class D — distortion / alignment (K17–K24)
    (0x0200, 0x020F, KLayer.K17, KProfilePolicy.HIGHEST_CLASS, "saturate"),
    (0x0210, 0x021F, KLayer.K20, KProfilePolicy.HIGHEST_CLASS, "throttle"),
    (0x0220, 0x022F, KLayer.K21, KProfilePolicy.HIGHEST_CLASS, "route"),
    (0x0230, 0x023F, KLayer.K24, KProfilePolicy.HIGHEST_CLASS, "align"),
    # K25 sentinel
    (0x0300, 0x030F, KLayer.K25, KProfilePolicy.EXPLICIT, "sentinel"),
    # Class A — agency (K26–K32)
    (0x0400, 0x040F, KLayer.K26, KProfilePolicy.EXPLICIT, "leverage"),
    (0x0410, 0x041F, KLayer.K28, KProfilePolicy.EXPLICIT, "memory"),
    (0x0420, 0x042F, KLayer.K29, KProfilePolicy.EXPLICIT, "identity"),
    (0x0500, 0x050F, KLayer.K32, KProfilePolicy.EXPLICIT, "agency"),
]

# Legacy aliases (smoke / CLI defaults)
OP_ALIASES = {
    0x0001: (KLayer.K3, "observe"),
    0x0501: (KLayer.K32, "agency"),
}


class UnknownOpCode(Exception):
    pass


def resolve_op(op_code: int) -> Dict[str, object]:
    if op_code in OP_ALIASES:
        k_layer, prefix = OP_ALIASES[op_code]
        return {
            "k_layer": k_layer,
            "k_profile_policy": KProfilePolicy.PRIMARY_WINS if k_layer.value <= 8 else KProfilePolicy.EXPLICIT,
            "name_prefix": prefix,
        }
    for lo, hi, k_layer, policy, prefix in OP_TABLE:
        if lo <= op_code <= hi:
            return {
                "k_layer": k_layer,
                "k_profile_policy": policy,
                "name_prefix": prefix,
            }
    raise UnknownOpCode(f"op_code 0x{op_code:04X} has no registered mapping")
