"""Subsystem 4: Exhaust Path (Mass + Energy Conservation).

Physics: exhaust_flow = MAF + fuel_flow (mass conservation)
         T_exhaust from energy balance: Q_fuel - Q_brake - Q_coolant - Q_rad
"""
import numpy as np
from src.constants import CP_EXHAUST, RADIATION_LOSS_FRACTION, ISENTROPIC_EXP_EXHAUST


def compute_exhaust(maf: float, fuel_flow: float, torque: float, rpm: float,
                    fuel_power: float, p_amb: float, p_backpressure: float,
                    coeffs: dict) -> dict:
    """Compute exhaust path sensor values.

    Args:
        maf: Mass air flow (g/s).
        fuel_flow: Fuel flow rate (g/s).
        torque: Brake torque (Nm).
        rpm: Engine speed (RPM).
        fuel_power: Fuel thermal power (W).
        p_amb: Ambient pressure (kPa).
        p_backpressure: Backpressure downstream of turbine (kPa).
        coeffs: Dict with keys coolant_loss_fraction, e0, e1, eta_turbine,
                cyl_offsets (list of 6 floats).

    Returns:
        Dict with exhaust_flow, t_exhaust_manifold, t_exh_cyl_1..6,
        exhaust_manifold_pressure, t_turbine_outlet.
    """
    exhaust_flow = maf + fuel_flow  # g/s (conservation of mass)

    # Energy balance
    q_brake = torque * rpm * 2 * np.pi / 60  # W
    q_coolant = fuel_power * coeffs["coolant_loss_fraction"]
    q_radiation = fuel_power * RADIATION_LOSS_FRACTION
    q_exhaust = fuel_power - q_brake - q_coolant - q_radiation
    q_exhaust = max(q_exhaust, 100)  # minimum to avoid negative temps

    # Exhaust manifold temperature
    exhaust_flow_kgs = exhaust_flow / 1000.0  # g/s -> kg/s
    t_exh_manifold = 300.0 + q_exhaust / (exhaust_flow_kgs * CP_EXHAUST)

    # Per-cylinder temps
    cyl_temps = {}
    offsets = coeffs.get("cyl_offsets", [0, 0, 0, 0, 0, 0])
    for i in range(6):
        offset = offsets[i] if i < len(offsets) else 0
        cyl_temps[f"t_exh_cyl_{i+1}"] = t_exh_manifold + offset

    # Exhaust manifold pressure (turbulent flow: P ~ flow^2)
    p_exh_manifold = p_amb + coeffs["e0"] * exhaust_flow_kgs ** 2 + coeffs["e1"]

    # Turbine expansion
    if p_exh_manifold > p_backpressure and p_backpressure > 0:
        expansion_ratio = p_exh_manifold / p_backpressure
        t_turb_out = t_exh_manifold * (
            1 - coeffs["eta_turbine"] * (1 - (1 / expansion_ratio) ** ISENTROPIC_EXP_EXHAUST)
        )
    else:
        t_turb_out = t_exh_manifold * 0.85  # fallback

    result = {
        "exhaust_flow": exhaust_flow,
        "t_exhaust_manifold": t_exh_manifold,
        "exhaust_manifold_pressure": p_exh_manifold,
        "t_turbine_outlet": t_turb_out,
    }
    result.update(cyl_temps)
    return result
