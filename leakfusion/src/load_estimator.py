"""Estimate engine load_fraction [0, 1] from (rpm, fuel_flow).

Uses syn-engine's combustion model inversion:
    fuel_flow_max(rpm) = c0 + c1 * (rpm / 1000)
    load_fraction = min(fuel_flow / fuel_flow_max, 1.0)

Coefficients c0, c1 come from syn-engine's calibration against NavicEngine.
If calibration hasn't been run in-session, we fall back to textbook defaults
that are approximately correct for a 7.6L inline-6 diesel.
"""
from typing import Optional
import pandas as pd

# Defaults approximating syn-engine's calibrated combustion for Navistar DT 7.6L.
# Recalibrated values from syn-engine can override via set_calibration().
_FUEL_FLOW_MAX_COEFFS = {"c0": 0.0, "c1": 2.5}  # g/s = c0 + c1 * (rpm/1000)


def set_calibration(c0: float, c1: float) -> None:
    """Override the combustion fuel_flow_max(rpm) coefficients."""
    _FUEL_FLOW_MAX_COEFFS["c0"] = c0
    _FUEL_FLOW_MAX_COEFFS["c1"] = c1


def estimate_load_fraction(rpm: float, fuel_flow: float) -> float:
    """Return load_fraction in [0, 1] for a single (rpm, fuel_flow) sample.

    Args:
        rpm: Engine speed (RPM).
        fuel_flow: Fuel consumption (g/s).

    Returns:
        Load fraction clipped to [0, 1].
    """
    if fuel_flow <= 0.0:
        return 0.0
    rpm_k = rpm / 1000.0
    ff_max = _FUEL_FLOW_MAX_COEFFS["c0"] + _FUEL_FLOW_MAX_COEFFS["c1"] * rpm_k
    if ff_max <= 0:
        return 0.0
    return min(max(fuel_flow / ff_max, 0.0), 1.0)


def add_load_fraction_column(df: pd.DataFrame,
                             rpm_col: str = "engine_rpm",
                             fuel_flow_col: str = "fuel_flow") -> pd.DataFrame:
    """Return a copy of df with a new 'load_fraction' column."""
    out = df.copy()
    out["load_fraction"] = [
        estimate_load_fraction(r, f)
        for r, f in zip(out[rpm_col], out[fuel_flow_col])
    ]
    return out
