import re
from typing import Any, Dict, List, Optional, Set, Tuple

from .errors import SpecError
from .models import ExcelModel, PadRow, SigCell, SubMode
from .utils import (
    classify_mode,
    nlow,
    norm,
    pad_orientation,
    padtype_key,
    strip_idx,
)


KW_PG = "Pin Group"
KW_PN = "Pin Name"
KW_PT = "PAD type"
FORBIDDEN_BASES = {"OM", "PORN", "XIN", "XOUT"}
NT_IN_RE = re.compile(r"(?i)(?:nt|nand(?:_tree)?)_in\[(\d+)\]")


def load_grid(ws):
    R, C = ws.max_row, ws.max_column
    g = [[ws.cell(r, c).value for c in range(1, C + 1)] for r in range(1, R + 1)]
    for rng in ws.merged_cells.ranges:
        r0, c0, r1, c1 = rng.min_row, rng.min_col, rng.max_row, rng.max_col
        v = ws.cell(r0, c0).value
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                g[r - 1][c - 1] = v
    return g


def find_header_row(grid) -> Tuple[int, Dict[str, int]]:
    want = [nlow(KW_PG), nlow(KW_PN), nlow(KW_PT)]
    for r, row in enumerate(grid):
        idx: Dict[str, List[int]] = {}
        for c, v in enumerate(row):
            nv = nlow(v)
            if nv:
                idx.setdefault(nv, []).append(c)
        if all(w in idx for w in want):
            return r, {KW_PG: idx[want[0]][0], KW_PN: idx[want[1]][0], KW_PT: idx[want[2]][0]}
    raise SpecError("F101")


def data_start_row(grid, r_hdr, cmap):
    cn = cmap["Pin Name"]
    ct = cmap["PAD type"]
    cg = cmap["Pin Group"]
    r = r_hdr + 1

    def is_header_like(val):
        v = nlow(val)
        return v in ("pin name", "pad type", "pin group") or v == ""

    while r < len(grid):
        row = grid[r]
        v_cn = row[cn] if cn < len(row) else None
        v_ct = row[ct] if ct < len(row) else None
        v_cg = row[cg] if cg < len(row) else None
        if is_header_like(v_cn) or is_header_like(v_ct) or is_header_like(v_cg):
            r += 1
            continue
        break
    return r


def parse_om_values(s: Any) -> List[int]:
    out: List[int] = []
    text = norm(s)
    if not text:
        return out
    text = re.sub(r"(?i)\bom\s*=\s*", "", text)
    parts = [p.strip() for p in text.split(",") if p.strip()]

    def nl(t: str) -> str:
        t = t.strip()
        t = re.sub(r"(?i)\b\d+\s*'\s*h\s*([0-9a-f]+)\b", r"0x\1", t)
        t = re.sub(r"(?i)\b\d+\s*'\s*d\s*([0-9]+)\b", r"\1", t)
        if re.fullmatch(r"[0-9A-Fa-f]+", t) and re.search(r"[A-Fa-f]", t):
            t = "0x" + t
        return t

    def one(tok: str):
        if "~" in tok:
            a, b = [nl(x) for x in tok.split("~", 1)]
            va, vb = int(a, 0), int(b, 0)
            lo, hi = min(va, vb), max(va, vb)
            return list(range(lo, hi + 1))
        return [int(nl(tok), 0)]

    for p in parts:
        out += one(p)
    uniq: List[int] = []
    [uniq.append(v) for v in out if v not in uniq]
    return uniq


def infer_mode_from_oms(oms: List[int]) -> Optional[str]:
    if not oms:
        return None
    if all(0 <= v <= 31 for v in oms):
        return "normal"
    if all(32 <= v <= 47 for v in oms):
        return "scan"
    if all(48 <= v <= 63 for v in oms):
        return "ipdt"
    return None


