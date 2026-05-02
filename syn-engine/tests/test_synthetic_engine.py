"""Tests for the SyntheticEngine orchestrator class."""
import pytest
import pandas as pd
import numpy as np
from src.synthetic_engine import SyntheticEngine


@pytest.fixture(scope="module")
def engine():
    """Create and calibrate engine once for all tests."""
    eng = SyntheticEngine(displacement_liters=7.6, num_cylinders=6)
    eng.calibrate()
    return eng


class TestSyntheticEngine:
    def test_calibrate_sets_is_calibrated(self, engine):
        assert engine.is_calibrated

    def test_run_returns_dataframe(self, engine):
        df = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=10, sample_rate_hz=1)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10

    def test_output_has_all_columns(self, engine):
        df = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=5, sample_rate_hz=1)
        required = ["timestamp", "engine_rpm", "torque", "maf", "fuel_flow",
                     "boost_pressure", "compressor_inlet_pressure", "pressure_ratio",
                     "exhaust_manifold_pressure", "exhaust_backpressure",
                     "t_intake", "t_boost", "t_exhaust_manifold", "t_turbine_outlet",
                     "ambient_pressure", "ambient_temperature", "lambda_calculated"]
        for col in required:
            assert col in df.columns, f"Missing: {col}"

    def test_physics_sanity_at_1200rpm(self, engine):
        df = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=5, sample_rate_hz=1)
        row = df.iloc[0]
        assert row["maf"] > 0
        assert row["boost_pressure"] > row["ambient_pressure"]
        assert row["t_exhaust_manifold"] > row["t_intake"]
        assert row["lambda_calculated"] > 1.0
        assert row["torque"] > 0

    def test_extrapolation_at_2000rpm(self, engine):
        """Should work at RPMs outside NavicEngine range."""
        df = engine.run(rpm=2000, load_fraction=0.75, duration_seconds=5, sample_rate_hz=1)
        row = df.iloc[0]
        assert row["maf"] > 0
        assert row["boost_pressure"] > row["ambient_pressure"]

    def test_leak_injection_works(self, engine):
        healthy = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=5, sample_rate_hz=1)
        leaked = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=5, sample_rate_hz=1,
                            leak_zone="zone3b", leak_severity=0.10)
        assert leaked["exhaust_backpressure"].median() < healthy["exhaust_backpressure"].median()

    def test_noise_adds_variation(self, engine):
        df = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=30, sample_rate_hz=10)
        # With noise, values should have some spread
        assert df["maf"].std() > 0
