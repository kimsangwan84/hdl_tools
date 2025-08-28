import re
from typing import Dict, List, Optional, Tuple

from ..banner import banner
from ..models import ExcelModel
from ..utils import (
    align_assign_pairs,
    align_decls,
    align_ports,
    en_names_for_base,
    fmt_if,
    is_gpio_like,
    is_io_test_name,
    pad_orientation,
    sv_id,
)
from .common import build_bus_maps_global


def gen_pad_mux_sv(model: ExcelModel, mode_maps) -> str:
    NI = len(model.pads_I)
    NO = len(model.pads_IO)
    has_io_test_any = any(any(is_io_test_name(sm.name) for sm in model.modes[m]) for m in ("normal", "scan", "ipdt"))
    has_io_test_mode = {m: any(is_io_test_name(sm.name) for sm in model.modes[m]) for m in ("normal", "scan", "ipdt")}
    g_sig_w, g_sig_dir, g_en_w = build_bus_maps_global(model.modes)

    ports: List[Dict[str, str]] = []
    marks: List[Tuple[int, str]] = []
    added = set()

    def add_port(entry):
        key = (
            entry["direction"],
            entry["type"],
            entry["bits"],
            entry["name"],
            entry.get("iface", ""),
            entry.get("array", ""),
        )
        if key in added:
            return
        added.add(key)
        ports.append(entry)

    a0 = len(ports)
    marks.append((a0, "// ---- enables ----"))
    add_port({"direction": "input", "type": "logic", "bits": "[31:0]", "name": "normal_mode_enable", "array": "", "iface": ""})
    add_port({"direction": "input", "type": "logic", "bits": "[15:0]", "name": "scan_mode_enable", "array": "", "iface": ""})
    add_port({"direction": "input", "type": "logic", "bits": "[15:0]", "name": "ipdt_mode_enable", "array": "", "iface": ""})

    if has_io_test_any:
        p1 = len(ports)
        marks.append((p1, "// ---- io_test passthrough ----"))
        add_port({"direction": "", "type": "", "bits": "", "name": "io_test_osc_io", "array": "", "iface": "if_pad_osc.core"})
        add_port({"direction": "", "type": "", "bits": "", "name": "io_test_in", "array": f"[0:{max(0, NI-1)}]", "iface": "if_pad_in.core"})
        add_port({"direction": "", "type": "", "bits": "", "name": "io_test_io", "array": f"[0:{max(0, NO-1)}]", "iface": "if_pad_io.core"})

    for mode in ("normal", "scan", "ipdt"):
        sig_w_map, sig_dir_map, en_w_map = mode_maps[mode]
        m0 = len(ports)
        marks.append((m0, f"// ---- {mode.capitalize()} signals ----"))
        for base in sorted(sig_w_map.keys()):
            W = "" if g_sig_w[base] <= 1 else f"[{g_sig_w[base]-1}:0]"
            if is_gpio_like(base):
                from ..utils import gpio_like_port_entries

                for e in gpio_like_port_entries(base, g_sig_w[base]):
                    add_port(e)
            add_port({"direction": g_sig_dir.get(base, sig_dir_map[base]), "type": "logic", "bits": W, "name": sv_id(base), "array": "", "iface": ""})
            for eb in en_names_for_base(base, g_en_w):
                W_en = "" if g_en_w[eb] <= 1 else f"[{g_en_w[eb]-1}:0]"
                add_port({"direction": "input", "type": "logic", "bits": W_en, "name": sv_id(eb), "array": "", "iface": ""})

    def vec_groups(pads):
        g = {}
        for pr in pads:
            m = re.match(r"^(?P<base>[A-Za-z_]\w*)(?:\[(?P<idx>\d+)\])?$", pr.name)
            if m:
                base = m.group("base")
                idx = m.group("idx")
                g.setdefault(base, []).append(int(idx) if idx is not None else None)
            else:
                g.setdefault(pr.name, []).append(None)
        return g

    in_g = vec_groups(model.pads_I)
    io_g = vec_groups(model.pads_IO)

    def pad_digits(groups: Dict[str, List[Optional[int]]]) -> Dict[str, int]:
        d = {}
        for base, idxs in groups.items():
            mx = max([i for i in idxs if i is not None] or [0])
            d[base] = max(3, len(str(mx)))
        return d

    DIG_I = pad_digits(in_g)
    DIG_IO = pad_digits(io_g)

    p0 = len(ports)
    marks.append((p0, "// ---- PAD pins ----"))
    for base, idxs in sorted(in_g.items()):
        if all(i is None for i in idxs):
            add_port({"direction": "input", "type": "logic", "bits": "", "name": sv_id(base), "array": "", "iface": ""})
        else:
            msb = max(i for i in idxs if i is not None)
            lsb = min(i for i in idxs if i is not None)
            add_port({"direction": "input", "type": "logic", "bits": f"[{msb}:{lsb}]", "name": sv_id(base), "array": "", "iface": ""})
    for base, idxs in sorted(io_g.items()):
        if all(i is None for i in idxs):
            add_port({"direction": "inout", "type": "logic", "bits": "", "name": sv_id(base), "array": "", "iface": ""})
        else:
            msb = max(i for i in idxs if i is not None)
            lsb = min(i for i in idxs if i is not None)
            add_port({"direction": "inout", "type": "logic", "bits": f"[{msb}:{lsb}]", "name": sv_id(base), "array": "", "iface": ""})
    if set(model.pads_OSC) >= {"XIN", "XOUT"}:
        add_port({"direction": "input", "type": "logic", "bits": "", "name": "XIN", "array": "", "iface": ""})
        add_port({"direction": "output", "type": "logic", "bits": "", "name": "XOUT", "array": "", "iface": ""})

    L = banner() + ["module pad_mux import gpio_pkg::*; ("]
    port_lines, _ = align_ports(ports)
    mark_map = {i: s for (i, s) in marks}
    for i, line in enumerate(port_lines):
        if i in mark_map:
            L.append("  " + mark_map[i])
        L.append(line)
    L.append(");\n")

    L.append(f"  if_pad_in.core core_normal_in  [0:{max(0, NI-1)}]();")
    L.append(f"  if_pad_io.core core_normal_io  [0:{max(0, NO-1)}]();")
    L.append(f"  if_pad_in.core core_scan_in    [0:{max(0, NI-1)}]();")
    L.append(f"  if_pad_io.core core_scan_io    [0:{max(0, NO-1)}]();")
    L.append(f"  if_pad_in.core core_ipdt_in    [0:{max(0, NI-1)}]();")
    L.append(f"  if_pad_io.core core_ipdt_io    [0:{max(0, NO-1)}]();")
    L.append("")

    for mode in ("normal", "scan", "ipdt"):
        sig_w_map, sig_dir_map, en_w_map = mode_maps[mode]
        conns = [
            (".test_in", f"core_{mode}_in"),
            (".test_io", f"core_{mode}_io"),
        ]
        if has_io_test_mode[mode]:
            conns.append((".io_test_osc_io", "io_test_osc_io"))
            conns.append((".io_test_in", "io_test_in"))
            conns.append((".io_test_io", "io_test_io"))
        conns.append((f".{mode}_mode_enable", f"{mode}_mode_enable"))
        for base in sorted(sig_w_map.keys()):
            if is_gpio_like(base):
                B = sv_id(base)
                conns += [
                    (f".{B}_oen", f"{B}_oen"),
                    (f".{B}_i", f"{B}_i"),
                    (f".{B}_pe_pu", f"{B}_pe_pu"),
                    (f".{B}_ps_pd", f"{B}_ps_pd"),
                    (f".{B}_st", f"{B}_st"),
                    (f".{B}_ie", f"{B}_ie"),
                    (f".{B}_ds", f"{B}_ds"),
                    (f".{B}_c", f"{B}_c"),
                ]
            conns.append((f".{sv_id(base)}", sv_id(base)))
        for eb in sorted(en_w_map.keys()):
            conns.append((f".{sv_id(eb)}", sv_id(eb)))
        L.append(f"  {mode}_mux u_{mode}_mux")
        from ..utils import align_instance

        L += align_instance(conns)
        L.append("")

    IDXW_I = max(1, len(str(max(0, NI - 1))))
    IDXW_O = max(1, len(str(max(0, NO - 1))))
    FW_I = 2
    FW_O = 5
    L.append("  logic test_on;")
    L.append("  assign test_on = |scan_mode_enable | |ipdt_mode_enable;")

    def sel_expr(ifname, idx, fld, fieldW):
        idxT = f"[{str(idx).rjust(IDXW_I if ifname=='in' else IDXW_O)}]"
        a = f"core_scan_{ifname}{idxT}.{fld.ljust(fieldW)}"
        b = f"core_ipdt_{ifname}{idxT}.{fld.ljust(fieldW)}"
        c = f"core_normal_{ifname}{idxT}.{fld.ljust(fieldW)}"
        return f"test_on ? ( |scan_mode_enable ? {a} : {b} ) : {c}"

    pairs = []
    for i in range(NI):
        for fld in ("PE", "PS", "ST", "IE"):
            pairs.append((fmt_if("pad_in", i, fld, IDXW_I, FW_I), sel_expr("in", i, fld, FW_I)))
        pairs.append((fmt_if("pad_in", i, "C", IDXW_I, 1), sel_expr("in", i, "C", 1)))
    L += align_assign_pairs(pairs)
    L.append("")
    pairs = []
    for i in range(NO):
        for fld in ("OEN", "I", "DS", "PE_PU", "PS_PD", "ST", "IE"):
            pairs.append((fmt_if("pad_io", i, fld, IDXW_O, FW_O), sel_expr("io", i, fld, FW_O)))
        pairs.append((fmt_if("pad_io", i, "C", IDXW_O, 1), sel_expr("io", i, "C", 1)))
    L += align_assign_pairs(pairs)
    L.append("")

    def inst_name(kind: str, idx, base: str, bit: Optional[int], digits: int) -> str:
        try:
            idx_str = f"{int(idx):03d}"
        except Exception:
            idx_str = str(idx)
        label = sv_id(base) if bit is None else f"{sv_id(base)}_{int(bit):0{digits}d}"
        return f"u_{kind}_{idx_str}_pad_{label}"

    if set(model.pads_OSC) >= {"XIN", "XOUT"}:
        L.append("  // OSC PAD")
        L.append("  primemas_lib_OSC_PAD #(.ORIENTATION(\"V\")) " f"{inst_name('0', 0, 'XIN_XOUT', None, 3)} ( .XIN(XIN), .XOUT(XOUT), .XE(pad_osc_io.XE), .DS(pad_osc_io.DS), .REF(pad_osc_ref), .RD(pad_osc_rd), .XC(pad_osc_io_XC), .RTE(1'b0) );\n")
        L.append("  primemas_lib_buf u_osc_anchor ( .A(pad_osc_io_XC), .Y(pad_osc_io.XC) );")

    L.append("  // IN PADs")
    for i, pr in enumerate(model.pads_I):
        m = re.match(r"^(?P<base>[A-Za-z_]\w*)(?:\[(?P<idx>\d+)\])?$", pr.name)
        base = m.group('base') if m else pr.name
        bit = int(m.group('idx')) if (m and m.group('idx') is not None) else None
        pad_sig = f"{sv_id(base)}[{bit}]" if bit is not None else sv_id(base)
        orient = pad_orientation(pr.pad_type)
        name = inst_name('1', (pr.index if pr.index >= 0 else i), base, bit, DIG_I.get(base, 3))
        L.append(
            f"  primemas_lib_IN_PAD #(.ORIENTATION(\"{orient}\")) {name} ( .PAD({pad_sig}), .PE({fmt_if('pad_in', pr.index, 'PE', max(1, len(str(max(0, NI-1)))), 2)}), .PS({fmt_if('pad_in', pr.index, 'PS', max(1, len(str(max(0, NI-1)))), 2)}), .ST({fmt_if('pad_in', pr.index, 'ST', max(1, len(str(max(0, NI-1)))), 2)}), .IE({fmt_if('pad_in', pr.index, 'IE', max(1, len(str(max(0, NI-1)))), 2)}), .C({fmt_if('pad_in', pr.index, 'C', max(1, len(str(max(0, NI-1)))), 1)}), .RTE(1'b0) );"
        )
    L.append("")
    L.append("  // IO PADs")
    for i, pr in enumerate(model.pads_IO):
        m = re.match(r"^(?P<base>[A-Za-z_]\w*)(?:\[(?P<idx>\d+)\])?$", pr.name)
        base = m.group('base') if m else pr.name
        bit = int(m.group('idx')) if (m and m.group('idx') is not None) else None
        pad_sig = f"{sv_id(base)}[{bit}]" if bit is not None else sv_id(base)
        orient = pad_orientation(pr.pad_type)
        name = inst_name('2', (pr.index if pr.index >= 0 else i), base, bit, DIG_IO.get(base, 3))
        L.append(
            f"  primemas_lib_IO_PAD #(.ORIENTATION(\"{orient}\")) {name} ( .PAD({pad_sig}), .OEN({fmt_if('pad_io', pr.index, 'OEN', max(1, len(str(max(0, NO-1)))), 5)}), .I({fmt_if('pad_io', pr.index, 'I', max(1, len(str(max(0, NO-1)))), 5)}), .DS({fmt_if('pad_io', pr.index, 'DS', max(1, len(str(max(0, NO-1)))), 5)}), .PE({fmt_if('pad_io', pr.index, 'PE_PU', max(1, len(str(max(0, NO-1)))), 5)}), .PS({fmt_if('pad_io', pr.index, 'PS_PD', max(1, len(str(max(0, NO-1)))), 5)}), .ST({fmt_if('pad_io', pr.index, 'ST', max(1, len(str(max(0, NO-1)))), 5)}), .IE({fmt_if('pad_io', pr.index, 'IE', max(1, len(str(max(0, NO-1)))), 5)}), .C({fmt_if('pad_io', pr.index, 'C', max(1, len(str(max(0, NO-1)))), 1)}), .RTE(1'b0) );"
        )

    L.append("\nendmodule\n")
    return "\n".join(L)
