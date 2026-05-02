"""Synthetic leak injection into sensor data.

Each zone applies physics-based perturbations to sensors downstream of the leak point.
See docs/plans/2026-04-14-synthetic-engine-design.md Section 6 for derivations.
"""
import numpy as np
from src.constants import GAMMA_AIR


def inject_leak(sensors: dict, zone: str, severity: float) -> dict:
    """Apply leak perturbation to a sensor value dict.

    Args:
        sensors: Dict of sensor_name -> value (modified in-place).
        zone: One of 'no_leak', 'zone1', 'zone2', 'zone3a', 'zone3b', 'zone4'.
        severity: Leak fraction (0.0 = no leak, 0.15 = 15%).

    Returns:
        Modified sensors dict.
    """
    if zone == "no_leak" or severity <= 0:
        return sensors

    s = severity

    if zone == "zone1":
        _inject_zone1(sensors, s)
    elif zone == "zone2":
        _inject_zone2(sensors, s)
    elif zone == "zone3a":
        _inject_zone3a(sensors, s)
    elif zone == "zone3b":
        _inject_zone3b(sensors, s)
    elif zone == "zone4":
        _inject_zone4(sensors, s)

    # Recompute pressure ratio if both pressures exist
    if "boost_pressure" in sensors and "compressor_inlet_pressure" in sensors:
        p_in = sensors["compressor_inlet_pressure"]
        if p_in > 0:
            sensors["pressure_ratio"] = sensors["boost_pressure"] / p_in

    return sensors


def _inject_zone1(sensors, s):
    """Zone 1: Air escapes between MAF sensor and compressor."""
    p_in = sensors.get("compressor_inlet_pressure", 101.0)
    p_boost_orig = sensors.get("boost_pressure", 130.0)
    delta = p_boost_orig - p_in
    sensors["boost_pressure"] = p_in + delta * (1 - s) ** GAMMA_AIR

    _scale_exhaust_temps(sensors, 1 + 0.3 * s)


def _inject_zone2(sensors, s):
    """Zone 2: Compressed air escapes between compressor and intake manifold."""
    if "t_intake_manifold" in sensors:
        sensors["t_intake_manifold"] -= s * 10
    if "torque" in sensors:
        sensors["torque"] *= (1 - 0.3 * s)

    _scale_exhaust_temps(sensors, 1 + 0.5 * s)


def _inject_zone3a(sensors, s):
    """Zone 3a: Exhaust escapes before turbine."""
    if "exhaust_manifold_pressure" in sensors:
        sensors["exhaust_manifold_pressure"] *= (1 - s) ** 2
    if "exhaust_backpressure" in sensors:
        sensors["exhaust_backpressure"] *= (1 - s) ** 2
    if "boost_pressure" in sensors:
        sensors["boost_pressure"] *= (1 - 0.7 * s)
    if "t_turbine_outlet" in sensors:
        sensors["t_turbine_outlet"] *= (1 - 0.2 * s)


def _inject_zone3b(sensors, s):
    """Zone 3b: Exhaust escapes after turbine. Only backpressure affected."""
    if "exhaust_backpressure" in sensors:
        sensors["exhaust_backpressure"] *= (1 - s) ** 2


def _inject_zone4(sensors, s):
    """Zone 4: Test cell ducting leak at compressor inlet."""
    p_in_orig = sensors.get("compressor_inlet_pressure", 101.0)
    boost_orig = sensors.get("boost_pressure", 130.0)
    delta_orig = boost_orig - p_in_orig

    sensors["compressor_inlet_pressure"] = p_in_orig * (1 - 0.5 * s)
    sensors["boost_pressure"] = sensors["compressor_inlet_pressure"] + delta_orig * (1 - 0.3 * s)


def _scale_exhaust_temps(sensors, factor):
    """Scale exhaust manifold and per-cylinder temps by factor."""
    if "t_exhaust_manifold" in sensors:
        sensors["t_exhaust_manifold"] *= factor
    for i in range(1, 7):
        key = f"t_exh_cyl_{i}"
        if key in sensors:
            sensors[key] *= factor
