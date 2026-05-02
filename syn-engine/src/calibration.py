"""Calibrate synthetic engine coefficients against NavicEngine PUMA data.

Sequential calibration: Combustion -> Compressor -> Air Intake -> Exhaust -> Backpressure.
Each subsystem is fitted independently using scipy.optimize.minimize.
"""
import numpy as np
from scipy.optimize import minimize
from src.data_loader import extract_operating_points, load_puma_nominal
from src.constants import (
    NAVIC_SPEEDS, LHV_DIESEL, AFR_STOICH, ETA_MECHANICAL,
    ISENTROPIC_EXP_AIR, DISPLACEMENT_M3, R_AIR, CP_EXHAUST,
    RADIATION_LOSS_FRACTION, ISENTROPIC_EXP_EXHAUST,
)


def calibrate_from_navicengine() -> dict:
    """Calibrate all subsystem coefficients from NavicEngine data.

    Returns:
        Dict with keys:
            coefficients: {intake: {...}, compressor: {...}, ...}
            validation_errors: {speed: {sensor: error, ...}, ...}
            noise_stats: {sensor: std_dev, ...}
            correction_polys: {sensor: [alpha0, alpha1, alpha2], ...}
    """
    ops = extract_operating_points()

    # --- Step 1: Calibrate Combustion (Subsystem 3) ---
    comb_coeffs = _calibrate_combustion(ops)

    # --- Step 2: Calibrate Compressor (Subsystem 2) ---
    comp_coeffs = _calibrate_compressor(ops)

    # --- Step 3: Calibrate Air Intake (Subsystem 1) ---
    intake_coeffs = _calibrate_intake(ops, comp_coeffs)

    # --- Step 4: Calibrate Exhaust (Subsystem 4) ---
    exhaust_coeffs = _calibrate_exhaust(ops, comb_coeffs)

    # --- Step 5: Calibrate Backpressure (Subsystem 5) ---
    back_coeffs = _calibrate_backpressure(ops)

    coefficients = {
        "intake": intake_coeffs,
        "compressor": comp_coeffs,
        "combustion": comb_coeffs,
        "exhaust": exhaust_coeffs,
        "backpressure": back_coeffs,
    }

    # --- Validation ---
    validation_errors = _compute_validation_errors(ops, coefficients)

    # --- Statistical Correction ---
    correction_polys = _fit_statistical_correction(ops, coefficients)

    # --- Noise Stats ---
    noise_stats = _extract_noise_stats()

    return {
        "coefficients": coefficients,
        "validation_errors": validation_errors,
        "correction_polys": correction_polys,
        "noise_stats": noise_stats,
    }


def _calibrate_combustion(ops):
    """Fit c0, c1, eta_thermal from torque and fuel_flow measurements."""
    rpms = ops["speed_setpoint"].values
    torques = ops["torque"].values
    fuel_flows = ops["fuel_flow"].values  # g/s

    def objective(params):
        c0, c1, eta_th = params
        error = 0
        for rpm, torque_actual, ff_actual in zip(rpms, torques, fuel_flows):
            rpm_k = rpm / 1000.0
            ff_max_pred = c0 + c1 * rpm_k
            # Use actual fuel flow for torque prediction
            fuel_power = ff_actual * LHV_DIESEL
            brake_power = fuel_power * eta_th * ETA_MECHANICAL
            omega = rpm * 2 * np.pi / 60
            torque_pred = brake_power / omega
            error += (torque_pred - torque_actual) ** 2
            # Also fit fuel_flow_max to match actual
            error += ((ff_max_pred - ff_actual) * 10) ** 2  # weighted
        return error

    result = minimize(objective, x0=[0.5, 2.0, 0.38],
                      bounds=[(0.01, 5.0), (0.1, 5.0), (0.25, 0.50)],
                      method="L-BFGS-B")
    c0, c1, eta_th = result.x
    return {"c0": float(c0), "c1": float(c1), "eta_thermal": float(eta_th)}


