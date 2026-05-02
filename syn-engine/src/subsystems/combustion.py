"""Subsystem 3: Combustion (Energy Balance).

Physics: fuel_power = fuel_flow * LHV; brake_power = fuel_power * eta_th * eta_mech
"""
import numpy as np
from src.constants import LHV_DIESEL, AFR_STOICH, ETA_MECHANICAL


def compute_combustion(maf: float, rpm: float, load_fraction: float,
                       coeffs: dict) -> dict:
    """Compute combustion chamber outputs.

    Args:
        maf: Mass air flow (g/s).
        rpm: Engine speed (RPM).
        load_fraction: Load as fraction (0.0 to 1.0).
        coeffs: Dict with keys c0, c1, eta_thermal.

    Returns:
        Dict with fuel_flow (g/s), torque (Nm), lambda_calculated,
        fuel_power (W).
    """
    rpm_k = rpm / 1000.0
    fuel_flow_max = coeffs["c0"] + coeffs["c1"] * rpm_k
    fuel_flow = max(load_fraction * fuel_flow_max, 0.01)  # avoid division by zero

    lambda_calc = maf / (fuel_flow * AFR_STOICH)

    fuel_power = fuel_flow * LHV_DIESEL  # W (since fuel_flow in g/s and LHV in J/g)
    brake_power = fuel_power * coeffs["eta_thermal"] * ETA_MECHANICAL

    omega = rpm * 2 * np.pi / 60  # rad/s
    torque = brake_power / omega if omega > 0 else 0.0

    return {
        "fuel_flow": fuel_flow,
        "torque": torque,
        "lambda_calculated": lambda_calc,
        "fuel_power": fuel_power,
    }
