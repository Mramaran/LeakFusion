"""Build 4 demo CSV files from leak_labeled.parquet for the Streamlit UI.

Each CSV has the 17 sensor columns + synthesized timestamp + ground-truth
leak_zone and leak_severity columns. Length ~600 rows = 60s @ 10Hz.

Usage:
    python -m leakfusion.scripts.build_demo_samples
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pandas as pd

from leakfusion.src.schema import REQUIRED_COLUMNS


SAMPLE_SPECS: dict[str, dict] = {
    "healthy_run": {
        "zone": "no_leak", "severity": 0.0, "rpm_target": 1500, "load_fraction": 0.75,
    },
    "zone1_intake_leak": {
        "zone": "zone1", "severity": 0.10, "rpm_target": 1500, "load_fraction": 0.75,
    },
    "zone3a_exhaust_leak": {
        "zone": "zone3a", "severity": 0.05, "rpm_target": 1500, "load_fraction": 0.75,
    },
    "zone4_testcell_leak": {
        "zone": "zone4", "severity": 0.10, "rpm_target": 1500, "load_fraction": 0.75,
    },
}

_MAX_ROWS_PER_SAMPLE = 600
_HZ = 10.0
_RPM_TOLERANCE = 100.0  # +/- around rpm_target


def build_one(leak_parquet: Path, spec: dict, out_path: Path) -> int:
    df = pd.read_parquet(leak_parquet)
    rpm_lo = spec["rpm_target"] - _RPM_TOLERANCE
    rpm_hi = spec["rpm_target"] + _RPM_TOLERANCE
    mask = (
        (df["leak_zone"] == spec["zone"])
        & (df["engine_rpm"].between(rpm_lo, rpm_hi))
        & (df["load_fraction"] == spec["load_fraction"])
    )
    if spec["zone"] != "no_leak":
        mask &= (df["leak_severity"] == spec["severity"])
    slice_ = df[mask].head(_MAX_ROWS_PER_SAMPLE).reset_index(drop=True)

    if len(slice_) < 50:
        raise RuntimeError(
            f"Only {len(slice_)} rows match {spec}; need >=50. "
            f"Check that leak_labeled.parquet contains this op-point."
        )

    keep_cols = sorted(REQUIRED_COLUMNS) + ["leak_zone", "leak_severity"]
    out = slice_[keep_cols].copy()
    out["timestamp"] = [i / _HZ for i in range(len(out))]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return len(out)


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input", default="leakfusion/data/leak_labeled.parquet",
        help="Source parquet (must contain leak_zone, leak_severity, engine_rpm, load_fraction).",
    )
    ap.add_argument(
        "--out-dir", default="leakfusion/data/demo_samples",
        help="Output directory for the 4 CSVs.",
    )
    args = ap.parse_args()

    leak_parquet = Path(args.input)
    out_dir = Path(args.out_dir)

    for name, spec in SAMPLE_SPECS.items():
        out_path = out_dir / f"{name}.csv"
        n = build_one(leak_parquet, spec, out_path)
        print(f"  {out_path.name}: {n} rows")


if __name__ == "__main__":
    _main()
