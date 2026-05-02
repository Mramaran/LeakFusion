"""Subsystem 1: Air Intake (Conservation of Mass).

Physics: MAF = eta_vol * V_d * (RPM/120) * rho_intake * 1000
Where rho_intake = P_boost / (R_air * T_after_CAC)
"""
import numpy as np
from src.constants import DISPLACEMENT_M3, R_AIR


def compute_air_intake(rpm: float, p_boost: float, t_after_cac: float,
                       p_amb: float, coeffs: dict) -> dict:
    """Compute air intake path sensor values.

    Args:
        rpm: Engine speed (RPM).
        p_boost: Boost pressure (kPa absolute) - from compressor subsystem.
        t_after_cac: Temperature after intercooler (K).
        p_amb: Ambient pressure (kPa).
        coeffs: Dict with keys a0, a1, a2, delta_P_filter.

    Returns:
        Dict with maf (g/s), compressor_inlet_pressure (kPa).
    """
    rpm_k = rpm / 1000.0  # RPM in thousands

    eta_vol = coeffs["a0"] + coeffs["a1"] * rpm_k + coeffs["a2"] * rpm_k ** 2
    eta_vol = np.clip(eta_vol, 0.3, 1.0)

    v_dot = eta_vol * DISPLACEMENT_M3 * (rpm / 120.0)  # m^3/s (4-stroke)
    rho_intake = (p_boost * 1000) / (R_AIR * t_after_cac)  # kPa->Pa, kg/m^3
    maf = v_dot * rho_intake * 1000  # kg/s -> g/s

    p_comp_in = p_amb - coeffs["delta_P_filter"]

    return {
        "maf": maf,
        "compressor_inlet_pressure": p_comp_in,
    }