def coalesce_mode_row(mode_row: List[Any], sub_row: List[Any], om_row: List[Any]) -> List[Any]:
    n = max(len(mode_row), len(sub_row), len(om_row))
    out = list(mode_row) + [None] * (n - len(mode_row))
    for c in range(n):
        m = classify_mode(out[c] if c < len(out) else None)
        s_raw = sub_row[c] if c < len(sub_row) else ""
        s = norm(s_raw)
        if nlow(s_raw) in {"pin group", "pin name", "pad type"}:
            s = ""
        if m is None and s:
            oms = parse_om_values(om_row[c] if c < len(om_row) else "")
            im = infer_mode_from_oms(oms)
            if im:
                out[c] = {"normal": "Normal Mode", "scan": "Scan Mode", "ipdt": "IPDT Mode"}[im]
    return out


def strict_check_mode_submode(mode_row, sub_row):
    n = max(len(mode_row), len(sub_row))
    prev_key = None
    seen_runs: Dict[Tuple[str, str], Tuple[int, int]] = {}
    header_kw = {"pin group", "pin name", "pad type"}
    for c in range(n):
        m = classify_mode(mode_row[c] if c < len(mode_row) else None)
        raw_s = sub_row[c] if c < len(sub_row) else ""
        s = norm(raw_s)
        if nlow(raw_s) in header_kw:
            s = ""
        if (m is None and s) or (m is not None and s == ""):
            raise SpecError("F104", {"col": c + 1, "mode": m or "", "sub_mode": s})
        key = (m, s) if m is not None else None
        if key != prev_key:
            if key is not None:
                if key in seen_runs:
                    raise SpecError("F105", {"mode": key[0], "sub_mode": key[1], "col": c + 1})
                seen_runs[key] = (c, c)
            prev_key = key
        else:
            if key is not None:
                a, _ = seen_runs[key]
                seen_runs[key] = (a, c)


def detect_spans(mode_row, sub_row, om_row):
    mode_row_filled = coalesce_mode_row(mode_row, sub_row, om_row)
    strict_check_mode_submode(mode_row_filled, sub_row)
    spans: Dict[Tuple[str, str], Tuple[int, int, List[int]]] = {}
    c = 0
    n = max(len(mode_row_filled), len(sub_row), len(om_row))
    while c < n:
        m = classify_mode(mode_row_filled[c] if c < len(mode_row_filled) else None)
        if not m:
            c += 1
            continue
        name = norm(sub_row[c]) if c < len(sub_row) else f"{m}_sub{c}"
        c0 = c
        c += 1
        while c < n:
            m2 = classify_mode(mode_row_filled[c] if c < len(mode_row_filled) else None)
            n2 = norm(sub_row[c]) if c < len(sub_row) else f"{m}_sub{c}"
            if m2 == m and n2 == name:
                c += 1
            else:
                break
        c1 = c - 1
        oms = parse_om_values(om_row[c0] if c0 < len(om_row) else "")
        key = (m, name)
        if key in spans and spans[key][2] != oms:
            raise SpecError("O304", {"mode": m, "submode": name})
        spans[key] = (c0, c1, oms)
    if not spans:
        raise SpecError("F102")
    spans = {k: v for k, v in spans.items() if not re.search(r"reserved", k[1], re.I)}
    return spans


