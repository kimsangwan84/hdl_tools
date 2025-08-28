from typing import List

from ..banner import banner
from ..models import SubMode
from ..utils import (
    fmt_if,
    fmt_vec,
    is_active_low_oe,
    is_gpio_like,
    sv_id,
)


def gen_submode_sv(NI: int, NO: int, sm: SubMode) -> str:
    sig_map = {}
    en_map = {}
    for c in sm.cells:
        base = c.base
        want = "output" if c.direction == "I" else "input"
        ent = sig_map.setdefault(base, {"dir": want, "idx": set()})
        if ent["dir"] != want:
            from ..errors import SpecError

            raise SpecError("U902", {"base": base, "submode": sm.name})
        if c.base_idx is not None:
            ent["idx"].add(c.base_idx)
        if c.enable:
            eb = c.enable.split("[")[0]
            s = en_map.setdefault(eb, set())
            if c.enable_idx is not None:
                s.add(c.enable_idx)
    sig_w = {b: (max(v["idx"]) + 1 if v["idx"] else 1) for b, v in sig_map.items()}
    sig_dir = {b: v["dir"] for b, v in sig_map.items()}
    en_w = {b: (max(v) + 1 if v else 1) for b, v in en_map.items()}

    if sm.name.strip().lower() == "nand_tree":
        ports = [
            {"direction": "input", "type": "logic", "bits": "", "name": "test_en", "array": "", "iface": ""},
            {"direction": "", "type": "", "bits": "", "name": "test_in", "array": f"[0:{max(0, NI-1)}]", "iface": "if_pad_in.core"},
            {"direction": "", "type": "", "bits": "", "name": "test_io", "array": f"[0:{max(0, NO-1)}]", "iface": "if_pad_io.core"},
        ]
        from ..utils import align_ports

        L = banner() + [f"module {sv_id(sm.name)} import gpio_pkg::*; ("]
        port_lines, _ = align_ports(ports)
        L += port_lines
        L.append(");\n")

        IDXW_I = max(1, len(str(max(0, NI - 1))))
        IDXW_O = max(1, len(str(max(0, NO - 1))))
        FW_I = 2
        FW_O = 5

        inputs = []
        outputs = []
        for c in sm.cells:
            use_as_input = c.direction in ("I", "IO")
            use_as_output = c.pad_kind == "IO" and c.direction in ("O", "IO")
            if use_as_input:
                if c.pad_kind == "I":
                    expr = fmt_if("test_in", c.pad_index, "C", IDXW_I, 1)
                    inputs.append((expr, "in", c.pad_index, c.excel_row, c.nt_order))
                else:
                    expr = fmt_if("test_io", c.pad_index, "C", IDXW_O, 1)
                    inputs.append((expr, "io", c.pad_index, c.excel_row, c.nt_order))
            if use_as_output:
                outputs.append(c)

        for c in sm.cells:
            if c.direction in ("I", "IO"):
                if c.pad_kind == "I":
                    for fld, val in (("PE", "TI_PE_PU"), ("PS", "TI_PS_PD"), ("ST", "TI_ST"), ("IE", "TI_IE")):
                        L.append(f"  assign {fmt_if('test_in', c.pad_index, fld, IDXW_I, FW_I)} = {val};")
                else:
                    for fld, val in (
                        ("PE_PU", "TI_PE_PU"),
                        ("PS_PD", "TI_PS_PD"),
                        ("ST", "TI_ST"),
                        ("IE", "TI_IE"),
                        ("I", "TI_I"),
                        ("OEN", "TI_OEN"),
                        ("DS", "TI_DS"),
                    ):
                        L.append(f"  assign {fmt_if('test_io', c.pad_index, fld, IDXW_O, FW_O)} = {val};")
        if sm.cells:
            L.append("")

        inputs.sort(key=lambda x: ((x[4] if x[4] is not None else 10**9), x[3], x[2]))
        exprs = [t[0] for t in inputs]
        EW = max((len(s) for s in exprs), default=1)
        n = len(exprs)
        if n >= 2:
            L.append(f"  logic [{n-2}:0] nand_out;")
            WNT = len(str(max(0, n - 2)))
            L.append(
                f"  primemas_lib_nand2 u_nand_000 ( .A({exprs[0].ljust(EW)}), .B({exprs[1].ljust(EW)}), .Y(nand_out{('['+str(0).rjust(WNT)+']')}) );"
            )
            for k in range(2, n):
                L.append(
                    f"  primemas_lib_nand2 u_nand_{k:03d} ( .A(nand_out{('['+str(k-2).rjust(WNT)+']')}), .B({exprs[k].ljust(EW)}), .Y(nand_out{('['+str(k-1).rjust(WNT)+']')}) );"
                )
            final = f"nand_out{('['+str(n-2).rjust(WNT)+']')}"
        elif n == 1:
            final = exprs[0]
        else:
            final = "'0'"

        for c in outputs:
            L.append(f"  assign {fmt_if('test_io', c.pad_index, 'I', IDXW_O, FW_O)} = {final};")
            for fld, val in (("PE_PU", "TO_PE_PU"), ("PS_PD", "TO_PS_PD"), ("ST", "TO_ST"), ("IE", "TO_IE"), ("DS", "TO_DS")):
                L.append(f"  assign {fmt_if('test_io', c.pad_index, fld, IDXW_O, FW_O)} = {val};")
            if c.enable:
                en = f"{sv_id(c.enable.split('[')[0])}{('['+str(c.enable_idx)+']') if c.enable_idx is not None else ''}"
                oen = en if is_active_low_oe(c.enable) else f"~{en}"
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'OEN', IDXW_O, FW_O)} = {oen};")
            else:
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'OEN', IDXW_O, FW_O)} = TO_OEN;")
        L.append("endmodule\n")
        return "\n".join(L)

    from ..utils import align_ports

    ports = [
        {"direction": "input", "type": "logic", "bits": "", "name": "test_en", "array": "", "iface": ""},
        {"direction": "", "type": "", "bits": "", "name": "test_in", "array": f"[0:{max(0, NI-1)}]", "iface": "if_pad_in.core"},
        {"direction": "", "type": "", "bits": "", "name": "test_io", "array": f"[0:{max(0, NO-1)}]", "iface": "if_pad_io.core"},
    ]
    for base in sorted(sig_w.keys()):
        w = sig_w[base]
        dir_ = sig_dir[base]
        if is_gpio_like(base):
            from ..utils import gpio_like_port_entries

            ports += gpio_like_port_entries(base, w)
        ports.append({"direction": dir_, "type": "logic", "bits": ("" if w <= 1 else f"[{w-1}:0]"), "name": sv_id(base), "array": "", "iface": ""})
        for eb in sorted(en_w.keys()):
            if eb.split("[")[0].startswith(base):
                w_en = en_w[eb]
                ports.append({"direction": "input", "type": "logic", "bits": ("" if w_en <= 1 else f"[{w_en-1}:0]"), "name": sv_id(eb), "array": "", "iface": ""})

    L = banner() + [f"module {sv_id(sm.name)} import gpio_pkg::*; ("]
    port_lines, _ = align_ports(ports)
    L += port_lines
    L.append(");\n")

    IDXW_I = max(1, len(str(max(0, NI - 1))))
    IDXW_O = max(1, len(str(max(0, NO - 1))))
    FW_I = 2
    FW_O = 5

    def oen_expr(c, def_val):
        if not c.enable:
            return def_val
        en = f"{sv_id(c.enable.split('[')[0])}{('['+str(c.enable_idx)+']') if c.enable_idx is not None else ''}"
        return en if is_active_low_oe(c.enable) else f"~{en}"

    for c in sm.cells:
        b = f"{sv_id(c.base)}[{c.base_idx}]" if c.base_idx is not None else sv_id(c.base)
        if c.pad_kind == "I":
            L.append(f"  assign {b} = test_en ? {fmt_if('test_in', c.pad_index, 'C', IDXW_I, 1)} : {c.default_in};")
            for fld, val in (("PE", "TI_PE_PU"), ("PS", "TI_PS_PD"), ("ST", "TI_ST"), ("IE", "TI_IE")):
                L.append(f"  assign {fmt_if('test_in', c.pad_index, fld, IDXW_I, FW_I)} = {val};")
        elif c.pad_kind == "IO":
            if is_gpio_like(c.base):
                B = sv_id(c.base)
                L.append(f"  assign {fmt_vec(B+'_c', c.pad_index, IDXW_O)} = test_en ? {fmt_if('test_io', c.pad_index, 'C', IDXW_O, 1)} : {c.default_in};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'OEN',   IDXW_O, FW_O)} = {fmt_vec(B+'_oen',  c.pad_index, IDXW_O)};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'I',     IDXW_O, FW_O)} = {fmt_vec(B+'_i',    c.pad_index, IDXW_O)};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'DS',    IDXW_O, FW_O)} = {fmt_vec(B+'_ds',   c.pad_index, IDXW_O)};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'PE_PU', IDXW_O, FW_O)} = {fmt_vec(B+'_pe_pu',c.pad_index, IDXW_O)};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'PS_PD', IDXW_O, FW_O)} = {fmt_vec(B+'_ps_pd',c.pad_index, IDXW_O)};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'ST',    IDXW_O, FW_O)} = {fmt_vec(B+'_st',   c.pad_index, IDXW_O)};")
                L.append(f"  assign {fmt_if('test_io', c.pad_index, 'IE',    IDXW_O, FW_O)} = {fmt_vec(B+'_ie',   c.pad_index, IDXW_O)};")
            else:
                if c.direction in ("I", "IO"):
                    L.append(f"  assign {b} = test_en ? {fmt_if('test_io', c.pad_index, 'C', IDXW_O, 1)} : {c.default_in};")
                    for fld, val in (
                        ("PE_PU", "TI_PE_PU"),
                        ("PS_PD", "TI_PS_PD"),
                        ("ST", "TI_ST"),
                        ("IE", "TI_IE"),
                        ("I", "TI_I"),
                        ("OEN", oen_expr(c, "TI_OEN")),
                        ("DS", "TI_DS"),
                    ):
                        L.append(f"  assign {fmt_if('test_io', c.pad_index, fld, IDXW_O, FW_O)} = {val};")
                if c.direction in ("O", "IO"):
                    L.append(f"  assign {fmt_if('test_io', c.pad_index, 'I', IDXW_O, FW_O)} = {b};")
                    for fld, val in (("PE_PU", "TO_PE_PU"), ("PS_PD", "TO_PS_PD"), ("ST", "TO_ST"), ("IE", "TO_IE"), ("OEN", oen_expr(c, "TO_OEN")), ("DS", "TO_DS")):
                        L.append(f"  assign {fmt_if('test_io', c.pad_index, fld, IDXW_O, FW_O)} = {val};")

    L.append("endmodule\n")
    return "\n".join(L)

