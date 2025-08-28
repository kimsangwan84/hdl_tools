import re
from typing import Any, Dict, List, Optional, Set, Tuple


def norm(x: Any) -> str:
    return "" if x is None else str(x).strip()


def nlow(x: Any) -> str:
    return norm(x).lower()


def sv_id(s: str) -> str:
    return "".join(ch if (ch.isalnum() or ch in "_$[]") else "_" for ch in s)


def strip_idx(s: str) -> str:
    return re.sub(r"\[.*\]$", "", s or "")


def padtype_key(s: Any) -> str:
    t = norm(s)
    return re.split(r"[_\s(]", t, 1)[0] if t else ""


def pad_orientation(s: Any) -> str:
    t = norm(s)
    m = re.search(r"_([HV])\b", t)
    return (m.group(1) if m else "V")


def classify_mode(x: Any) -> Optional[str]:
    t = nlow(x)
    if t.startswith("normal"):
        return "normal"
    if t.startswith("scan"):
        return "scan"
    if t.startswith("ipdt"):
        return "ipdt"
    return None


# io_test 서브모드 이름 정규화
IO_TEST_CANON = "iotest"


def canon_submode_name(s: str) -> str:
    t = (s or "").lower().strip()
    # 비영숫자 모두 제거하여 비교 (공백/하이픈/언더스코어 차이 허용)
    t = re.sub(r"[^a-z0-9]", "", t)
    return t


def is_io_test_name(s: str) -> bool:
    return canon_submode_name(s) == IO_TEST_CANON


# 정렬/포맷 유틸
def idx_r(i: int, W: int) -> str:
    return f"[{i:>{max(1, W)}}]"


def align_bracket_num(txt: str, width: int) -> str:
    if width <= 0:
        return ""
    s = (txt or "").strip()
    if not s:
        return " " * width
    if s[0] == "[" and s[-1] == "]":
        return "[" + s[1:-1].rjust(width - 2) + "]"
    return s.rjust(width)


def align_ports(entries: List[Dict[str, str]]) -> Tuple[List[str], int]:
    if not entries:
        return [], 0
    DIR_W = max((len(e["direction"]) for e in entries if not e.get("iface")), default=0)
    TYP_W = max((len(e["type"]) for e in entries if not e.get("iface")), default=0)
    IF_W = max((len(e["iface"]) for e in entries if e.get("iface")), default=0)
    LEFT_W = max(IF_W, (DIR_W + (1 if TYP_W > 0 else 0) + TYP_W))
    BITS_W = max(len(e["bits"]) for e in entries) if entries else 0
    ARR_W = max(len(e["array"]) for e in entries) if entries else 0
    NAME_W = max(len(e["name"]) for e in entries) if entries else 0
    lines = []
    for i, e in enumerate(entries):
        if e.get("iface"):
            left = e["iface"].ljust(LEFT_W)
        else:
            left = (
                e["direction"].ljust(DIR_W)
                + (" " if TYP_W > 0 else "")
                + e["type"].ljust(LEFT_W - DIR_W - (1 if TYP_W > 0 else 0))
            )
        bits = align_bracket_num(e["bits"], BITS_W)
        arr = (" " + align_bracket_num(e["array"], ARR_W)) if e["array"] else " " * (ARR_W + 1 if ARR_W > 0 else 1)
        comma = "," if i < len(entries) - 1 else ""
        lines.append(f"  {left}  {bits}  {e['name']:<{NAME_W}}{arr}{comma}")
    return lines, 2


def align_decls(decls: List[Tuple[str, str, str]]) -> List[str]:
    if not decls:
        return []
    T_W = max(len(t) for t, _, _ in decls)
    B_W = max(len(b) for _, b, _ in decls)
    N_W = max(len(n) for _, _, n in decls)
    return [f"  {t.ljust(T_W)}  {align_bracket_num(b, B_W)}  {n};" for t, b, n in decls]


def align_assign_pairs(pairs: List[Tuple[str, str]]) -> List[str]:
    if not pairs:
        return []
    L_W = max(len(lhs) for lhs, _ in pairs)
    return [f"  assign {lhs.ljust(L_W)} = {rhs};" for lhs, rhs in pairs]


def align_instance(conns: List[Tuple[str, str]]) -> List[str]:
    PW = max(len(k) for k, _ in conns)
    VW = max(len(v) for _, v in conns)
    out = ["  ("]
    for i, (k, v) in enumerate(conns):
        comma = "," if i < len(conns) - 1 else ""
        out.append(f"    {k.ljust(PW)} ( {v.ljust(VW)} ){comma}")
    out.append("  );")
    return out


def fmt_if(ifname: str, idx: int, field: str, idxW: int, fieldW: int) -> str:
    return f"{ifname}{idx_r(idx, idxW)}.{field.ljust(fieldW)}"


def fmt_vec(name: str, idx: int, idxW: int) -> str:
    return f"{name}{idx_r(idx, idxW)}"


# 유효성/네이밍
def is_valid_oe_for_base(base: str, en: str) -> bool:
    b = strip_idx(base).lower()
    e = strip_idx(en).lower()
    return e in (f"{b}_oe", f"{b}_oen", f"{b}_oe_n", f"{b}_oen_n")


def is_active_low_oe(en: str) -> bool:
    e = strip_idx(en).lower()
    return e.endswith("_oen") or e.endswith("_oe_n") or e.endswith("_oen_n")


def is_oe_name(name: str) -> bool:
    e = strip_idx(name).lower()
    return e.endswith("_oe") or e.endswith("_oen") or e.endswith("_oe_n") or e.endswith("_oen_n")


def is_gpio_like(s: str) -> bool:
    return strip_idx(s).lower().endswith("gpio")


GPIO_BOOL = ("oen", "i", "pe_pu", "ps_pd", "st", "ie")


def gpio_like_port_entries(base: str, width: int) -> List[Dict[str, str]]:
    b = sv_id(base)
    ent = []
    for nm in GPIO_BOOL:
        ent.append(
            {
                "direction": "input",
                "type": "logic",
                "bits": ("" if width <= 1 else f"[{width-1}:0]"),
                "name": f"{b}_{nm}",
                "array": "",
                "iface": "",
            }
        )
    ent.append(
        {
            "direction": "input",
            "type": "logic",
            "bits": ("" if width <= 1 else f"[{width-1}:0]") + "[3:0]",
            "name": f"{b}_ds",
            "array": "",
            "iface": "",
        }
    )
    ent.append(
        {
            "direction": "output",
            "type": "logic",
            "bits": ("" if width <= 1 else f"[{width-1}:0]"),
            "name": f"{b}_c",
            "array": "",
            "iface": "",
        }
    )
    return ent


def en_names_for_base(base: str, en_w_map: Dict[str, int]) -> List[str]:
    out: List[str] = []
    for eb in en_w_map.keys():
        if is_valid_oe_for_base(base, eb):
            out.append(eb)
    return sorted(out)

