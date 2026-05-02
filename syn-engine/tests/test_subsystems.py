"""Tests for individual physics subsystems."""
import pytest
import numpy as np
from src.subsystems.air_intake import compute_air_intake
from src.subsystems.compressor import compute_compressor
from src.subsystems.combustion import compute_combustion
from src.subsystems.exhaust import compute_exhaust
from src.subsystems.backpressure import compute_backpressure


# Default coefficients (reasonable starting points)
DEFAULT_INTAKE_COEFFS = {"a0": 0.85, "a1": 0.02, "a2": -0.01, "delta_P_filter": 0.3}
DEFAULT_COMP_COEFFS = {"b0": 1.5, "b1": 1.0, "MAF_ref": 30.0,
                       "eta_compressor": 0.75, "eta_intercooler": 0.85,
                       "delta_P_intercooler": 3.0}
DEFAULT_COMB_COEFFS = {"c0": 0.5, "c1": 1.4, "eta_thermal": 0.40}
DEFAULT_EXHAUST_COEFFS = {"coolant_loss_fraction": 0.30, "e0": 150.0, "e1": 1.0,
                          "eta_turbine": 0.72,
                          "cyl_offsets": [-8, -3, 2, 5, -1, 6]}
DEFAULT_BACK_COEFFS = {"f0": 50.0, "f1": 0.5, "h0": 150.0, "h1": 0.1, "g0": 0.3}


class TestAirIntake:
    def test_maf_positive(self):
        result = compute_air_intake(rpm=1200, p_boost=130.0, t_after_cac=310.0,
                                    p_amb=101.3, coeffs=DEFAULT_INTAKE_COEFFS)
        assert result["maf"] > 0

    def test_maf_increases_with_rpm(self):
        r1 = compute_air_intake(rpm=1000, p_boost=120.0, t_after_cac=310.0,
                                p_amb=101.3, coeffs=DEFAULT_INTAKE_COEFFS)
        r2 = compute_air_intake(rpm=1600, p_boost=160.0, t_after_cac=310.0,
                                p_amb=101.3, coeffs=DEFAULT_INTAKE_COEFFS)
        assert r2["maf"] > r1["maf"]

    def test_comp_inlet_below_ambient(self):
        result = compute_air_intake(rpm=1200, p_boost=130.0, t_after_cac=310.0,
                                    p_amb=101.3, coeffs=DEFAULT_INTAKE_COEFFS)
        assert result["compressor_inlet_pressure"] < 101.3


class TestCompressor:
    def test_boost_above_ambient(self):
        result = compute_compressor(maf=25.0, p_comp_in=101.0, t_amb=298.0,
                                    coeffs=DEFAULT_COMP_COEFFS)
        assert result["boost_pressure"] > 101.0

    def test_pr_above_one(self):
        result = compute_compressor(maf=25.0, p_comp_in=101.0, t_amb=298.0,
                                    coeffs=DEFAULT_COMP_COEFFS)
        assert result["pressure_ratio"] > 1.0

    def test_t_comp_out_above_ambient(self):
        """Compression always heats air."""
        result = compute_compressor(maf=25.0, p_comp_in=101.0, t_amb=298.0,
                                    coeffs=DEFAULT_COMP_COEFFS)
        assert result["t_boost"] > 298.0

    def test_t_after_cac_below_t_comp_out(self):
        """Intercooler always cools."""
        result = compute_compressor(maf=25.0, p_comp_in=101.0, t_amb=298.0,
                                    coeffs=DEFAULT_COMP_COEFFS)
        assert result["t_after_intercooler"] < result["t_boost"]


class TestCombustion:
    def test_torque_positive(self):
        result = compute_combustion(maf=25.0, rpm=1200, load_fraction=0.75,
                                    coeffs=DEFAULT_COMB_COEFFS)
        assert result["torque"] > 0

    def test_lambda_above_one(self):
        """Diesel always runs lean."""
        result = compute_combustion(maf=25.0, rpm=1200, load_fraction=0.75,
                                    coeffs=DEFAULT_COMB_COEFFS)
        assert result["lambda_calculated"] > 1.0

    def test_torque_increases_with_load(self):
        r1 = compute_combustion(maf=25.0, rpm=1200, load_fraction=0.25,
                                coeffs=DEFAULT_COMB_COEFFS)
        r2 = compute_combustion(maf=25.0, rpm=1200, load_fraction=1.0,
                                coeffs=DEFAULT_COMB_COEFFS)
        assert r2["torque"] > r1["torque"]


class TestExhaust:
    def test_exhaust_temp_above_ambient(self):
        result = compute_exhaust(maf=25.0, fuel_flow=3.0, torque=250.0, rpm=1200,
                                 fuel_power=25.0 * 42700, p_amb=101.3,
                                 p_backpressure=102.0, coeffs=DEFAULT_EXHAUST_COEFFS)
        assert result["t_exhaust_manifold"] > 300

    def test_exhaust_pressure_above_ambient(self):
        result = compute_exhaust(maf=25.0, fuel_flow=3.0, torque=250.0, rpm=1200,
                                 fuel_power=3.0 * 42700, p_amb=101.3,
                                 p_backpressure=102.0, coeffs=DEFAULT_EXHAUST_COEFFS)
        assert result["exhaust_manifold_pressure"] > 101.3

    def test_six_cylinder_temps(self):
        result = compute_exhaust(maf=25.0, fuel_flow=3.0, torque=250.0, rpm=1200,
                                 fuel_power=3.0 * 42700, p_amb=101.3,
                                 p_backpressure=102.0, coeffs=DEFAULT_EXHAUST_COEFFS)
        for i in range(1, 7):
            assert f"t_exh_cyl_{i}" in result
            assert result[f"t_exh_cyl_{i}"] > 300


class TestBackpressure:
    def test_backpressure_above_ambient(self):
        result = compute_backpressure(exhaust_flow=28.0, p_amb=101.3, rpm=1200,
                                      fuel_power=3.0 * 42700, coeffs=DEFAULT_BACK_COEFFS)
        assert result["exhaust_backpressure"] > 101.3

    def test_oil_pressure_positive(self):
        result = compute_backpressure(exhaust_flow=28.0, p_amb=101.3, rpm=1200,
                                      fuel_power=3.0 * 42700, coeffs=DEFAULT_BACK_COEFFS)
        assert result["oil_pressure"] > 0
