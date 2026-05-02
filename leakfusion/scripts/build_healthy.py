"""Build the healthy baseline parquet from NavicEngine NOMINAL files.

Pipeline:
  1. Load each SPEED_{N}_NOMINAL.xlsx via syn-engine's loader (SI conversion).
  2. Filter to steady-state windows.
  3. Add load_fraction from (rpm, fuel_flow).
  4. Enrich with synthetic turbo_speed and t_aftertreatment_inlet.
  5. Compute lambda_sensor = MAF / (fuel_flow * 14.5).
  6. Compute intake_manifold_pressure = boost_pressure - intercooler_dp (assumed 5 kPa).
  7. Ensure all REQUIRED_COLUMNS present, drop NaN, write parquet.

Usage:
    python -m leakfusion.scripts.build_healthy --out leakfusion/data/healthy_baseline.parquet
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

# Ensure syn-engine importable when run as script
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT / "syn-engine") not in sys.path:
    sys.path.insert(0, str(_ROOT / "syn-engine"))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data_loader import load_puma_nominal  # noqa: E402

from leakfusion.src.steady_state import filter_steady_state  # noqa: E402
from leakfusion.src.load_estimator import add_load_fraction_column  # noqa: E402
from leakfusion.src.syn_fill import fill_missing_columns, build_syn_baseline_rows  # noqa: E402
from leakfusion.src.schema import REQUIRED_COLUMNS  # noqa: E402


INTERCOOLER_DP_KPA = 5.0  # Typical intercooler pressure drop, assumed constant
AFR_STOICH = 14.5

# Default augmentation grid mirrors leak_labeled.parquet's grid so Phase 2 regressors
# see every (rpm, load) cell the Phase 3 classifier will encounter.
DEFAULT_AUG_RPMS = [800.0, 1000.0, 1200.0, 1400.0, 1600.0, 1800.0, 2000.0, 2400.0]
DEFAULT_AUG_LOADS = [0.25, 0.50, 0.75, 1.00]
DEFAULT_AUG_SAMPLES_PER_CELL = 100


def _enrich_one_speed(speed: int) -> pd.DataFrame:
    df = load_puma_nominal(speed)
    df = filter_steady_state(df, window=10, rpm_tol=50.0, torque_tol_pct=5.0)
    if df.empty:
        return df

    df = add_load_fraction_column(df)
    df = fill_missing_columns(df)

    # Derived: lambda_sensor (ratio), intake_manifold_pressure (kPa)
    df["lambda_sensor"] = df["maf"] / (df["fuel_flow"].replace(0, np.nan) * AFR_STOICH)
    df["intake_manifold_pressure"] = df["boost_pressure"] - INTERCOOLER_DP_KPA

    return df


def build_healthy_baseline(out_path: Path | str,
                           speeds: list[int] | None = None,
                           aug_rpms: list[float] | None = None,
                           aug_loads: list[float] | None = None,
                           aug_samples_per_cell: int | None = None) -> pd.DataFrame:
    """Build the healthy baseline parquet (hybrid real + syn_baseline).

    Real NavicEngine NOMINAL rows are tagged `source="navic_real"`.
    Syn-engine samples at the requested (rpm, load) grid are tagged
    `source="syn_baseline"`. If all three `aug_*` args are None, no
    augmentation is done (caller gets real-only — used by fast unit tests).

    Returns the DataFrame written.
    """
    speeds = speeds if speeds is not None else [1000, 1200, 1400, 1600]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Real NavicEngine rows ---
    frames = [_enrich_one_speed(s) for s in speeds]
    frames = [f for f in frames if not f.empty]
    if not frames:
        raise RuntimeError("No steady-state rows found for any requested speed")

    real = pd.concat(frames, ignore_index=True)
    missing = REQUIRED_COLUMNS - set(real.columns)
    if missing:
        raise RuntimeError(f"Required columns missing after enrichment: {missing}")
    real = real.dropna(subset=list(REQUIRED_COLUMNS))
    real["source"] = "navic_real"

    keep = list(REQUIRED_COLUMNS | {"load_fraction", "source"})
    if "recorder_time" in real.columns:
        real = real.rename(columns={"recorder_time": "timestamp"})
        keep.append("timestamp")
    real = real[[c for c in keep if c in real.columns]]

    # --- Syn-engine augmentation (opt-in via aug_* args) ---
    do_aug = aug_rpms is not None or aug_loads is not None or aug_samples_per_cell is not None
    if do_aug:
        aug_rpms = aug_rpms if aug_rpms is not None else DEFAULT_AUG_RPMS
        aug_loads = aug_loads if aug_loads is not None else DEFAULT_AUG_LOADS
        aug_samples_per_cell = (aug_samples_per_cell
                                if aug_samples_per_cell is not None
                                else DEFAULT_AUG_SAMPLES_PER_CELL)

        syn = build_syn_baseline_rows(
            rpms=aug_rpms, loads=aug_loads,
            samples_per_cell=aug_samples_per_cell,
        )
        syn["source"] = "syn_baseline"
        syn = syn[[c for c in keep if c in syn.columns]]
        # Require same required columns on syn path
        syn_missing = REQUIRED_COLUMNS - set(syn.columns)
        if syn_missing:
            raise RuntimeError(f"syn_baseline rows missing required cols: {syn_missing}")
        syn = syn.dropna(subset=list(REQUIRED_COLUMNS))
        df = pd.concat([real, syn], ignore_index=True)
    else:
        df = real

    df.to_parquet(out_path, index=False)
    n_real = int((df["source"] == "navic_real").sum())
    n_syn = int((df["source"] == "syn_baseline").sum())
    print(f"Wrote {len(df):,} rows to {out_path} "
          f"(navic_real={n_real:,}, syn_baseline={n_syn:,})")
    return df


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="leakfusion/data/healthy_baseline.parquet",
                    help="Output parquet path")
    ap.add_argument("--speeds", nargs="+", type=int, default=[1000, 1200, 1400, 1600],
                    help="Which NavicEngine NOMINAL speeds to include")
    ap.add_argument("--aug-rpms", nargs="+", type=float, default=DEFAULT_AUG_RPMS,
                    help="RPM grid for syn-engine augmentation (matches leaky grid by default)")
    ap.add_argument("--aug-loads", nargs="+", type=float, default=DEFAULT_AUG_LOADS,
                    help="Load-fraction grid for syn-engine augmentation")
    ap.add_argument("--aug-samples", type=int, default=DEFAULT_AUG_SAMPLES_PER_CELL,
                    help="Syn-baseline samples per (rpm, load) cell")
    ap.add_argument("--no-aug", action="store_true",
                    help="Disable syn-engine augmentation (real NavicEngine rows only)")
    args = ap.parse_args()

    aug_rpms = None if args.no_aug else args.aug_rpms
    aug_loads = None if args.no_aug else args.aug_loads
    aug_samples = None if args.no_aug else args.aug_samples

    build_healthy_baseline(
        out_path=args.out, speeds=args.speeds,
        aug_rpms=aug_rpms, aug_loads=aug_loads,
        aug_samples_per_cell=aug_samples,
    )


if __name__ == "__main__":
    _main()
