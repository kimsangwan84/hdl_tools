from typing import Dict, List, Set, Tuple

from ..banner import banner
from ..errors import SpecError
from ..models import SubMode
from ..utils import (
    align_assign_pairs,
    align_decls,
    align_instance,
    align_ports,
    en_names_for_base,
    fmt_if,
    idx_r,
    is_gpio_like,
    is_io_test_name,
    is_oe_name,
    sv_id,
    gpio_like_port_entries,
)
from .common import build_bus_maps_for_mode, short_sm_name


def gen_mode_mux_sv(mode: str, NI: int, NO: int, subs: List[SubMode]):
    sig_w_map, sig_dir_map, en_w_map, per_sub = build_bus_maps_for_mode(subs)

    io_test_idx = next((i for i, sm in enumerate(subs) if is_io_test_name(sm.name)), None)
    has_io_test = io_test_idx is not None

    widths_by_base: Dict[str, Set[int]] = {}
    for sm, l_sig_w, _ in per_sub:
        for b, w in l_sig_w.items():
            widths_by_base.setdefault(b, set()).add(w)
    for b, ws in widths_by_base.items():
        if len(ws) > 1:
            raise SpecError("U903", {"mode": mode, "base": b, "widths": sorted(ws)})

    ports: List[Dict[str, str]] = []
    marks: List[Tuple[int, str]] = []

    a0 = len(ports)
    marks.append((a0, f"// ---- {mode.upper()} : mode_enable & test_if ----"))
    ports.append({"direction": "input", "type": "logic", "bits": ("" if len(subs) <= 1 else f"[{len(subs)-1}:0]"), "name": f"{mode}_mode_enable", "array": "", "iface": ""})
    ports.append({"direction": "", "type": "", "bits": "", "name": "test_in", "array": f"[0:{max(0, NI-1)}]", "iface": "if_pad_in.core"})
    ports.append({"direction": "", "type": "", "bits": "", "name": "test_io", "array": f"[0:{max(0, NO-1)}]", "iface": "if_pad_io.core"})
    if has_io_test:
        ports.append({"direction": "", "type": "", "bits": "", "name": "io_test_osc_io", "array": "", "iface": "if_pad_osc.core"})
        ports.append({"direction": "", "type": "", "bits": "", "name": "io_test_in", "array": f"[0:{max(0, NI-1)}]", "iface": "if_pad_in.core"})
        ports.append({"direction": "", "type": "", "bits": "", "name": "io_test_io", "array": f"[0:{max(0, NO-1)}]", "iface": "if_pad_io.core"})

    present: Dict[str, int] = {}
    per_sm_sets = []
    for sm, l_sig_w, _ in per_sub:
        sigs = {b for b in l_sig_w.keys() if not is_oe_name(b)}
        per_sm_sets.append((sm, sigs))
        for b in sigs:
            present[b] = present.get(b, 0) + 1
    shared = [b for b, cnt in present.items() if cnt > 1]
    unique_by_sm = [(sm, [b for b in s if present[b] == 1]) for sm, s in per_sm_sets]

    b0 = len(ports)
    marks.append((b0, f"// ---- shared signals across sub-modes ----"))
    for base in sorted(shared):
        w = sig_w_map[base]
        dir_ = sig_dir_map[base]
        if is_gpio_like(base):
            ports += gpio_like_port_entries(base, w)
        ports.append({"direction": dir_, "type": "logic", "bits": ("" if w <= 1 else f"[{w-1}:0]"), "name": sv_id(base), "array": "", "iface": ""})
        for eb in en_names_for_base(base, en_w_map):
            w_en = en_w_map[eb]
            ports.append({"direction": "input", "type": "logic", "bits": ("" if w_en <= 1 else f"[{w_en-1}:0]"), "name": sv_id(eb), "array": "", "iface": ""})

    for sm, lst in unique_by_sm:
        if not lst:
            continue
        c0 = len(ports)
        marks.append((c0, f"// ---- only in {sv_id(sm.name)} ----"))
        for base in sorted(lst):
            w = sig_w_map[base]
            dir_ = sig_dir_map[base]
            if is_gpio_like(base):
                ports += gpio_like_port_entries(base, w)
            ports.append({"direction": dir_, "type": "logic", "bits": ("" if w <= 1 else f"[{w-1}:0]"), "name": sv_id(base), "array": "", "iface": ""})
            for eb in en_names_for_base(base, en_w_map):
                w_en = en_w_map[eb]
                ports.append({"direction": "input", "type": "logic", "bits": ("" if w_en <= 1 else f"[{w_en-1}:0]"), "name": sv_id(eb), "array": "", "iface": ""})

    L = banner() + [f"module {mode}_mux import gpio_pkg::*; ("]
    port_lines, _ = align_ports(ports)
    mark_map = {i: s for (i, s) in marks}
    for i, line in enumerate(port_lines):
        if i in mark_map:
            L.append("  " + mark_map[i])
        L.append(line)
    L.append(");\n")

    IDXW_I = max(1, len(str(max(0, NI - 1))))
    IDXW_O = max(1, len(str(max(0, NO - 1))))
    FW_I = 2
    FW_O = 5

    out_decls = []
    out_wires_by_base: Dict[str, List[Tuple[int, int, str]]] = {}
    for i, (sm, l_sig_w, l_dir) in enumerate(per_sub):
        if is_io_test_name(sm.name):
            continue
        L.append(f"  // -- integrate {sv_id(sm.name)}")
        L.append(f"  if_pad_in.core core_{i}_in [0:{max(0, NI-1)}]();")
        L.append(f"  if_pad_io.core core_{i}_io [0:{max(0, NO-1)}]();")
        en_idxW = len(str(max(0, len(per_sub) - 1)))
        conns = [
            (".test_en", f"{mode}_mode_enable{idx_r(i, en_idxW)}"),
            (".test_in", f"core_{i}_in"),
            (".test_io", f"core_{i}_io"),
        ]
        for base in sorted(l_sig_w.keys()):
            w = l_sig_w[base]
            dir_ = l_dir[base]
            bname = sv_id(base)
            if dir_ == "output":
                short = sv_id(short_sm_name(sm.name))
                wname = f"{short}_{bname}"
                out_decls.append(("logic", ("" if w <= 1 else f"[{w-1}:0]"), wname))
                out_wires_by_base.setdefault(base, []).append((i, w, wname))
                conns.append((f".{bname}", wname))
            else:
                gated = f"{mode}_mode_enable{idx_r(i, en_idxW)} ? {bname} : '0"
                conns.append((f".{bname}", gated))
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
        for eb in sorted(en_w_map.keys()):
            conns.append((f".{sv_id(eb)}", sv_id(eb)))
        L.append(f"  {sv_id(sm.name)} u_{sv_id(sm.name)}")
        L += align_instance(conns)
        L.append("")

    if out_decls:
        L += align_decls(out_decls)
        L.append("")

    def widen(expr, wi, W):
        if wi == W:
            return expr
        return "{ " + f"{{{W-wi}{{1'b0}}}}, {expr} " + "}"

    mux_pairs = []
    for base, lst in out_wires_by_base.items():
        W = sig_w_map.get(base, 1)
        en_idxW = len(str(max(0, len(per_sub) - 1)))
        terms = [f"({mode}_mode_enable{idx_r(i, en_idxW)} ? {widen(wi_name, wi, W)} : '0)" for i, wi, wi_name in lst]
        mux_pairs.append((sv_id(base), " | ".join(terms) if terms else "'0"))
    if mux_pairs:
        L += align_assign_pairs(mux_pairs)
        L.append("")

    def or_terms(ifname, idx, field, fieldW):
        en_idxW = len(str(max(0, len(per_sub) - 1)))
        idxT = idx_r(idx, IDXW_I if ifname == "in" else IDXW_O)
        core = lambda i: f"core_{i}_{ifname}{idxT}.{field.ljust(fieldW)}"
        terms = []
        for i, (sm, _, _) in enumerate(per_sub):
            if is_io_test_name(sm.name):
                continue
            terms.append(f"({mode}_mode_enable{idx_r(i, en_idxW)} ? {core(i)} : '0)")
        if has_io_test and io_test_idx is not None:
            src = f"io_test_{'in' if ifname=='in' else 'io'}{idxT}.{field.ljust(fieldW)}"
            terms.append(f"({mode}_mode_enable{idx_r(io_test_idx, en_idxW)} ? {src} : '0)")
        return " | ".join(terms)

    pairs = []
    for i in range(NI):
        for fld in ("PE", "PS", "ST", "IE"):
            pairs.append((fmt_if("test_in", i, fld, IDXW_I, FW_I), or_terms("in", i, fld, FW_I)))
    L += align_assign_pairs(pairs)
    L.append("")
    pairs = []
    for i in range(NO):
        for fld in ("OEN", "I", "DS", "PE_PU", "PS_PD", "ST", "IE"):
            pairs.append((fmt_if("test_io", i, fld, IDXW_O, FW_O), or_terms("io", i, fld, FW_O)))
    L += align_assign_pairs(pairs)
    L.append("")
    decls = []
    if NI > 0:
        decls.append(("logic", f"[{NI-1}:0]", "c_in"))
    if NO > 0:
        decls.append(("logic", f"[{NO-1}:0]", "c_io"))
    if decls:
        L += align_decls(decls)
        L.append("")
    pairs = [(f"c_in{idx_r(i, IDXW_I)}", or_terms("in", i, "C", 1)) for i in range(NI)]
    L += align_assign_pairs(pairs)
    pairs = [(f"c_io{idx_r(i, IDXW_O)}", or_terms("io", i, "C", 1)) for i in range(NO)]
    L += align_assign_pairs(pairs)
    L.append("")
    for i in range(NI):
        L.append(f"  primemas_lib_buf z_buf_{mode}_IN_{i}_C ( .A(c_in{idx_r(i, IDXW_I)}), .Y({fmt_if('test_in', i, 'C', IDXW_I, 1)}) );")
    for i in range(NO):
        L.append(f"  primemas_lib_buf z_buf_{mode}_IO_{i}_C ( .A(c_io{idx_r(i, IDXW_O)}), .Y({fmt_if('test_io', i, 'C', IDXW_O, 1)}) );")
    L.append("endmodule\n")
    return "\n".join(L), sig_w_map, sig_dir_map, en_w_map