def _calibrate_compressor(ops):
    """Fit compressor map and efficiency from boost pressure and temperature."""
    rpms = ops["speed_setpoint"].values
    mafs = ops["maf"].values
    boosts = ops["boost_pressure"].values
    p_ins = ops["compressor_inlet_pressure"].values
    t_ambs = ops["t_intake"].values
    t_boosts = ops["t_boost"].values

    def objective(params):
        b0, b1, maf_ref, eta_c, eta_ic, dp_ic = params
        error = 0
        for maf, boost, p_in, t_amb, t_boost_actual in zip(
            mafs, boosts, p_ins, t_ambs, t_boosts
        ):
            maf_ratio = maf / maf_ref
            pr = 1.0 + b0 * np.power(max(maf_ratio, 0.01), b1)
            p_comp_out = p_in * pr
            t_comp_ideal = t_amb * np.power(pr, ISENTROPIC_EXP_AIR)
            t_comp_out = t_amb + (t_comp_ideal - t_amb) / eta_c

            error += ((p_comp_out - boost) / 10) ** 2  # pressure error (scaled)
            error += ((t_comp_out - t_boost_actual) / 20) ** 2  # temp error (scaled)
        return error

    result = minimize(objective, x0=[1.0, 1.0, 30.0, 0.75, 0.85, 3.0],
                      bounds=[(0.1, 5.0), (0.3, 2.0), (5.0, 200.0),
                              (0.40, 0.95), (0.60, 0.98), (0.5, 15.0)],
                      method="L-BFGS-B")
    b0, b1, maf_ref, eta_c, eta_ic, dp_ic = result.x
    return {
        "b0": float(b0), "b1": float(b1), "MAF_ref": float(maf_ref),
        "eta_compressor": float(eta_c), "eta_intercooler": float(eta_ic),
        "delta_P_intercooler": float(dp_ic),
    }


def _calibrate_intake(ops, comp_coeffs):
    """Fit volumetric efficiency from MAF measurements."""
    rpms = ops["speed_setpoint"].values
    mafs = ops["maf"].values
    boosts = ops["boost_pressure"].values
    t_after_cacs = ops.get("t_after_intercooler",
                           ops.get("t_intake_manifold", None))
    if t_after_cacs is None:
        t_after_cacs = np.full(len(rpms), 300.0)
    else:
        t_after_cacs = t_after_cacs.values

    def objective(params):
        a0, a1, a2, dp_filter = params
        error = 0
        for rpm, maf_actual, p_boost, t_cac in zip(rpms, mafs, boosts, t_after_cacs):
            rpm_k = rpm / 1000.0
            eta_vol = a0 + a1 * rpm_k + a2 * rpm_k ** 2
            eta_vol = np.clip(eta_vol, 0.3, 1.0)
            v_dot = eta_vol * DISPLACEMENT_M3 * (rpm / 120.0)
            rho = (p_boost * 1000) / (R_AIR * t_cac)
            maf_pred = v_dot * rho * 1000
            error += (maf_pred - maf_actual) ** 2
        return error

    result = minimize(objective, x0=[0.85, 0.0, -0.01, 0.3],
                      bounds=[(0.2, 1.0), (-0.3, 0.3), (-0.1, 0.05), (0.05, 2.0)],
                      method="L-BFGS-B")
    a0, a1, a2, dp = result.x
    return {"a0": float(a0), "a1": float(a1), "a2": float(a2),
            "delta_P_filter": float(dp)}


