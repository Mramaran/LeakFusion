"""Subsystem 2: Turbo Compressor (Isentropic Relation).

Physics: T2/T1 = (P2/P1)^((gamma-1)/gamma) with isentropic efficiency.
"""
import numpy as np
from src.constants import ISENTROPIC_EXP_AIR


def compute_compressor(maf: float, p_comp_in: float, t_amb: float,
                       coeffs: dict) -> dict:
    """Compute compressor and intercooler sensor values.

    Args:
        maf: Mass air flow (g/s).
        p_comp_in: Compressor inlet pressure (kPa absolute).
        t_amb: Ambient temperature (K).
        coeffs: Dict with keys b0, b1, MAF_ref, eta_compressor,
                eta_intercooler, delta_P_intercooler.

    Returns:
        Dict with boost_pressure, pressure_ratio, t_boost,
        t_after_intercooler, t_intake_manifold (all in kPa / K).
    """
    maf_ratio = maf / coeffs["MAF_ref"]
    pr = 1.0 + coeffs["b0"] * np.power(max(maf_ratio, 0.01), coeffs["b1"])
    pr = max(pr, 1.01)  # PR must be > 1

    p_comp_out = p_comp_in * pr

    # Isentropic compression temperature
    t_comp_out_ideal = t_amb * np.power(pr, ISENTROPIC_EXP_AIR)
    t_comp_out = t_amb + (t_comp_out_ideal - t_amb) / coeffs["eta_compressor"]

    # After intercooler
    t_after_cac = t_amb + (t_comp_out - t_amb) * (1 - coeffs["eta_intercooler"])
    p_after_cac = p_comp_out - coeffs["delta_P_intercooler"]

    t_intake_manifold = t_after_cac + 2.0

    return {
        "boost_pressure": p_comp_out,
        "pressure_ratio": pr,
        "t_boost": t_comp_out,
        "t_after_intercooler": t_after_cac,
        "t_intake_manifold": t_intake_manifold,
    }
