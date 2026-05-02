"""Subsystem 5: Backpressure & Auxiliaries.

Physics: P_back = P_amb + f0 * (flow/1000)^2 + f1 (pipe flow resistance)
"""


def compute_backpressure(exhaust_flow: float, p_amb: float, rpm: float,
                         fuel_power: float, coeffs: dict) -> dict:
    """Compute backpressure and auxiliary sensor values.

    Args:
        exhaust_flow: Total exhaust mass flow (g/s).
        p_amb: Ambient pressure (kPa).
        rpm: Engine speed (RPM).
        fuel_power: Fuel thermal power (W).
        coeffs: Dict with keys f0, f1, h0, h1, g0.

    Returns:
        Dict with exhaust_backpressure, turbine_outlet_pressure,
        oil_pressure (kPa), coolant_temperature (K).
    """
    flow_kgs = exhaust_flow / 1000.0

    p_back = p_amb + coeffs["f0"] * flow_kgs ** 2 + coeffs["f1"]
    p_turb_out = p_back + 0.5

    p_oil = coeffs["h0"] + coeffs["h1"] * rpm
    t_coolant = 350.0 + coeffs["g0"] * (fuel_power / 1000.0)

    return {
        "exhaust_backpressure": p_back,
        "turbine_outlet_pressure": p_turb_out,
        "oil_pressure": p_oil,
        "coolant_temperature": t_coolant,
    }