def parse_sheet(ws, pad_types: Dict[str, str], mux_exclude: Set[str]) -> ExcelModel:
    g = load_grid(ws)
    r_hdr, cmap = find_header_row(g)
    cg, cn, ct = cmap["Pin Group"], cmap["Pin Name"], cmap["PAD type"]

    r_mode = None
    for rr in range(r_hdr - 1, max(-1, r_hdr - 10), -1):
        if any(classify_mode(v) for v in g[rr]):
            r_mode = rr
            break
    if r_mode is None:
        r_mode = r_hdr
    r_sub = r_mode + 1
    r_om = r_mode + 2
    mode_row = g[r_mode]
    sub_row = g[r_sub]
    om_row = g[r_om]
    spans = detect_spans(mode_row, sub_row, om_row)

    pads_I: List[PadRow] = []
    pads_IO: List[PadRow] = []
    pads_OSC: List[str] = []
    seen: Set[str] = set()
    ixI = 0
    ixO = 0
    ex_bases = {strip_idx(x) for x in mux_exclude}

    r_data = data_start_row(g, r_hdr, cmap)
    for r in range(r_data, len(g)):
        row = g[r]
        pin_raw = row[cn] if cn < len(row) else None
        if pin_raw is None or norm(pin_raw) == "":
            continue
        pin = norm(pin_raw)
        if pin in seen:
            raise SpecError("F103", {"pin": pin, "row": r + 1})
        seen.add(pin)

        ptype_text = norm(row[ct] if ct < len(row) else "")
        pkey = padtype_key(ptype_text)
        pdir = pad_types.get(pkey, "")
        base = strip_idx(pin)

        if base in ("XIN", "XOUT"):
            if base not in pads_OSC:
                pads_OSC.append(base)
            continue

        excluded = (pin in mux_exclude) or (base in ex_bases) or (base.upper() in FORBIDDEN_BASES)

        if not pdir:
            raise SpecError("P201", {"pad_type": ptype_text, "pin": pin, "row": r + 1})

        group_val = norm(row[cg] if cg < len(row) else "")

        if pdir == "I":
            pr = PadRow(r, group_val, pin, ptype_text, "I", excluded, (-1 if excluded else ixI))
            if not excluded:
                pads_I.append(pr)
                ixI += 1
        else:
            pr = PadRow(r, group_val, pin, ptype_text, "IO", excluded, (-1 if excluded else ixO))
            if not excluded:
                pads_IO.append(pr)
                ixO += 1

    pin2pad = {p.name: p for p in pads_I + pads_IO}
    modes: Dict[str, List[SubMode]] = {"normal": [], "scan": [], "ipdt": []}
    bit_idx = {"normal": 0, "scan": 0, "ipdt": 0}
    for (m, name), (c0, c1, omv) in sorted(spans.items(), key=lambda kv: kv[1][0]):
        sm = SubMode(m, name, omv, [], bit_idx[m])
        bit_idx[m] += 1
        modes[m].append(sm)

    for r in range(r_data, len(g)):
        row = g[r]
        pin_raw = row[cn] if cn < len(row) else None
        if pin_raw is None or norm(pin_raw) == "":
            continue
        pin = norm(pin_raw)
        base_pin = strip_idx(pin)

        any_payload = False
        for (_m, _n), (c0, c1, _) in spans.items():
            for c in range(c0, c1 + 1):
                if c < len(row) and row[c] not in (None, ""):
                    any_payload = True
                    break
            if any_payload:
                break

        if any_payload and ((pin in mux_exclude) or (base_pin in ex_bases)):
            raise SpecError("S701", {"pin": pin, "row": r + 1})

        base_up = base_pin.upper()
        if any_payload and (base_up in FORBIDDEN_BASES):
            raise SpecError("P203", {"pin": pin, "row": r + 1})

        pr = pin2pad.get(pin, None)
        if pr is None:
            continue

        for (m, name), (c0, c1, _) in spans.items():
            width = c1 - c0 + 1
            if width < 4:
                has_any = any((cc < len(row) and norm(row[cc]) != "") for cc in range(c0, c1 + 1))
                if has_any:
                    raise SpecError("F106", {"row": r + 1, "submode": name, "reason": "block width < 4 (missing Marker/Direction/Default)"})
                else:
                    continue

            ctrl_c0 = c1 - 2
            scname = norm(row[c0] if c0 < len(row) else "")
            if scname == "":
                any_payload = any((c < len(row) and row[c] not in (None, "")) for c in range(c0, c1 + 1))
                if any_payload:
                    continue
                else:
                    continue

            v_marker = norm(row[ctrl_c0] if ctrl_c0 < len(row) else "")
            v_dir = norm(row[ctrl_c0 + 1] if ctrl_c0 + 1 < len(row) else "")
            v_default = norm(row[ctrl_c0 + 2] if ctrl_c0 + 2 < len(row) else "")

            if scname != "" and v_dir == "":
                misplaced_dir_col = None
                for cc in range(c0 + 1, ctrl_c0 + 1):
                    tok = norm(row[cc] if cc < len(row) else "")
                    if tok.upper() in ("I", "O", "IO"):
                        misplaced_dir_col = cc + 1
                        break
                if misplaced_dir_col is not None:
                    raise SpecError(
                        "F106",
                        {
                            "row": r + 1,
                            "submode": name,
                            "col": ctrl_c0 + 2,
                            "field": "direction",
                            "value": v_dir,
                            "reason": f"direction must be at last-1 column; found at col={misplaced_dir_col}",
                        },
                    )

            if v_marker == "" and v_dir == "" and v_default == "":
                other_payload = any((c < len(row) and row[c] not in (None, "")) for c in range(c0 + 1, ctrl_c0))
                if other_payload:
                    raise SpecError("F106", {"row": r + 1, "submode": name, "reason": "control columns empty but other columns filled"})
                else:
                    continue

            marker = "none"
            if v_marker != "":
                um = v_marker.upper()
                if um in ("C", "R"):
                    marker = um
                else:
                    raise SpecError("F106", {"row": r + 1, "submode": name, "col": ctrl_c0 + 1, "field": "marker", "value": v_marker})

            ud = v_dir.upper()
            if ud in ("I", "O", "IO"):
                direction = ud
            else:
                raise SpecError("F106", {"row": r + 1, "submode": name, "col": ctrl_c0 + 2, "field": "direction", "value": v_dir})

            dflt = v_default
            if dflt == "":
                dflt = "1'b0"
            else:
                vd = dflt.lower()
                if vd in ("0", "1", "1'b0", "1'b1"):
                    dflt = ("1'b" + vd if vd in ("0", "1") else dflt)
                else:
                    raise SpecError("F106", {"row": r + 1, "submode": name, "col": ctrl_c0 + 3, "field": "default", "value": v_default})

            raw_base = scname
            raw_en = None
            if "/" in scname:
                left, right = [x.strip() for x in scname.split("/", 1)]
                raw_base, raw_en = left, right

            m2 = re.match(r"^(?P<base>[A-Za-z_]\w*)(?:\[(?P<idx>\d+)\])?$", raw_base)
            base_name = m2.group("base") if m2 else raw_base
            base_idx = int(m2.group("idx")) if (m2 and m2.group("idx")) else None

            en_idx = None
            if raw_en:
                m3 = re.match(r"^(?P<base>[A-Za-z_]\w*)(?:\[(?P<idx>\d+)\])?$", raw_en)
                en_idx = int(m3.group("idx")) if (m3 and m3.group("idx")) else None

            nt_ord = None
            for c in range(c0 + 1, ctrl_c0):
                if c < len(row):
                    m_nt = NT_IN_RE.fullmatch(norm(row[c]))
                    if m_nt:
                        nt_ord = int(m_nt.group(1))
                        break

            if pr.kind == "I" and direction in ("O", "IO"):
                raise SpecError("P202", {"pin": pin, "row": r + 1, "submode": name})

            cell = SigCell(
                base_name,
                base_idx,
                raw_en,
                en_idx,
                marker,
                direction or "",
                dflt,
                pr.kind,
                pr.index,
                pin,
                pr.row,
                nt_ord,
            )
            for sm in modes[m]:
                if sm.name == name:
                    sm.cells.append(cell)
                    break

    return ExcelModel(pads_I, pads_IO, pads_OSC, modes)

