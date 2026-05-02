"""CLI: fit Stage 1 calibration from healthy_baseline.parquet.

Usage:
    python -m leakfusion.scripts.fit_calibration \\
        --input leakfusion/data/healthy_baseline.parquet \\
        --out leakfusion/models/calibration.json
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pandas as pd

from leakfusion.src.calibration.fit import fit_calibration
from leakfusion.src.calibration.persist import save_calibration


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="leakfusion/data/healthy_baseline.parquet")
    ap.add_argument("--out", default="leakfusion/models/calibration.json")
    ap.add_argument("--source-filter", default="navic_real",
                    help="Filter rows by source column value. Use 'all' to disable.")
    args = ap.parse_args()

    df = pd.read_parquet(args.input)
    if args.source_filter != "all" and "source" in df.columns:
        df = df[df["source"] == args.source_filter].copy()
        print(f"Filtered to source=={args.source_filter}: {len(df):,} rows")

    cs = fit_calibration(df)
    out_path = Path(args.out)
    save_calibration(cs, out_path)
    print(f"Wrote {len(cs.cells)} cells to {out_path}")

    for c in cs.cells[:5]:
        print(f"  ({c.rpm_bin}, {c.load_bin:.2f}): n={c.sample_count}, "
              f"eta_c={c.coeffs['eta_c']:.3f}, phi_coolant={c.coeffs['phi_coolant']:.3f}")


if __name__ == "__main__":
    _main()
