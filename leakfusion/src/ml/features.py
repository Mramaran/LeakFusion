"""Stage 3 feature engineering — build_feature_frame and helpers."""
from __future__ import annotations


EPSILON = 1e-6
LAMBDA_BASELINE = 1.4  # diesel cruise stoichiometry midpoint


def op_cell_id(rpm_bin: float, load_bin: float) -> int:
    """Deterministic int label for (rpm_bin, load_bin) pair.

    Hash via a stable formula so the same (rpm_bin, load_bin) always maps to
    the same int. Tree models treat this as categorical; identity matters,
    distance does not.
    """
    return int(round(float(rpm_bin) * 1000 + float(load_bin) * 1000))


def safe_ratio(numer: float, denom: float) -> float:
    """num / max(|denom|, EPSILON), preserving sign of denom."""
    if denom == 0.0:
        if numer == 0.0:
            return 0.0
        return numer / EPSILON
    if abs(denom) < EPSILON:
        return numer / (EPSILON if denom >= 0 else -EPSILON)
    return numer / denom


def thermal_gradient(t_exh_manifold: float, t_ats_inlet: float) -> float:
    return float(t_exh_manifold) - float(t_ats_inlet)


def lambda_deviation(lambda_sensor: float) -> float:
    return float(lambda_sensor) - LAMBDA_BASELINE


import hashlib
import numpy as np
import pandas as pd

from leakfusion.src.calibration.persist import load_calibration
from leakfusion.src.residuals.orchestrator import compute_residuals


FEATURE_COLUMNS = [
    "z_R1", "z_R2", "z_R3", "z_R4", "z_R5", "z_R6",
    "engine_rpm", "load_fraction", "op_point_extrapolated", "op_cell_id",
    "boost_minus_expected_norm", "exhaust_pressure_ratio", "thermal_gradient",
    "lambda_deviation", "maf_per_boost",
]
ZONE_NAMES = ["zone1", "zone2", "zone3a", "zone3b", "zone4"]


def _run_id(zone: str, severity: float, rpm_bin: float, load_bin: float) -> int:
    """Stable int hash of (zone, severity, rpm_bin, load_bin) for GroupKFold."""
    key = f"{zone}|{severity:.4f}|{rpm_bin:.1f}|{load_bin:.3f}"
    return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)


def _enrich_with_residuals(df: pd.DataFrame, calibration) -> pd.DataFrame:
    """Loop compute_residuals across rows; append z_R*, R*_raw, rpm_bin, load_bin, op_point_extrapolated."""
    enriched = df.reset_index(drop=True).copy()
    z_cols = {f"z_R{i}": [] for i in range(1, 7)}
    raw_cols = {f"R{i}_raw": [] for i in range(1, 7)}
    rpm_bins, load_bins, extrapolated = [], [], []
    for _, row in enriched.iterrows():
        out = compute_residuals(row, calibration)
        for i in range(1, 7):
            z = out["z_scores"][f"R{i}"]
            r = out["residuals"][f"R{i}"]
            z_cols[f"z_R{i}"].append(float(z) if z is not None else np.nan)
            raw_cols[f"R{i}_raw"].append(float(r) if r is not None else np.nan)
        rpm_bins.append(out["op_point"]["rpm_bin"])
        load_bins.append(out["op_point"]["load_bin"])
        extrapolated.append(bool(out["flags"]["op_point_extrapolated"]))
    for k, v in z_cols.items():
        enriched[k] = v
    for k, v in raw_cols.items():
        enriched[k] = v
    enriched["rpm_bin"] = rpm_bins
    enriched["load_bin"] = load_bins
    enriched["op_point_extrapolated"] = extrapolated
    return enriched


