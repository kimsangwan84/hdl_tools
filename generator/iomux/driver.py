import os
import sys
import zipfile
from typing import Dict, Optional, Set, Tuple

from .banner import set_gen_header
from .errors import SpecError
from .excel import find_header_row, load_grid, parse_sheet
from .models import ExcelModel
from .validate import validate
from .utils import padtype_key, sv_id, is_io_test_name
from .codegen.gen_mode_mux import gen_mode_mux_sv
from .codegen.gen_pad_mux import gen_pad_mux_sv
from .codegen.gen_tb import gen_testbench_sv


def run_generate(
    xlsx_path: str,
    outdir: str,
    pad_types: Dict[str, str],
    mux_exclude: Set[str],
    sheet: Optional[str] = None,
) -> Tuple[str, int, int]:
    try:
        import openpyxl
    except Exception:
        print("[U901] openpyxl import failed. Please `pip install openpyxl`.", file=sys.stderr)
        sys.exit(3)

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = None
    last_e: Optional[SpecError] = None
    if sheet:
        if sheet in wb.sheetnames:
            ws = wb[sheet]
        else:
            raise SpecError("F101", {"sheet": sheet})
    else:
        for cand in wb.worksheets:
            try:
                g = load_grid(cand)
                find_header_row(g)
                ws = cand
                break
            except SpecError as e:
                last_e = e
        if ws is None:
            raise last_e or SpecError("F101")

    model: ExcelModel = parse_sheet(ws, pad_types, mux_exclude)
    validate(model)

    set_gen_header({
        "input": os.path.basename(xlsx_path),
        "sheet": ws.title,
        "NI": str(len(model.pads_I)),
        "NO": str(len(model.pads_IO)),
    })

    os.makedirs(outdir, exist_ok=True)
    design_dir = os.path.join(outdir, "design")
    verif_dir = os.path.join(outdir, "verification")
    os.makedirs(design_dir, exist_ok=True)
    os.makedirs(verif_dir, exist_ok=True)

    NI = len(model.pads_I)
    NO = len(model.pads_IO)
    mode_maps = {}
    for mode in ("normal", "scan", "ipdt"):
        mdir = os.path.join(design_dir, mode)
        os.makedirs(mdir, exist_ok=True)
        text_mux, sig_w_map, sig_dir_map, en_w_map = gen_mode_mux_sv(mode, NI, NO, model.modes[mode])
        with open(os.path.join(mdir, f"{mode}_mux.sv"), "w", encoding="utf-8") as f:
            f.write(text_mux)
        mode_maps[mode] = (sig_w_map, sig_dir_map, en_w_map)
        for sm in model.modes[mode]:
            if is_io_test_name(sm.name):
                continue
            from .codegen.gen_submode import gen_submode_sv

            text_sm = gen_submode_sv(NI, NO, sm)
            with open(os.path.join(mdir, f"{sv_id(sm.name)}.sv"), "w", encoding="utf-8") as f:
                f.write(text_sm)

    text_top = gen_pad_mux_sv(model, mode_maps)
    with open(os.path.join(design_dir, "pad_mux.sv"), "w", encoding="utf-8") as f:
        f.write(text_top)

    tb_text = gen_testbench_sv(model, mode_maps)
    with open(os.path.join(verif_dir, "testbench.sv"), "w", encoding="utf-8") as f:
        f.write(tb_text)
    return ws.title, NI, NO

