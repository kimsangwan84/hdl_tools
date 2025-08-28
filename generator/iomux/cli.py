import argparse
import os
import sys
import zipfile

from .driver import run_generate
from .errors import SpecError
from .utils import padtype_key


def main():
    ap = argparse.ArgumentParser(description="IO Mux generator (Excel -> SystemVerilog)")
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--sheet")
    ap.add_argument("-pad_type", dest="pad_types", nargs=2, action="append", default=[], metavar=("PAD_CELL_NAME", "DIR"))
    ap.add_argument("-mux_exclude", dest="exclude", action="append", default=[])
    ap.add_argument("--zip", dest="zip_path")
    args = ap.parse_args()

    if not args.pad_types:
        raise SpecError("P201")
    pad_map = {padtype_key(n): d.upper() for (n, d) in args.pad_types}
    sheet, NI, NO = run_generate(args.input, args.outdir, pad_map, set(args.exclude or []), sheet=args.sheet)

    if args.zip_path:
        with zipfile.ZipFile(args.zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(args.outdir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    z.write(fp, arcname=os.path.relpath(fp, args.outdir))
    print(f"[OK] sheet={sheet} NI={NI} NO={NO} outdir={args.outdir}")


if __name__ == "__main__":
    try:
        main()
    except SpecError as e:
        print(e.pretty(), file=sys.stderr)
        sys.exit(3)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[U901] {e}", file=sys.stderr)
        sys.exit(3)

