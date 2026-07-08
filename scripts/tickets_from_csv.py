"""Convert an outage-ticket CSV into case YAMLs under outage_whatif/cases/.

Each row (an eNodeB outage ticket) becomes one case file that
outage_whatif.loop.case.CaseSpec can load.  Column names, budget, and
output directory are arguments so the CSV layout stays flexible.

Usage:
  python scripts/tickets_from_csv.py tickets.csv \
      --site-col enodeb --start-col start_time --end-col end_time \
      --budget 5000 [--out-dir outage_whatif/cases] [--prefix ticket]
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M")


def parse_time(raw: str) -> str:
    """Normalize a ticket timestamp to the ISO form CaseSpec expects."""
    raw = raw.strip()
    try:
        return datetime.fromisoformat(raw).isoformat(timespec="minutes")
    except ValueError:
        pass
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).isoformat(timespec="minutes")
        except ValueError:
            continue
    raise ValueError(f"unrecognized timestamp: {raw!r} "
                     f"(tried ISO + {TIME_FORMATS})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--site-col", required=True, help="eNodeB / site id column")
    ap.add_argument("--start-col", required=True, help="outage start column")
    ap.add_argument("--end-col", required=True, help="outage end column")
    ap.add_argument("--budget", type=float, required=True,
                    help="query budget per case")
    ap.add_argument("--out-dir", type=Path,
                    default=Path(__file__).parent.parent
                    / "outage_whatif" / "cases")
    ap.add_argument("--prefix", default="ticket", help="case name prefix")
    ap.add_argument("--kind", default="blind",
                    choices=["blind", "calibration"])
    args = ap.parse_args(argv)

    rows = list(csv.DictReader(args.csv_path.open()))
    if not rows:
        print("empty CSV", file=sys.stderr)
        return 1
    missing = {args.site_col, args.start_col, args.end_col} - set(rows[0])
    if missing:
        print(f"columns not in CSV: {sorted(missing)}; "
              f"found: {sorted(rows[0])}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(rows, start=1):
        name = f"{args.prefix}{i:02d}"
        text = (f"name: {name}\n"
                f"kind: {args.kind}\n"
                f"seed: {i}\n"
                f"budget: {args.budget}\n"
                f"outage_start: \"{parse_time(row[args.start_col])}\"\n"
                f"outage_end: \"{parse_time(row[args.end_col])}\"\n"
                f"target_site: \"{row[args.site_col].strip()}\"\n")
        path = args.out_dir / f"{name}_{args.kind}.yaml"
        path.write_text(text)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
