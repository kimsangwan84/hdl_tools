from typing import Dict, Set

from .errors import SpecError
from .models import ExcelModel
from .utils import is_active_low_oe, strip_idx


def validate(model: ExcelModel):
    def check(mode, subs, lo, hi):
        seen: Set[int] = set()
        for sm in subs:
            for v in sm.om_values:
                if not (lo <= v <= hi):
                    raise SpecError("O301", {"mode": mode, "om": v})
                if v in seen:
                    raise SpecError("O302", {"mode": mode, "om": v})
                seen.add(v)

    check("normal", model.modes["normal"], 0, 31)
    check("scan", model.modes["scan"], 32, 47)
    check("ipdt", model.modes["ipdt"], 48, 63)

    for _, subs in model.modes.items():
        for sm in subs:
            for c in sm.cells:
                if c.enable:
                    def split_oe(name: str):
                        n = strip_idx(name)
                        nl = n.lower()
                        for suf in ("_oen_n", "_oe_n", "_oen", "_oe"):
                            if nl.endswith(suf):
                                return n[: -len(suf)], suf
                        return None, None

                    base_sig = strip_idx(c.base)
                    en_base, suf = split_oe(c.enable)
                    if suf is None:
                        raise SpecError("C403", {"signal": c.base, "enable": c.enable, "submode": sm.name})
                    if (en_base or "").strip().lower() != base_sig.strip().lower():
                        raise SpecError("C402", {"signal": c.base, "enable": c.enable, "submode": sm.name})

    for mode, subs in model.modes.items():
        for sm in subs:
            seen_pairs = set()
            for c in sm.cells:
                if c.base_idx is not None:
                    key = (c.base, c.base_idx)
                    if key in seen_pairs:
                        raise SpecError("B103", {"mode": mode, "submode": sm.name, "base": c.base, "idx": c.base_idx})
                    seen_pairs.add(key)

        idx_map: Dict[str, set] = {}
        has_scalar: Dict[str, bool] = {}
        for sm in subs:
            for c in sm.cells:
                b = c.base
                if c.base_idx is None:
                    has_scalar[b] = True
                else:
                    idx_map.setdefault(b, set()).add(c.base_idx)
        for b, s in idx_map.items():
            if has_scalar.get(b, False):
                raise SpecError("B102", {"mode": mode, "base": b})
            if s:
                mx = max(s)
                expect = set(range(0, mx + 1))
                if s != expect:
                    raise SpecError("B101", {"mode": mode, "base": b, "indices": sorted(s), "expect": f"0..{mx}"})

    g_idx: Dict[str, set] = {}
    g_scalar: Dict[str, bool] = {}
    for subs in model.modes.values():
        for sm in subs:
            for c in sm.cells:
                b = c.base
                if c.base_idx is None:
                    g_scalar[b] = True
                else:
                    g_idx.setdefault(b, set()).add(c.base_idx)
    for b, s in g_idx.items():
        if g_scalar.get(b, False):
            raise SpecError("B102", {"mode": "*", "base": b})
        if s:
            mx = max(s)
            expect = set(range(0, mx + 1))
            if s != expect:
                raise SpecError("B101", {"mode": "*", "base": b, "indices": sorted(s), "expect": f"0..{mx}"})

