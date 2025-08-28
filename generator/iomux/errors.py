from typing import Any, Dict, Optional

EID = {
    "F101":"Excel merge/markers not found (Pin Group/Pin Name/PAD type rows missing)",
    "F102":"Mode/Submode header not found",
    "F103":"Pin Name duplicated",
    "F104":"Blank cell in mode/sub_mode header (STRICT)",
    "F105":"Non-contiguous merge for mode/sub_mode (STRICT)",
    "F106":"§3.2 control columns violation (order/value/placement)",
    "P201":"PAD type capability not provided (-pad_type)",
    "P202":"I-only PAD has O/IO direction",
    "P203":"Forbidden PAD must not be MUXed (OM/XIN/XOUT/PORn)",
    "O301":"OM value out of range",
    "O302":"OM value duplicated across submodes",
    "O304":"Conflicting OM definitions for same submode",
    "C402":"Enable base mismatch with signal (e.g., 'TDO' must pair with 'TDO_oe(n)')",
    "C403":"OE must be '<signal>_oe' (AH) or '<signal>_oen'/'<signal>_oe_n' (AL)",
    "S701":"-mux_exclude but Excel defines mapping",
    "U901":"Unexpected error",
    "U902":"Mixed directions for same signal base",
    "U903":"Inconsistent bus width across submodes for same signal",
    "B101":"Bus indices are not contiguous (must be 0..W-1)",
    "B102":"Mixed scalar and indexed forms for the same base signal",
    "B103":"Duplicate index for the same base within a single submode",
}


class SpecError(Exception):
    def __init__(self, eid: str, ctx: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{eid}] {EID.get(eid, eid)}")
        self.eid = eid
        self.ctx = ctx or {}

    def pretty(self) -> str:
        c = " ".join(f"{k}={v}" for k, v in self.ctx.items())
        return f"[{self.eid}] {EID.get(self.eid, self.eid)}" + (f" | {c}" if c else "")

