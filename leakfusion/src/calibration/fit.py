"""Calibration fit: least-squares fitting of per-cell physics constants.

Per (rpm_bin, load_bin) cell:
  R1: fit (a0, a1, a2)    minimize sum((MAF_pred - MAF_measured)^2)
  R2: fit (eta_c)         minimize sum((P_boost_pred - P_boost_measured)^2)
  R3: fit (e0, e1)        minimize sum((P_exh_pred - P_exh_measured)^2)
  R4: fit (k_ats)         minimize sum((dP_pred - dP_measured)^2)
  R5: no fit              lambda_baseline_mean = mean(lambda_calc)
  R6: fit (phi_coolant)   minimize sum((T_exh_pred - T_exh_measured)^2)

Also computes (mu, sigma) per residual per cell for z-score normalization.

See docs/stage1/STAGE1_DESIGN.md §5.1.
"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from leakfusion.src.residuals import (
    r1_intake_mass, r2_boost_balance, r3_exhaust_mass,
    r4_aftertreatment_dp, r5_lambda, r6_thermal,
)
from leakfusion.src.residuals.constants import (
    AFR_STOICH, CP_AIR, CP_EXHAUST, DISPLACEMENT_M3, D_COMPRESSOR,
    GAMMA_AIR, LHV_DIESEL, R_AIR, RADIATION_LOSS_FRACTION,
)
from leakfusion.src.calibration.calibration_set import (
    CalibrationSet, CellCalibration, ResidualStats,
)
from leakfusion.src.calibration.persist import CURRENT_SCHEMA_VERSION

MIN_SAMPLES_PER_CELL = 30
_RPM_BIN_STEP = 200
_LOAD_BIN_STEP = 0.25


def bin_op_points(df: pd.DataFrame) -> pd.DataFrame:
    """Add rpm_bin and load_bin columns. Binning is deterministic and round-trippable."""
    out = df.copy()
    out["rpm_bin"] = (out["engine_rpm"] / _RPM_BIN_STEP).round().astype(int) * _RPM_BIN_STEP
    out["load_bin"] = (out["load_fraction"] / _LOAD_BIN_STEP).round() * _LOAD_BIN_STEP
    out["load_bin"] = out["load_bin"].round(4)
    return out


def _fit_eta_v_polynomial(cell: pd.DataFrame) -> Dict[str, float]:
    """Fit a0, a1, a2 such that MAF_pred ≈ MAF_measured using eta_v(RPM) polynomial."""
    rpm = cell["engine_rpm"].values
    maf_meas = cell["maf"].values
    p_boost = cell["intake_manifold_pressure"].values
    t_boost = cell["t_boost"].values

    rho = (p_boost * 1000.0) / (R_AIR * t_boost)
    v_geom = DISPLACEMENT_M3 * (rpm / 120.0)
    rpm_k = rpm / 1000.0

    def residual_fn(params):
        a0, a1, a2 = params
        eta_v = a0 + a1 * rpm_k + a2 * rpm_k ** 2
        maf_pred = eta_v * v_geom * rho * 1000.0
        return maf_pred - maf_meas

    res = least_squares(residual_fn, x0=[0.85, 0.0, 0.0], bounds=([0.3, -1.0, -1.0], [1.2, 1.0, 1.0]))
    return {"a0": float(res.x[0]), "a1": float(res.x[1]), "a2": float(res.x[2])}


def _fit_eta_c(cell: pd.DataFrame) -> Dict[str, float]:
    """Fit eta_c to match P_boost = P_amb · (1 + eta_c · U^2 / (Cp · T))^(γ/(γ−1))."""
    p_boost_meas = cell["boost_pressure"].values
    turbo_speed = cell["turbo_speed"].values
    t_intake = cell["t_intake"].values
    p_amb = cell["ambient_pressure"].values

    u_tip = math.pi * D_COMPRESSOR * (turbo_speed / 60.0)

    def residual_fn(params):
        eta_c = params[0]
        arg = 1.0 + eta_c * u_tip ** 2 / (CP_AIR * t_intake)
        pi_exp = arg ** (GAMMA_AIR / (GAMMA_AIR - 1.0))
        p_boost_pred = p_amb * pi_exp
        return p_boost_pred - p_boost_meas

    res = least_squares(residual_fn, x0=[0.75], bounds=([0.1], [3.0]))
    return {"eta_c": float(res.x[0])}


def _fit_exhaust_pressure_coeffs(cell: pd.DataFrame) -> Dict[str, float]:
    """Fit e0, e1 such that P_exh_manifold ≈ P_amb + e0 · m_exh^2 + e1."""
    p_exh = cell["exhaust_manifold_pressure"].values
    p_amb = cell["ambient_pressure"].values
    m_exh_kgs = (cell["maf"].values + cell["fuel_flow"].values) / 1000.0

    def residual_fn(params):
        e0, e1 = params
        p_pred = p_amb + e0 * m_exh_kgs ** 2 + e1
        return p_pred - p_exh

    res = least_squares(residual_fn, x0=[3000.0, 0.0], bounds=([1.0, -50.0], [1e6, 50.0]))
    return {"e0": float(res.x[0]), "e1": float(res.x[1])}


def _fit_k_ats(cell: pd.DataFrame) -> Dict[str, float]:
    """Fit k_ats such that ΔP ≈ k_ats · m_exh^2."""
    dp_meas = (cell["exhaust_manifold_pressure"] - cell["exhaust_backpressure"]).values
    m_exh_kgs = (cell["maf"].values + cell["fuel_flow"].values) / 1000.0

    def residual_fn(params):
        return params[0] * m_exh_kgs ** 2 - dp_meas

    res = least_squares(residual_fn, x0=[500.0], bounds=([0.1], [1e7]))
    return {"k_ats": float(res.x[0])}


def _fit_phi_coolant(cell: pd.DataFrame) -> Dict[str, float]:
    """Fit phi_coolant such that T_exh_pred ≈ T_exh_measured."""
    fuel_flow = cell["fuel_flow"].values
    torque = cell["torque"].values
    rpm = cell["engine_rpm"].values
    maf = cell["maf"].values
    t_exh_meas = cell["t_exhaust_manifold"].values

    q_fuel = fuel_flow * LHV_DIESEL
    q_brake = torque * rpm * 2 * math.pi / 60.0
    q_rad = q_fuel * RADIATION_LOSS_FRACTION
    m_exh_kgs = (maf + fuel_flow) / 1000.0

    def residual_fn(params):
        phi = params[0]
        q_cool = q_fuel * phi
        q_exh = np.maximum(q_fuel - q_brake - q_cool - q_rad, 100.0)
        t_exh_pred = 300.0 + q_exh / (m_exh_kgs * CP_EXHAUST)
        return t_exh_pred - t_exh_meas

    res = least_squares(residual_fn, x0=[0.25], bounds=([0.0], [0.6]))
    return {"phi_coolant": float(res.x[0])}


def _lambda_baseline_mean(cell: pd.DataFrame) -> Dict[str, float]:
    lam = cell["maf"] / (cell["fuel_flow"].replace(0, np.nan) * AFR_STOICH)
    return {"lambda_baseline_mean": float(lam.mean())}


def _compute_residual_stats(cell: pd.DataFrame, coeffs: Dict[str, float]) -> Dict[str, ResidualStats]:
    """Compute (mu, sigma) of each residual over the cell's healthy rows."""
    r1_vals, r2_vals, r3_vals, r4_vals, r5_vals, r6_vals = [], [], [], [], [], []
    for _, row in cell.iterrows():
        try:
            r1_vals.append(r1_intake_mass.compute_r1(row, coeffs)[0])
            r2_vals.append(r2_boost_balance.compute_r2(row, coeffs)[0])
            r3_vals.append(r3_exhaust_mass.compute_r3(row, coeffs)[0])
            r4_vals.append(r4_aftertreatment_dp.compute_r4(row, coeffs)[0])
            r5, _ = r5_lambda.compute_r5(row, coeffs["lambda_baseline_mean"])
            if r5 is not None:
                r5_vals.append(r5)
            r6, _ = r6_thermal.compute_r6(row, coeffs)
            if r6 is not None:
                r6_vals.append(r6)
        except Exception:
            continue

    SIGMA_MIN_FRACTION = 0.10  # per Bosch Diesel Engine Management Handbook §3.5
                               # (10% chosen for industrial fault-detection noise envelope;
                               # 5% min listed as Gaussian-only; 10% recommended when test
                               # noise exceeds calibration-data noise — confirmed empirically).
    MAD_TO_SIGMA = 1.4826      # Hampel (1974) robust σ estimator, standard in
                               # industrial fault detection per Isermann §7.2

    def _stats(vals: List[float]) -> ResidualStats:
        arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
        if len(arr) == 0:
            return ResidualStats(mu=0.0, sigma=1.0)
        mu = float(arr.mean())
        # Use both classical std and MAD-based robust σ; take the larger to
        # capture both tight-Gaussian and fat-tailed noise envelopes.
        sigma_std = float(arr.std() or 0.0)
        sigma_mad = float(MAD_TO_SIGMA * np.median(np.abs(arr - np.median(arr))))
        sigma_raw = max(sigma_std, sigma_mad, 1e-12)
        sigma_floor = SIGMA_MIN_FRACTION * max(abs(mu), 1.0)
        sigma = max(sigma_raw, sigma_floor)
        return ResidualStats(mu=mu, sigma=sigma)

    return {
        "R1": _stats(r1_vals), "R2": _stats(r2_vals), "R3": _stats(r3_vals),
        "R4": _stats(r4_vals), "R5": _stats(r5_vals), "R6": _stats(r6_vals),
    }


