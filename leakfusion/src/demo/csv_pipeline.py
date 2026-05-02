"""CSV upload pipeline: validate -> Stage 1 residuals -> Stage 2 CUSUM -> Stage 3 ML."""
from __future__ import annotations

import pandas as pd

from leakfusion.src.schema import REQUIRED_COLUMNS


class CsvValidationError(ValueError):
    """Raised when an uploaded CSV does not conform to the expected schema."""


_MIN_ROWS = 50
_MAX_ROWS = 1000


_RANGE: dict[str, tuple[float, float]] = {
    "engine_rpm": (0, 3000),
    "torque": (-200, 3000),
    "maf": (0, 600),
    "boost_pressure": (60, 400),
    "intake_manifold_pressure": (60, 400),
    "turbo_speed": (0, 200000),
    "exhaust_manifold_pressure": (60, 500),
    "exhaust_backpressure": (60, 400),
    "fuel_flow": (0, 100),
    "lambda_sensor": (0.5, 5.0),
    "t_intake": (250, 400),
    "t_boost": (250, 500),
    "t_exhaust_manifold": (273, 1300),
    "t_turbine_outlet": (273, 1100),
    "t_aftertreatment_inlet": (273, 1000),
    "ambient_pressure": (60, 110),
    "ambient_temperature": (220, 330),
}
_NEG_DISALLOWED = {
    "boost_pressure", "intake_manifold_pressure", "exhaust_manifold_pressure",
    "exhaust_backpressure", "ambient_pressure",
    "engine_rpm", "maf", "fuel_flow", "turbo_speed",
}


def validate_csv(df: pd.DataFrame) -> list[str]:
    """Return list of human-readable error strings. Empty list = valid."""
    errors: list[str] = []

    n = len(df)
    if n < _MIN_ROWS:
        errors.append(f"Need at least 50 rows (5 seconds at 10 Hz); got {n}")

    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    for col in missing:
        errors.append(f"Missing column: {col}")
    if missing:
        return errors

    for col in REQUIRED_COLUMNS:
        coerced = pd.to_numeric(df[col], errors="coerce")
        bad_idx = coerced.isna() & df[col].notna()
        for i in df.index[bad_idx][:3]:
            errors.append(f"Column {col} row {i} is not numeric: {df[col].iloc[i]!r}")
        if bad_idx.any():
            continue

        if col in _NEG_DISALLOWED and (coerced < 0).any():
            errors.append(f"Column {col} has negative values")

        lo, hi = _RANGE[col]
        out = (coerced < lo) | (coerced > hi)
        for i in df.index[out][:3]:
            errors.append(
                f"Column {col} row {i} = {coerced.iloc[i]} (plausible range {lo}-{hi})"
            )

    return errors


def _inject_timestamp(df: pd.DataFrame, hz: float = 10.0) -> pd.DataFrame:
    """If 'timestamp' column missing, synthesize it at fixed sample rate (default 10 Hz)."""
    if "timestamp" in df.columns:
        return df
    out = df.copy()
    out["timestamp"] = [i / hz for i in range(len(out))]
    return out


from leakfusion.src.calibration.calibration_set import CalibrationSet
from leakfusion.src.load_estimator import add_load_fraction_column
from leakfusion.src.residuals.orchestrator import compute_residuals


def process_sensor_csv(
    csv_df: pd.DataFrame,
    calibration: CalibrationSet,
    cusum_config: dict,
    predictor=None,
    persistence_seconds: float = 3.0,
) -> tuple[pd.DataFrame, list[dict]]:
    """Validate, compute residuals, run Stage 2 + (optional) Stage 3.

    Returns (residuals_df with z_R1..z_R6 + bookkeeping cols, list of AlertEvent dicts).
    Raises CsvValidationError on schema/range errors.
    """
    errors = validate_csv(csv_df)
    if errors:
        raise CsvValidationError("; ".join(errors))

    df = csv_df.copy()
    if len(df) > _MAX_ROWS:
        df = df.iloc[:_MAX_ROWS].copy()

    df = _inject_timestamp(df)

    if "load_fraction" not in df.columns:
        df = add_load_fraction_column(df)

    records = []
    for idx, row in df.iterrows():
        out = compute_residuals(row, calibration)
        rec = {"row_index": idx}
        rec.update({f"R{i}": out["residuals"][f"R{i}"] for i in range(1, 7)})
        rec.update({f"z_R{i}": out["z_scores"][f"R{i}"] for i in range(1, 7)})
        rec["op_point_extrapolated"] = out["flags"]["op_point_extrapolated"]
        rec["rpm_bin"] = out["op_point"]["rpm_bin"]
        rec["load_bin"] = out["op_point"]["load_bin"]
        rec["leak_zone"] = str(row.get("leak_zone", "unknown"))
        rec["leak_severity"] = float(row.get("leak_severity", 0.0))
        records.append(rec)
    residuals_df = pd.DataFrame(records)

    from leakfusion.scripts.run_stage2 import run_stage2
    events = run_stage2(
        residuals_df,
        cusum_config,
        persistence_seconds=persistence_seconds,
        predictor=predictor,
        source_df=df.reset_index(drop=True) if predictor is not None else None,
    )

    return residuals_df, events
