"""CLI: compute residuals over the entire leak_labeled.parquet.

Usage:
    python -m leakfusion.scripts.compute_residuals_batch \\
        --input leakfusion/data/leak_labeled.parquet \\
        --calibration leakfusion/models/calibration.json \\
        --out leakfusion/data/residuals.parquet
"""
from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from leakfusion.src.calibration.persist import load_calibration
from leakfusion.src.residuals.orchestrator import compute_residuals


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="leakfusion/data/leak_labeled.parquet")
    ap.add_argument("--calibration", default="leakfusion/models/calibration.json")
    ap.add_argument("--out", default="leakfusion/data/residuals.parquet")
    args = ap.parse_args()

    df = pd.read_parquet(args.input)
    cs = load_calibration(args.calibration)

    records = []
    for idx, row in df.iterrows():
        try:
            out = compute_residuals(row, cs)
            rec = {"row_index": idx}
            rec.update({f"R{i}": out["residuals"][f"R{i}"] for i in range(1, 7)})
            rec.update({f"z_R{i}": out["z_scores"][f"R{i}"] for i in range(1, 7)})
            rec["op_point_extrapolated"] = out["flags"]["op_point_extrapolated"]
            rec["rpm_bin"] = out["op_point"]["rpm_bin"]
            rec["load_bin"] = out["op_point"]["load_bin"]
            if "leak_zone" in row:
                rec["leak_zone"] = row["leak_zone"]
            if "leak_severity" in row:
                rec["leak_severity"] = row["leak_severity"]
            records.append(rec)
        except Exception as e:
            records.append({"row_index": idx, "error": str(e)})

    out_df = pd.DataFrame(records)
    out_df.to_parquet(args.out, index=False)
    print(f"Wrote {len(out_df):,} rows to {args.out}")
    if "leak_zone" in out_df.columns:
        print("\nMean z-score per leak zone:")
        for rk in [f"z_R{i}" for i in range(1, 7)]:
            print(f"\n  {rk}:")
            print(out_df.groupby("leak_zone")[rk].mean().round(2))


if __name__ == "__main__":
    _main()
