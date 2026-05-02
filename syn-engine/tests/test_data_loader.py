"""Tests for NavicEngine PUMA data loader."""
import pytest
import pandas as pd
from src.data_loader import load_puma_nominal, extract_operating_points


class TestLoadPumaNominal:
    def test_returns_dataframe(self):
        df = load_puma_nominal(1000)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 100

    def test_has_standard_columns(self):
        df = load_puma_nominal(1000)
        required = ["engine_rpm", "torque", "maf", "fuel_flow",
                     "boost_pressure", "compressor_inlet_pressure",
                     "exhaust_manifold_pressure", "exhaust_backpressure",
                     "t_intake", "t_boost", "t_exhaust_manifold",
                     "t_turbine_outlet", "ambient_pressure"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_units_are_si(self):
        """MAF in g/s, pressures in kPa absolute, temps in K."""
        df = load_puma_nominal(1000)
        # MAF: ~86 kg/h = ~23.9 g/s
        assert 10 < df["maf"].median() < 50, f"MAF={df['maf'].median()} not in g/s range"
        # Boost: ~122 kPa absolute at 1000 RPM
        assert 100 < df["boost_pressure"].median() < 200, \
            f"Boost={df['boost_pressure'].median()} not in kPa absolute range"
        # Temps in K (ambient ~298K)
        assert 270 < df["t_intake"].median() < 330, \
            f"T_intake={df['t_intake'].median()} not in Kelvin range"

    def test_invalid_speed_raises(self):
        with pytest.raises(FileNotFoundError):
            load_puma_nominal(9999)


class TestExtractOperatingPoints:
    def test_returns_4_rows(self):
        ops = extract_operating_points()
        assert len(ops) == 4

    def test_has_all_speeds(self):
        ops = extract_operating_points()
        assert list(ops["speed_setpoint"]) == [1000, 1200, 1400, 1600]

    def test_values_are_medians(self):
        ops = extract_operating_points()
        row_1000 = ops[ops["speed_setpoint"] == 1000].iloc[0]
        # Torque at 1000 RPM should be ~222 Nm
        assert 200 < row_1000["torque"] < 250
