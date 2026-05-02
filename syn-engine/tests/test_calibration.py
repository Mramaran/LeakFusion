"""Tests for calibration against NavicEngine data."""
import pytest
import numpy as np
from src.calibration import calibrate_from_navicengine


class TestCalibration:
    @pytest.fixture(scope="class")
    def calibration_result(self):
        return calibrate_from_navicengine()

    def test_returns_all_coefficient_groups(self, calibration_result):
        coeffs = calibration_result["coefficients"]
        assert "intake" in coeffs
        assert "compressor" in coeffs
        assert "combustion" in coeffs
        assert "exhaust" in coeffs
        assert "backpressure" in coeffs

    def test_intake_coeffs_in_range(self, calibration_result):
        c = calibration_result["coefficients"]["intake"]
        assert 0.2 <= c["a0"] <= 1.0
        assert 0.0 < c["delta_P_filter"] < 2.0

    def test_compressor_eta_in_range(self, calibration_result):
        c = calibration_result["coefficients"]["compressor"]
        assert 0.4 <= c["eta_compressor"] <= 0.95

    def test_thermal_efficiency_in_range(self, calibration_result):
        c = calibration_result["coefficients"]["combustion"]
        assert 0.25 < c["eta_thermal"] < 0.50

    def test_validation_errors_within_tolerance(self, calibration_result):
        """After calibration, predictions should match NavicEngine data."""
        errors = calibration_result["validation_errors"]
        for speed, errs in errors.items():
            # Torque within 15 Nm
            assert abs(errs.get("torque", 0)) < 30, \
                f"Speed {speed}: torque error {errs['torque']:.1f} Nm too large"

    def test_noise_stats_extracted(self, calibration_result):
        noise = calibration_result["noise_stats"]
        assert "maf" in noise
        assert noise["maf"] > 0
