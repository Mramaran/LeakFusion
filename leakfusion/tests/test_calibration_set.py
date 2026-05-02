"""CalibrationSet: in-memory representation of fitted per-cell coefficients."""
import pytest
from leakfusion.src.calibration.calibration_set import (
    CalibrationSet, CellCalibration, ResidualStats, CellNotFoundError,
)


def _sample_cell(rpm_bin=1400, load_bin=0.75):
    return CellCalibration(
        rpm_bin=rpm_bin, load_bin=load_bin, sample_count=100,
        coeffs={"a0": 0.85, "a1": 0.0, "a2": 0.0, "eta_c": 0.75,
                "e0": 0.001, "e1": 0.5, "k_ats": 8.0, "phi_coolant": 0.25,
                "lambda_baseline_mean": 1.8},
        residual_stats={f"R{i}": ResidualStats(mu=0.0, sigma=1.0) for i in range(1, 7)},
    )


def test_get_cell_exact_match():
    cs = CalibrationSet(schema_version=1, cells=[_sample_cell()])
    cell = cs.get_cell(1400, 0.75)
    assert cell.coeffs["eta_c"] == 0.75


def test_get_cell_missing_raises():
    cs = CalibrationSet(schema_version=1, cells=[_sample_cell()])
    with pytest.raises(CellNotFoundError):
        cs.get_cell(9999, 0.5)


def test_nearest_cell_falls_back():
    cs = CalibrationSet(schema_version=1, cells=[_sample_cell(1400, 0.75)])
    cell, extrapolated = cs.get_nearest_cell(1450, 0.80)
    assert cell.rpm_bin == 1400
    assert cell.load_bin == 0.75
    assert extrapolated is True


def test_nearest_cell_exact_match_not_extrapolated():
    cs = CalibrationSet(schema_version=1, cells=[_sample_cell(1400, 0.75)])
    cell, extrapolated = cs.get_nearest_cell(1400, 0.75)
    assert extrapolated is False


def test_residual_stats_has_mu_and_sigma():
    rs = ResidualStats(mu=0.1, sigma=0.5)
    assert rs.mu == 0.1
    assert rs.sigma == 0.5