def _calibrate_exhaust(ops, comb_coeffs):
    """Fit exhaust temperature and pressure models."""
    rpms = ops["speed_setpoint"].values
    mafs = ops["maf"].values
    torques = ops["torque"].values
    t_exh_mans = ops["t_exhaust_manifold"].values
    p_exh_mans = ops["exhaust_manifold_pressure"].values
    fuel_flows = ops["fuel_flow"].values
    p_ambs = ops["ambient_pressure"].values

    # Cylinder offsets: extract from one speed point
    cyl_cols = [f"t_exh_cyl_{i}" for i in range(1, 7)]
    offsets = [0.0] * 6
    if all(c in ops.columns for c in cyl_cols):
        mean_exh = ops[cyl_cols].mean(axis=1).iloc[0]
        for i, c in enumerate(cyl_cols):
            offsets[i] = float(ops[c].iloc[0] - mean_exh)

    def objective(params):
        cool_loss, e0, e1, eta_turb = params
        error = 0
        for rpm, maf, ff, torque, t_exh_actual, p_exh_actual, p_amb in zip(
            rpms, mafs, fuel_flows, torques, t_exh_mans, p_exh_mans, p_ambs
        ):
            fuel_power = ff * LHV_DIESEL
            q_brake = torque * rpm * 2 * np.pi / 60
            q_cool = fuel_power * cool_loss
            q_rad = fuel_power * RADIATION_LOSS_FRACTION
            q_exh = max(fuel_power - q_brake - q_cool - q_rad, 100)
            exhaust_flow_kgs = (maf + ff) / 1000.0
            t_exh_pred = 300.0 + q_exh / (exhaust_flow_kgs * CP_EXHAUST)
            p_exh_pred = p_amb + e0 * exhaust_flow_kgs ** 2 + e1

            error += ((t_exh_pred - t_exh_actual) / 30) ** 2
            error += ((p_exh_pred - p_exh_actual) / 10) ** 2
        return error

    result = minimize(objective, x0=[0.30, 150.0, 1.0, 0.72],
                      bounds=[(0.10, 0.45), (10.0, 1000.0), (0.0, 20.0), (0.50, 0.90)],
                      method="L-BFGS-B")
    cool_loss, e0, e1, eta_turb = result.x
    return {
        "coolant_loss_fraction": float(cool_loss),
        "e0": float(e0), "e1": float(e1),
        "eta_turbine": float(eta_turb),
        "cyl_offsets": offsets,
    }


def _calibrate_backpressure(ops):
    """Fit backpressure model from measured data."""
    mafs = ops["maf"].values
    fuel_flows = ops["fuel_flow"].values
    p_backs = ops["exhaust_backpressure"].values
    p_ambs = ops["ambient_pressure"].values
    rpms = ops["speed_setpoint"].values

    def objective(params):
        f0, f1 = params
        error = 0
        for maf, ff, p_back_actual, p_amb in zip(mafs, fuel_flows, p_backs, p_ambs):
            flow_kgs = (maf + ff) / 1000.0
            p_back_pred = p_amb + f0 * flow_kgs ** 2 + f1
            error += (p_back_pred - p_back_actual) ** 2
        return error

    result = minimize(objective, x0=[50.0, 0.5],
                      bounds=[(1.0, 500.0), (-5.0, 10.0)],
                      method="L-BFGS-B")
    f0, f1 = result.x

    # Oil and coolant: simple linear fits
    # These are secondary; use reasonable defaults if data missing
    h0, h1 = 150.0, 0.1
    g0 = 0.3

    return {"f0": float(f0), "f1": float(f1),
            "h0": h0, "h1": h1, "g0": g0}


def _compute_validation_errors(ops, coefficients):
    """Compare predictions vs measurements at each speed."""
    from src.subsystems.combustion import compute_combustion
    errors = {}
    for _, row in ops.iterrows():
        speed = int(row["speed_setpoint"])
        # Compute what load_fraction reproduces the actual fuel flow
        comb_coeffs = coefficients["combustion"]
        rpm_k = speed / 1000.0
        ff_max = comb_coeffs["c0"] + comb_coeffs["c1"] * rpm_k
        actual_ff = row["fuel_flow"]
        load_frac = min(actual_ff / ff_max, 1.0) if ff_max > 0 else 1.0

        comb = compute_combustion(
            maf=row["maf"], rpm=speed, load_fraction=load_frac,
            coeffs=comb_coeffs
        )
        errors[speed] = {
            "torque": comb["torque"] - row["torque"],
        }
    return errors


def _fit_statistical_correction(ops, coefficients):
    """Fit polynomial correction for each sensor: delta(RPM) = a0 + a1*RPM + a2*RPM^2."""
    # Placeholder - compute prediction errors at each speed and fit quadratic
    corrections = {}
    sensors = ["maf", "boost_pressure", "t_exhaust_manifold", "exhaust_manifold_pressure"]
    for sensor in sensors:
        corrections[sensor] = [0.0, 0.0, 0.0]  # no correction initially
    return corrections


def _extract_noise_stats() -> dict:
    """Extract per-sensor standard deviations from NavicEngine NOMINAL data."""
    df = load_puma_nominal(1000)
    noise = {}
    for col in ["maf", "fuel_flow", "boost_pressure", "exhaust_manifold_pressure",
                "exhaust_backpressure", "t_intake", "t_boost", "t_exhaust_manifold",
                "t_turbine_outlet", "torque"]:
        if col in df.columns:
            noise[col] = float(df[col].std())
    return noise
