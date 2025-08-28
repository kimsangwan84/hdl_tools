from typing import Dict, List, Set, Tuple

from ..errors import SpecError
from ..models import SubMode


def short_sm_name(name: str) -> str:
    import re
    return re.sub(r"^(normal_|scan_|ipdt_)", "", name, flags=re.I)


def build_bus_maps_for_mode(subs: List[SubMode]):
    sig_map: Dict[str, Dict[str, object]] = {}
    en_map: Dict[str, Set[int]] = {}
    per_sub = []
    for sm in subs:
        l_sig: Dict[str, Set[int]] = {}
        l_dir: Dict[str, str] = {}
        for c in sm.cells:
            base = c.base
            want = "output" if c.direction == "I" else "input"
            ent = sig_map.setdefault(base, {"dir": want, "idx": set()})
            if ent["dir"] != want:
                raise SpecError("U902", {"base": base, "mode": sm.mode})
            if c.base_idx is not None:
                ent["idx"].add(c.base_idx)
            e = l_sig.setdefault(base, set())
            if c.base_idx is not None:
                e.add(c.base_idx)
            l_dir.setdefault(base, want)
            if l_dir[base] != want:
                raise SpecError("U902", {"base": base, "mode": sm.mode})
            if c.enable:
                eb = c.enable.split("[")[0]
                s = en_map.setdefault(eb, set())
                if c.enable_idx is not None:
                    s.add(c.enable_idx)
        per_sub.append((sm, {b: (max(s) + 1 if s else 1) for b, s in l_sig.items()}, l_dir))
    sig_w = {b: (max(v["idx"]) + 1 if v["idx"] else 1) for b, v in sig_map.items()}
    sig_dir = {b: v["dir"] for b, v in sig_map.items()}
    en_w = {b: (max(v) + 1 if v else 1) for b, v in en_map.items()}
    return sig_w, sig_dir, en_w, per_sub


def build_bus_maps_global(modes):
    g_sig_w: Dict[str, int] = {}
    g_en_w: Dict[str, int] = {}
    g_dir: Dict[str, str] = {}
    for mode in ("normal", "scan", "ipdt"):
        sig_w, sig_dir, en_w, _ = build_bus_maps_for_mode(modes[mode])
        for b, w in sig_w.items():
            if b in g_dir and g_dir[b] != sig_dir[b]:
                raise SpecError("U902", {"base": b})
            g_sig_w[b] = max(g_sig_w.get(b, 0), w)
            g_dir[b] = sig_dir[b]
        for b, w in en_w.items():
            g_en_w[b] = max(g_en_w.get(b, 0), w)
    return g_sig_w, g_dir, g_en_w