def build_feature_frame(
    df: pd.DataFrame,
    calibration_path: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """Build the 15-feature matrix + zone label + severity target + group keys.

    - Drops rows where leak_zone == "no_leak" (Stage 2 owns gating).
    - Computes Stage 1 residuals/z-scores via the orchestrator.
    - Adds op-point + zone-disambiguating ratio features.
    - Group key is a stable hash of (zone, severity, rpm_bin, load_bin).
    """
    calibration = load_calibration(calibration_path)
    df = df[df["leak_zone"] != "no_leak"].reset_index(drop=True).copy()

    # Stage 1 residuals — wraps the row-level compute_residuals into a frame.
    enriched = _enrich_with_residuals(df, calibration)

    feats = pd.DataFrame(index=enriched.index)
    for k in ["R1", "R2", "R3", "R4", "R5", "R6"]:
        feats[f"z_{k}"] = enriched[f"z_{k}"].fillna(0.0)
    feats["engine_rpm"] = enriched["engine_rpm"].astype(float)
    feats["load_fraction"] = enriched["load_fraction"].astype(float)
    feats["op_point_extrapolated"] = enriched["op_point_extrapolated"].astype(int)
    feats["op_cell_id"] = enriched.apply(
        lambda r: op_cell_id(r["rpm_bin"], r["load_bin"]), axis=1
    ).astype(int)

    # boost_minus_expected_norm = R2 / boost_expected. R2 = boost_actual - boost_expected,
    # so boost_expected = boost_actual - R2. Falls back to z_R2 / boost_actual if R2_raw is NaN.
    def _boost_norm(r):
        r2 = r.get("R2_raw")
        if r2 is None or pd.isna(r2):
            return safe_ratio(float(r["z_R2"]), float(r["boost_pressure"]))
        boost_expected = float(r["boost_pressure"]) - float(r2)
        return safe_ratio(float(r2), boost_expected)

    feats["boost_minus_expected_norm"] = enriched.apply(_boost_norm, axis=1)
    feats["exhaust_pressure_ratio"] = enriched.apply(
        lambda r: safe_ratio(float(r["exhaust_manifold_pressure"]), float(r["exhaust_backpressure"])),
        axis=1,
    )
    feats["thermal_gradient"] = enriched.apply(
        lambda r: thermal_gradient(float(r["t_exhaust_manifold"]), float(r["t_aftertreatment_inlet"])),
        axis=1,
    )
    feats["lambda_deviation"] = enriched["lambda_sensor"].apply(lambda x: lambda_deviation(float(x)))
    feats["maf_per_boost"] = enriched.apply(
        lambda r: safe_ratio(float(r["maf"]), float(r["boost_pressure"])),
        axis=1,
    )

    feats = feats[FEATURE_COLUMNS]

    y_zone = enriched["leak_zone"].to_numpy()
    y_sev = enriched["leak_severity"].astype(float).to_numpy()
    groups = np.array([
        _run_id(z, s, rb, lb)
        for z, s, rb, lb in zip(
            y_zone, y_sev, enriched["rpm_bin"].to_numpy(), enriched["load_bin"].to_numpy()
        )
    ])
    return feats, y_zone, y_sev, groups


def build_feature_row(residual_row, sensor_row) -> np.ndarray:
    """Build a single 15-element feature vector from a residuals row + sensor row.

    Used by run_stage2.py to compute Stage 3 features per row without re-running
    the Stage 1 orchestrator (residuals already computed in residuals.parquet).

    residual_row needs: z_R1..z_R6, R2 (raw), rpm_bin, load_bin, op_point_extrapolated.
    sensor_row needs: engine_rpm, load_fraction, boost_pressure, exhaust_manifold_pressure,
                       exhaust_backpressure, t_exhaust_manifold, t_aftertreatment_inlet,
                       lambda_sensor, maf.
    Returns: ndarray of shape (15,) in FEATURE_COLUMNS order.
    """
    def _g(row, key, default=0.0):
        v = row[key] if key in row else row.get(key, default) if hasattr(row, "get") else default
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return float(v)

    z = [_g(residual_row, f"z_R{i}", 0.0) for i in range(1, 7)]
    rpm = _g(sensor_row, "engine_rpm")
    load = _g(sensor_row, "load_fraction")
    extrap = int(bool(residual_row.get("op_point_extrapolated", False)
                      if hasattr(residual_row, "get") else residual_row["op_point_extrapolated"]))
    cell = op_cell_id(_g(residual_row, "rpm_bin", rpm),
                      _g(residual_row, "load_bin", load))

    r2_raw = residual_row["R2"] if "R2" in residual_row else None
    if r2_raw is None or (isinstance(r2_raw, float) and np.isnan(r2_raw)):
        boost_norm = safe_ratio(z[1], _g(sensor_row, "boost_pressure", 1.0))
    else:
        boost_actual = _g(sensor_row, "boost_pressure")
        boost_expected = boost_actual - float(r2_raw)
        boost_norm = safe_ratio(float(r2_raw), boost_expected)

    exh_ratio = safe_ratio(_g(sensor_row, "exhaust_manifold_pressure"),
                           _g(sensor_row, "exhaust_backpressure"))
    therm = thermal_gradient(_g(sensor_row, "t_exhaust_manifold"),
                             _g(sensor_row, "t_aftertreatment_inlet"))
    lam = lambda_deviation(_g(sensor_row, "lambda_sensor", LAMBDA_BASELINE))
    maf_per_boost = safe_ratio(_g(sensor_row, "maf"),
                               _g(sensor_row, "boost_pressure", 1.0))

    return np.array([*z, rpm, load, extrap, cell, boost_norm, exh_ratio, therm, lam, maf_per_boost],
                    dtype=float)
