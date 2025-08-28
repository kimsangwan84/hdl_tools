import re
from typing import Dict, List, Tuple

from ..models import ExcelModel
from ..utils import en_names_for_base, is_active_low_oe, is_io_test_name, sv_id
from .common import build_bus_maps_global


def gen_testbench_sv(model: ExcelModel, mode_maps) -> str:
    NI = len(model.pads_I)
    NO = len(model.pads_IO)
    g_sig_w, g_sig_dir, g_en_w = build_bus_maps_global(model.modes)

    def split_base_idx(pin: str):
        m = re.match(r"^(?P<base>[A-Za-z_]\w*)(?:\[(?P<idx>\d+)\])?$", pin)
        if not m:
            return pin, None
        base = m.group("base")
        idx = m.group("idx")
        return base, (int(idx) if idx is not None else None)

    in_pin_map: Dict[str, Tuple[str, int]] = {}
    for pr in model.pads_I:
        b, i = split_base_idx(pr.name)
        in_pin_map[pr.name] = (b, i)
    io_pin_map: Dict[str, Tuple[str, int]] = {}
    for pr in model.pads_IO:
        b, i = split_base_idx(pr.name)
        io_pin_map[pr.name] = (b, i)

    L: List[str] = []
    L.append("`timescale 1ns/1ps")
    L.append("")
    L.append("// Auto-generated smoke testbench for pad_mux")
    L.append("")
    L.append("module testbench;")
    L.append("")

    L.append("  // mode enables")
    L.append("  logic [31:0] normal_mode_enable;")
    L.append("  logic [15:0] scan_mode_enable;")
    L.append("  logic [15:0] ipdt_mode_enable;")
    L.append("")

    L.append("  // functional signals (drive 'input' as reg, monitor 'output' as wire)")
    func_inputs = []
    func_outputs = []
    for base, W in sorted(g_sig_w.items()):
        width = ("" if W <= 1 else f"[{W-1}:0]")
        b = sv_id(base)
        if g_sig_dir.get(base) == "input":
            L.append(f"  logic {width} {b};")
            func_inputs.append((base, W))
        else:
            L.append(f"  wire  {width} {b};")
            func_outputs.append((base, W))
    for base in sorted(g_sig_w.keys()):
        for eb in en_names_for_base(base, g_en_w):
            W = g_en_w[eb]
            width = ("" if W <= 1 else f"[{W-1}:0]")
            L.append(f"  logic {width} {sv_id(eb)};")
    L.append("")

    in_groups = {}
    for pr in model.pads_I:
        b, i = split_base_idx(pr.name)
        in_groups.setdefault(b, set()).add(i)
    for base, idxs in sorted(in_groups.items()):
        if None in idxs and len(idxs) == 1:
            L.append(f"  logic {sv_id(base)};")
        else:
            msb = max(i for i in idxs if i is not None)
            lsb = min(i for i in idxs if i is not None)
            L.append(f"  logic [{msb}:{lsb}] {sv_id(base)};")

    io_groups = {}
    for pr in model.pads_IO:
        b, i = split_base_idx(pr.name)
        io_groups.setdefault(b, set()).add(i)
    for base, idxs in sorted(io_groups.items()):
        b = sv_id(base)
        if None in idxs and len(idxs) == 1:
            L.append(f"  wire  {b};")
            L.append(f"  logic tb_{b}_drv, tb_{b}_oe;")
            L.append(f"  assign {b} = tb_{b}_oe ? tb_{b}_drv : 1'bz;")
        else:
            msb = max(i for i in idxs if i is not None)
            lsb = min(i for i in idxs if i is not None)
            L.append(f"  wire  [{msb}:{lsb}] {b};")
            L.append(f"  logic [{msb}:{lsb}] tb_{b}_drv, tb_{b}_oe;")
            L.append(f"  assign {b} = tb_{b}_oe ? tb_{b}_drv : 'bz;")
    if set(model.pads_OSC) >= {"XIN", "XOUT"}:
        L.append("  logic XIN;")
        L.append("  wire  XOUT;")

    L.append("")
    L.append("  // DUT")
    # optional note about io_test ports left unconnected
    has_io_test_any = any(any(is_io_test_name(sm.name) for sm in model.modes[m]) for m in ("normal", "scan", "ipdt"))
    if has_io_test_any:
        L.append("  // Note: pad_mux exposes io_test passthrough ports (io_test_osc_io, io_test_in, io_test_io)")
        L.append("  // These are intentionally left unconnected in this smoke testbench.")
    L.append("  pad_mux dut (")
    conns = []
    conns.append((".normal_mode_enable", "normal_mode_enable"))
    conns.append((".scan_mode_enable", "scan_mode_enable"))
    conns.append((".ipdt_mode_enable", "ipdt_mode_enable"))
    for base, _ in sorted(g_sig_w.items()):
        conns.append((f".{sv_id(base)}", sv_id(base)))
    for base in sorted(g_sig_w.keys()):
        for eb in en_names_for_base(base, g_en_w):
            conns.append((f".{sv_id(eb)}", sv_id(eb)))
    for base, _ in sorted(in_groups.items()):
        conns.append((f".{sv_id(base)}", sv_id(base)))
    for base, _ in sorted(io_groups.items()):
        conns.append((f".{sv_id(base)}", sv_id(base)))
    if set(model.pads_OSC) >= {"XIN", "XOUT"}:
        conns.append((".XIN", "XIN"))
        conns.append((".XOUT", "XOUT"))
    PW = max(len(p) for p, _ in conns)
    VW = max(len(v) for _, v in conns)
    for i, (p, v) in enumerate(conns):
        comma = "," if i < len(conns) - 1 else ""
        L.append(f"    {p.ljust(PW)} ( {v.ljust(VW)} ){comma}")
    L.append("  );")
    L.append("")

    L.append("  task automatic disable_all_modes();")
    L.append("    normal_mode_enable = '0;")
    L.append("    scan_mode_enable   = '0;")
    L.append("    ipdt_mode_enable   = '0;")
    L.append("  endtask")
    L.append("")

    L.append("  initial begin")
    L.append("    disable_all_modes();")
    for base in sorted(g_sig_w.keys()):
        for eb in en_names_for_base(base, g_en_w):
            L.append(f"    {sv_id(eb)} = '0;")
    for base, _ in sorted(io_groups.items()):
        b = sv_id(base)
        L.append(f"    tb_{b}_oe = '0; tb_{b}_drv = '0;")

    for base, W in func_outputs:
        if W <= 1:
            L.append(f"    if ({sv_id(base)} !== 1'b0) $error(\"[TB] default(all disable) | base={sv_id(base)} exp=0 got=%0b\", {sv_id(base)});")
        else:
            L.append(f"    if ({sv_id(base)} !== '0) $error(\"[TB] default(all disable) | base={sv_id(base)} exp=0\");")
    L.append("")

    for mode in ("normal", "scan", "ipdt"):
        subs = model.modes[mode]
        if not subs:
            continue
        subs = [sm for sm in subs if not is_io_test_name(sm.name)]
        for k, sm in enumerate(subs):
            L.append(f"    // ---- enable {mode}[{k}] : {sv_id(sm.name)} ----")
            L.append("    disable_all_modes();")
            if mode == "normal":
                L.append(f"    normal_mode_enable[{k}] = 1'b1;")
            elif mode == "scan":
                L.append(f"    scan_mode_enable[{k}]   = 1'b1;")
            else:
                L.append(f"    ipdt_mode_enable[{k}]   = 1'b1;")

            sm_bases = sorted({c.base for c in sm.cells})
            other_bases = [b for b, _ in func_outputs if b not in sm_bases]
            for b in other_bases:
                L.append(f"    logic [$bits({sv_id(b)})-1:0] snap_{sv_id(b)} = {sv_id(b)};")

            for c in sm.cells:
                bname = sv_id(c.base)
                idx = (f"[{c.base_idx}]" if c.base_idx is not None else "")
                if c.direction in ("O", "IO") and c.pad_kind in ("IO",):
                    if c.enable:
                        en_name = sv_id(c.enable.split("[")[0])
                        en_val_on = "1'b0" if is_active_low_oe(c.enable) else "1'b1"
                        if c.enable_idx is None:
                            L.append(f"    {en_name} = {en_val_on};")
                        else:
                            L.append(f"    {en_name}[{c.enable_idx}] = {en_val_on};")
                    L.append(f"    {bname}{idx} = 1'b0; #1; {bname}{idx} = 1'b1; #1; {bname}{idx} = 1'b0;")
                if c.direction in ("I", "IO"):
                    pbase, pidx = split_base_idx(c.pin_name)
                    pB = sv_id(pbase)
                    if c.pad_kind == "I":
                        tgt = (f"{pB}[{pidx}]" if pidx is not None else pB)
                        L.append(f"    {tgt} = 1'b0; #1; {tgt} = 1'b1; #1; {tgt} = 1'b0;")
                    else:
                        if pidx is None:
                            L.append(f"    tb_{pB}_oe = 1'b1; tb_{pB}_drv = 1'b0; #1; tb_{pB}_drv = 1'b1; #1; tb_{pB}_drv = 1'b0; tb_{pB}_oe = 1'b0;")
                        else:
                            L.append(
                                f"    tb_{pB}_oe[{pidx}] = 1'b1; tb_{pB}_drv[{pidx}] = 1'b0; #1; tb_{pB}_drv[{pidx}] = 1'b1; #1; tb_{pB}_drv[{pidx}] = 1'b0; tb_{pB}_oe[{pidx}] = 1'b0;"
                            )

            for b in other_bases:
                L.append(f"    if ({sv_id(b)} !== snap_{sv_id(b)}) $error(\"[TB] stable | mode={mode} sub={sv_id(sm.name)} base={sv_id(b)}\");")
            L.append("")

    L.append("    #10;")
    L.append("    $display(\"[TB] Full sequence run done\");")
    L.append("    $finish;")
    L.append("  end")
    L.append("")
    L.append("endmodule")

    return "\n".join(L)
