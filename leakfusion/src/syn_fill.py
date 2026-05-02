"""Synthetic fill-in for columns NavicEngine does not record.

Uses syn-engine's physics simulator to derive turbo_speed and t_aftertreatment_inlet
at each (rpm, load_fraction) operating point. Deterministic: the same op point always
produces the same fill-in, so training and inference agree.
"""
import hashlib
from functools import lru_cache
from pathlib import Path
import sys

import pandas as pd

# Ensure syn-engine is importable
_SYN_ENGINE_PATH = Path(__file__).parent.parent.parent / "syn-engine"
if str(_SYN_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(_SYN_ENGINE_PATH))

from src.synthetic_engine import SyntheticEngine  # noqa: E402


_engine_singleton: SyntheticEngine | None = None


def _get_engine() -> SyntheticEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = SyntheticEngine()
        _engine_singleton.calibrate()
    return _engine_singleton


def deterministic_seed(rpm: float, load_fraction: float) -> int:
    """Derive a stable 32-bit int seed from an operating point."""
    key = f"{round(rpm, 1)}|{round(load_fraction, 4)}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


@lru_cache(maxsize=4096)
def _sample_op_point(rpm: float, load_fraction: float) -> tuple[float, float]:
    """Run syn-engine at (rpm, load_fraction), return (turbo_speed, t_aftertreatment_inlet).

    Cached to avoid re-running the simulator for repeated op points.
    """
    engine = _get_engine()
    seed = deterministic_seed(rpm, load_fraction)
    df = engine.run(rpm=rpm, load_fraction=load_fraction,
                    duration_seconds=1.0, sample_rate_hz=10.0, seed=seed)
    # syn-engine currently emits t_turbine_outlet; t_aftertreatment_inlet is ~30K below it
    # (typical post-turbine heat loss to DOC inlet). This is a physics approximation
    # until syn-engine exposes the column directly.
    ts = float(df["turbo_speed"].iloc[0]) if "turbo_speed" in df.columns else _estimate_turbo_speed(rpm, load_fraction)
    t_ats = float(df["t_turbine_outlet"].iloc[0]) - 30.0
    return ts, t_ats


def _estimate_turbo_speed(rpm: float, load_fraction: float) -> float:
    """Fallback physics estimate when syn-engine does not emit turbo_speed directly.

    Empirical correlation for a Navistar-class dual-stage turbo:
        turbo_speed ≈ 60,000 * (rpm/1600) * (0.5 + 0.5*load_fraction)  [RPM]
    """
    return 60_000.0 * (rpm / 1600.0) * (0.5 + 0.5 * load_fraction)


AFR_STOICH = 14.5
INTERCOOLER_DP_KPA = 5.0
T_ATS_OFFSET_K = 30.0


def _enrich_syn_row_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    """Add columns the syn-engine does not emit directly (lambda, IM pressure, T_ATS, turbo_speed)."""
    import numpy as np
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


def build_syn_baseline_rows(rpms: list[float],
                            loads: list[float],
                            samples_per_cell: int = 100,
                            seed_base: int = 9_999) -> pd.DataFrame:
    """Generate syn-engine no_leak samples across a (rpm, load) grid.

    Produces a DataFrame ready for concatenation into the healthy baseline.
    Each row carries a fixed `load_fraction` equal to the requested grid load
    (not the noisy syn-engine internal value) so that grid-coverage checks work.

    Args:
        rpms: Engine RPM setpoints.
        loads: Load fractions in [0, 1].
        samples_per_cell: Rows per (rpm, load) cell.
        seed_base: Offset so these seeds do not collide with leak dataset seeds.

    Returns:
        DataFrame with REQUIRED_COLUMNS + load_fraction (and optionally timestamp).
    """
    engine = _get_engine()
    duration = samples_per_cell / 10.0  # 10 Hz sample rate
    frames: list[pd.DataFrame] = []
    offset = 0
    for rpm in rpms:
        for load in loads:
            df = engine.run(
                rpm=float(rpm), load_fraction=float(load),
                duration_seconds=duration, sample_rate_hz=10.0,
                seed=seed_base + offset,
                leak_zone="no_leak", leak_severity=0.0,
            )
            df["load_fraction"] = float(load)
            frames.append(df)
            offset += 1
    out = pd.concat(frames, ignore_index=True)
    out = _enrich_syn_row_columns(out)
    return out


def fill_missing_columns(df: pd.DataFrame,
                         rpm_col: str = "engine_rpm",
                         load_col: str = "load_fraction") -> pd.DataFrame:
    """Add turbo_speed and t_aftertreatment_inlet columns via syn-engine physics.

    Args:
        df: DataFrame with engine_rpm and load_fraction columns.
        rpm_col: Name of the RPM column.
        load_col: Name of the load fraction column.

    Returns:
        Copy of df with two new columns.
    """
    if rpm_col not in df.columns or load_col not in df.columns:
        raise KeyError(f"df must have {rpm_col} and {load_col} columns")

    out = df.copy()
    turbo = []
    t_ats = []
    for rpm, load in zip(out[rpm_col], out[load_col]):
        ts, tats = _sample_op_point(float(rpm), float(load))
        turbo.append(ts)
        t_ats.append(tats)
    out["turbo_speed"] = turbo
    out["t_aftertreatment_inlet"] = t_ats
    return out
