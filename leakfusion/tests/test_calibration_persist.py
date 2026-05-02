"""JSON save/load roundtrip with schema version checks."""
import json
import tempfile
from pathlib import Path

import pytest

from leakfusion.src.calibration.calibration_set import CalibrationSet, CellCalibration, ResidualStats
from leakfusion.src.calibration.persist import (
    save_calibration, load_calibration, CalibrationVersionError, CURRENT_SCHEMA_VERSION,
)


def _sample_set():
    cell = CellCalibration(
        rpm_bin=1400, load_bin=0.75, sample_count=100,
        coeffs={"a0": 0.85, "eta_c": 0.75, "e0": 0.001, "e1": 0.5,
                "k_ats": 8.0, "phi_coolant": 0.25, "lambda_baseline_mean": 1.8},
        residual_stats={f"R{i}": ResidualStats(mu=0.0, sigma=1.0) for i in range(1, 7)},
    )
    return CalibrationSet(schema_version=CURRENT_SCHEMA_VERSION, cells=[cell])


def test_save_creates_json():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "calib.json"
        save_calibration(_sample_set(), path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["schema_version"] == CURRENT_SCHEMA_VERSION
        assert len(data["cells"]) == 1


def test_roundtrip_preserves_coeffs():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "calib.json"
        original = _sample_set()
        save_calibration(original, path)
        loaded = load_calibration(path)
        assert loaded.cells[0].coeffs["eta_c"] == 0.75
        assert loaded.cells[0].residual_stats["R1"].sigma == 1.0


def test_load_rejects_old_schema():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "old.json"
        path.write_text(json.dumps({"schema_version": 0, "cells": []}))
        with pytest.raises(CalibrationVersionError):
            load_calibration(path)