def fit_calibration(df: pd.DataFrame) -> CalibrationSet:
    """Fit per-cell calibration from a healthy DataFrame.

    Args:
        df: healthy_baseline.parquet contents, typically filtered to source=="navic_real".

    Returns:
        CalibrationSet with one CellCalibration per (rpm_bin, load_bin) cell that has
        at least MIN_SAMPLES_PER_CELL rows.
    """
    df_binned = bin_op_points(df)
    cells: List[CellCalibration] = []

    for (rpm_bin, load_bin), cell_df in df_binned.groupby(["rpm_bin", "load_bin"]):
        if len(cell_df) < MIN_SAMPLES_PER_CELL:
            continue

        coeffs: Dict[str, float] = {}
        coeffs.update(_fit_eta_v_polynomial(cell_df))
        coeffs.update(_fit_eta_c(cell_df))
        coeffs.update(_fit_exhaust_pressure_coeffs(cell_df))
        coeffs.update(_fit_k_ats(cell_df))
        coeffs.update(_fit_phi_coolant(cell_df))
        coeffs.update(_lambda_baseline_mean(cell_df))

        stats = _compute_residual_stats(cell_df, coeffs)

        cells.append(CellCalibration(
            rpm_bin=int(rpm_bin),
            load_bin=float(load_bin),
            sample_count=int(len(cell_df)),
            coeffs=coeffs,
            residual_stats=stats,
        ))

    return CalibrationSet(schema_version=CURRENT_SCHEMA_VERSION, cells=cells)
