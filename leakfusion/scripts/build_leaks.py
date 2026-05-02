"""Build the leak-labeled parquet using syn-engine's batch training data generator.

Wraps `SyntheticEngine.run()` over a (rpm x load x zone x severity) grid and reshapes
the output into our canonical schema with LABEL_COLUMNS (leak_zone, leak_severity,
load_fraction) attached.

Usage:
    python -m leakfusion.scripts.build_leaks --out leakfusion/data/leak_labeled.parquet
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT / "syn-engine") not in sys.path:
    sys.path.insert(0, str(_ROOT / "syn-engine"))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.synthetic_engine import SyntheticEngine  # noqa: E402
from leakfusion.src.schema import REQUIRED_COLUMNS  # noqa: E402
from leakfusion.src.syn_fill import _estimate_turbo_speed  # noqa: E402


AFR_STOICH = 14.5
INTERCOOLER_DP_KPA = 5.0
T_ATS_OFFSET_K = 30.0  # t_aftertreatment_inlet ~= t_turbine_outlet - 30K (post-turbine heat loss)

DEFAULT_GRID = {
    "rpms": [800, 1000, 1200, 1400, 1600, 1800, 2000, 2400],
    "loads": [0.25, 0.50, 0.75, 1.00],
    "zones": ["no_leak", "zone1", "zone2", "zone3a", "zone3b", "zone4"],
    "severities": [0.01, 0.02, 0.05, 0.10, 0.15],
    "samples_per_point": 100,
}


_engine_singleton: SyntheticEngine | None = None


def _get_engine() -> SyntheticEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = SyntheticEngine()
        _engine_singleton.calibrate()
    return _engine_singleton


def _run_point(rpm: float, load: float, zone: str, severity: float,
               samples: int, seed_offset: int) -> pd.DataFrame:
    engine = _get_engine()
    duration = samples / 10.0  # sample rate is 10 Hz
    df = engine.run(
        rpm=rpm, load_fraction=load, duration_seconds=duration,
        sample_rate_hz=10.0, seed=42 + seed_offset,
        leak_zone=zone,
        leak_severity=severity if zone != "no_leak" else 0.0,
    )
    df["leak_zone"] = zone
    df["leak_severity"] = severity if zone != "no_leak" else 0.0
    df["load_fraction"] = load
    return df


def _enrich_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns missing from raw syn-engine output."""
    if "lambda_sensor" not in df.columns:
        df["lambda_sensor"] = df["maf"] / (df["fuel_flow"].replace(0, np.nan) * AFR_STOICH)
    if "intake_manifold_pressure" not in df.columns:
        df["intake_manifold_pressure"] = df["boost_pressure"] - INTERCOOLER_DP_KPA
    if "t_aftertreatment_inlet" not in df.columns and "t_turbine_outlet" in df.columns:
        df["t_aftertreatment_inlet"] = df["t_turbine_outlet"] - T_ATS_OFFSET_K
    if "turbo_speed" not in df.columns:
        df["turbo_speed"] = [
            _estimate_turbo_speed(float(r), float(l))
            for r, l in zip(df["engine_rpm"], df["load_fraction"])
        ]
    return df


def build_leak_dataset(out_path: Path | str,
                       rpms: list[float] | None = None,
                       loads: list[float] | None = None,
                       zones: list[str] | None = None,
                       severities: list[float] | None = None,
                       samples_per_point: int | None = None) -> pd.DataFrame:
    rpms = rpms if rpms is not None else DEFAULT_GRID["rpms"]
    loads = loads if loads is not None else DEFAULT_GRID["loads"]
    zones = zones if zones is not None else DEFAULT_GRID["zones"]
    severities = severities if severities is not None else DEFAULT_GRID["severities"]
    samples = samples_per_point if samples_per_point is not None else DEFAULT_GRID["samples_per_point"]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    seed_offset = 0
    for rpm in rpms:
        for load in loads:
            # no_leak once per (rpm, load)
            frames.append(_run_point(rpm, load, "no_leak", 0.0, samples, seed_offset))
            seed_offset += 1
            # Each non-no_leak zone x severity
            for zone in zones:
                if zone == "no_leak":
                    continue
                for sev in severities:
                    frames.append(_run_point(rpm, load, zone, sev, samples, seed_offset))
                    seed_offset += 1

    df = pd.concat(frames, ignore_index=True)
    df = _enrich_derived_columns(df)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise RuntimeError(f"syn-engine output missing required cols: {missing}")

    keep = list(REQUIRED_COLUMNS) + ["load_fraction", "leak_zone", "leak_severity"]
    if "timestamp" in df.columns:
        keep.append("timestamp")
    df = df[[c for c in keep if c in df.columns]]

    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df):,} rows to {out_path}")
    return df


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="leakfusion/data/leak_labeled.parquet")
    ap.add_argument("--samples", type=int, default=DEFAULT_GRID["samples_per_point"])
    args = ap.parse_args()
    build_leak_dataset(out_path=args.out, samples_per_point=args.samples)


if __name__ == "__main__":
    _main()
