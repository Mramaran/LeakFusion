"""SyntheticEngine: Virtual diesel engine test cell.

Orchestrates 5 physics subsystems to generate realistic sensor data
at any RPM/load, calibrated against NavicEngine test bench data.
"""
import numpy as np
import pandas as pd
from src.constants import (
    DISPLACEMENT_M3, P_AMB_STD, T_AMB_STD, LEAK_ZONES,
)
from src.subsystems.air_intake import compute_air_intake
from src.subsystems.compressor import compute_compressor
from src.subsystems.combustion import compute_combustion
from src.subsystems.exhaust import compute_exhaust
from src.subsystems.backpressure import compute_backpressure
from src.calibration import calibrate_from_navicengine
from src.leak_injection import inject_leak


class SyntheticEngine:
    """Virtual diesel engine test cell simulator.

    Usage:
        engine = SyntheticEngine(displacement_liters=7.6, num_cylinders=6)
        engine.calibrate()
        data = engine.run(rpm=1800, load_fraction=0.75, duration_seconds=300)
    """

    def __init__(self, displacement_liters: float = 7.6, num_cylinders: int = 6,
                 turbo_stages: int = 2):
        self.displacement_m3 = displacement_liters / 1000.0
        self.num_cylinders = num_cylinders
        self.turbo_stages = turbo_stages
        self.is_calibrated = False
        self._coefficients = {}
        self._noise_stats = {}
        self._correction_polys = {}

    def calibrate(self, data_path: str | None = None) -> "SyntheticEngine":
        """Calibrate coefficients from NavicEngine data.

        Args:
            data_path: Path to NavicEngine dataset (default: use constants.DATA_DIR).
        """
        result = calibrate_from_navicengine()
        self._coefficients = result["coefficients"]
        self._noise_stats = result["noise_stats"]
        self._correction_polys = result["correction_polys"]
        self.is_calibrated = True
        return self

    def run(self, rpm: float, load_fraction: float, duration_seconds: float,
            sample_rate_hz: float = 10.0, leak_zone: str = "no_leak",
            leak_severity: float = 0.0, p_amb: float = P_AMB_STD,
            t_amb: float = T_AMB_STD, seed: int | None = None) -> pd.DataFrame:
        """Generate synthetic sensor data at a given operating point.

        Args:
            rpm: Engine speed (RPM).
            load_fraction: Load as fraction (0.0 to 1.0).
            duration_seconds: How long to simulate.
            sample_rate_hz: Output sample rate (default 10 Hz).
            leak_zone: Leak zone ('no_leak', 'zone1', etc.).
            leak_severity: Leak fraction (0.0 to 0.20).
            p_amb: Ambient pressure (kPa, default 101.325).
            t_amb: Ambient temperature (K, default 298.15).
            seed: Random seed for noise (None = no noise).

        Returns:
            DataFrame with all sensor columns.
        """
        if not self.is_calibrated:
            raise RuntimeError("Must call calibrate() before run()")

        # Compute steady-state sensor values from physics
        sensors = self._compute_steady_state(rpm, load_fraction, p_amb, t_amb)

        # Apply leak perturbation
        if leak_zone != "no_leak" and leak_severity > 0:
            sensors = inject_leak(sensors, leak_zone, leak_severity)

        # Generate time series with noise
        n_samples = int(duration_seconds * sample_rate_hz)
        rng = np.random.default_rng(seed)

        rows = []
        for i in range(n_samples):
            row = {"timestamp": i / sample_rate_hz}
            for key, value in sensors.items():
                noise = 0.0
                if seed is not None and key in self._noise_stats:
                    noise = rng.normal(0, self._noise_stats[key])
                row[key] = value + noise
            row["engine_rpm"] = rpm + (rng.normal(0, 2) if seed is not None else 0)
            row["ambient_pressure"] = p_amb
            row["ambient_temperature"] = t_amb
            row["t_intake"] = t_amb
            rows.append(row)

        return pd.DataFrame(rows)

    def _compute_steady_state(self, rpm, load_fraction, p_amb, t_amb):
        """Run all 5 subsystems in sequence to get steady-state sensor values."""
        coeffs = self._coefficients

        # Subsystem 5 first (need backpressure for exhaust)
        # Use initial estimate, then iterate
        exhaust_flow_est = 30.0  # initial guess g/s
        fuel_power_est = 100000.0
        back = compute_backpressure(exhaust_flow_est, p_amb, rpm, fuel_power_est,
                                    coeffs["backpressure"])

        # Subsystem 2: Compressor (need MAF estimate)
        maf_est = 25.0  # initial guess
        comp = compute_compressor(maf_est, p_amb, t_amb, coeffs["compressor"])

        # Subsystem 1: Air Intake
        intake = compute_air_intake(rpm, comp["boost_pressure"],
                                    comp["t_after_intercooler"], p_amb,
                                    coeffs["intake"])

        # Now iterate with better MAF estimate
        for _ in range(3):
            comp = compute_compressor(intake["maf"], intake["compressor_inlet_pressure"],
                                      t_amb, coeffs["compressor"])
            intake = compute_air_intake(rpm, comp["boost_pressure"],
                                        comp["t_after_intercooler"], p_amb,
                                        coeffs["intake"])

        # Subsystem 3: Combustion
        comb = compute_combustion(intake["maf"], rpm, load_fraction,
                                  coeffs["combustion"])

        # Subsystem 5: Backpressure (with real exhaust flow)
        exhaust_flow = intake["maf"] + comb["fuel_flow"]
        back = compute_backpressure(exhaust_flow, p_amb, rpm, comb["fuel_power"],
                                    coeffs["backpressure"])

        # Subsystem 4: Exhaust
        exh = compute_exhaust(intake["maf"], comb["fuel_flow"], comb["torque"],
                              rpm, comb["fuel_power"], p_amb,
                              back["exhaust_backpressure"], coeffs["exhaust"])

        # Assemble sensor dict
        sensors = {}
        sensors.update(intake)
        sensors.update(comp)
        sensors.update(comb)
        sensors.update(exh)
        sensors.update(back)

        return sensors

    def generate_training_set(
        self,
        rpms: list[int] | None = None,
        loads: list[float] | None = None,
        leak_zones: list[str] | None = None,
        severities: list[float] | None = None,
        samples_per_point: int = 100,
        seed: int = 42,
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.DataFrame]:
        """Generate a full training dataset.

        Returns:
            (X_sensors, y_zone, y_severity, metadata)
        """
        rpms = rpms or [800, 1000, 1200, 1400, 1600, 1800, 2000, 2400]
        loads = loads or [0.25, 0.50, 0.75, 1.00]
        leak_zones = leak_zones or LEAK_ZONES
        severities = severities or [0.01, 0.02, 0.05, 0.10, 0.15]

        all_frames = []
        all_zones = []
        all_sevs = []
        all_meta = []

        for rpm in rpms:
            for load in loads:
                for zone in leak_zones:
                    sevs = [0.0] if zone == "no_leak" else severities
                    for sev in sevs:
                        df = self.run(
                            rpm=rpm, load_fraction=load,
                            duration_seconds=samples_per_point,
                            sample_rate_hz=1.0,
                            leak_zone=zone, leak_severity=sev,
                            seed=seed,
                        )
                        all_frames.append(df)
                        all_zones.extend([zone] * len(df))
                        all_sevs.extend([sev] * len(df))
                        all_meta.extend([{
                            "rpm": rpm, "load": load,
                            "source": "synthetic",
                        }] * len(df))

        X = pd.concat(all_frames, ignore_index=True)
        y_zone = pd.Series(all_zones, name="zone")
        y_severity = pd.Series(all_sevs, name="severity")
        metadata = pd.DataFrame(all_meta)

        return X, y_zone, y_severity, metadata
