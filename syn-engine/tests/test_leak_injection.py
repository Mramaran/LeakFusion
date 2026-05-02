"""Tests for leak injection into synthetic sensor data."""
import pytest
from src.leak_injection import inject_leak


class TestInjectLeak:
    def setup_method(self):
        """Create a healthy sensor dict for testing."""
        self.healthy = {
            "maf": 25.0,
            "boost_pressure": 130.0,
            "compressor_inlet_pressure": 101.0,
            "pressure_ratio": 1.287,
            "exhaust_manifold_pressure": 145.0,
            "exhaust_backpressure": 102.0,
            "t_exhaust_manifold": 600.0,
            "t_turbine_outlet": 520.0,
            "t_intake_manifold": 310.0,
            "torque": 280.0,
            "t_exh_cyl_1": 595.0,
            "t_exh_cyl_2": 598.0,
            "t_exh_cyl_3": 602.0,
            "t_exh_cyl_4": 605.0,
            "t_exh_cyl_5": 599.0,
            "t_exh_cyl_6": 606.0,
        }

    def test_no_leak_unchanged(self):
        result = inject_leak(self.healthy.copy(), "no_leak", 0.0)
        assert result["boost_pressure"] == 130.0

    def test_zone1_drops_boost(self):
        result = inject_leak(self.healthy.copy(), "zone1", 0.10)
        assert result["boost_pressure"] < 130.0

    def test_zone2_keeps_boost(self):
        result = inject_leak(self.healthy.copy(), "zone2", 0.10)
        assert result["boost_pressure"] == 130.0

    def test_zone2_raises_exhaust_temp(self):
        result = inject_leak(self.healthy.copy(), "zone2", 0.10)
        assert result["t_exhaust_manifold"] > 600.0

    def test_zone3a_drops_exhaust_pressure(self):
        result = inject_leak(self.healthy.copy(), "zone3a", 0.10)
        assert result["exhaust_manifold_pressure"] < 145.0

    def test_zone3a_drops_boost(self):
        result = inject_leak(self.healthy.copy(), "zone3a", 0.10)
        assert result["boost_pressure"] < 130.0

    def test_zone3b_only_drops_backpressure(self):
        result = inject_leak(self.healthy.copy(), "zone3b", 0.10)
        assert result["exhaust_backpressure"] < 102.0
        assert result["exhaust_manifold_pressure"] == 145.0
        assert result["boost_pressure"] == 130.0

    def test_zone4_drops_comp_inlet(self):
        result = inject_leak(self.healthy.copy(), "zone4", 0.10)
        assert result["compressor_inlet_pressure"] < 101.0
