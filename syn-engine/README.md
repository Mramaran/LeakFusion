# Synthetic Engine Simulator

Physics-based diesel engine sensor data generator calibrated against NavicEngine PUMA test bench data. Generates realistic sensor readings at any RPM/load with optional leak injection across 5 zones.

## Setup

```bash
cd syn-engine
pip install -r requirements.txt
```

Requires Python 3.13+ and the NavicEngine dataset at `../dataset/NavicEngine/processed_PUMA/processed_PUMA/`.

## Quick Start

```python
from src.synthetic_engine import SyntheticEngine

engine = SyntheticEngine()
engine.calibrate()

# Generate 60 seconds of healthy data at 1200 RPM, 75% load
df = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=60, seed=42)

# Generate data with a zone 3a leak (10% severity)
df_leaked = engine.run(rpm=1200, load_fraction=0.75, duration_seconds=60,
                       leak_zone="zone3a", leak_severity=0.10, seed=42)
```

## CLI Usage

```bash
# Single operating point (outputs 100 rows = 10s * 10Hz)
python -m src --rpm 1200 --load 75 --duration 10 --output output.csv

# With leak injection
python -m src --rpm 1200 --load 75 --leak zone2 --severity 5 --duration 10 --output leaked.csv

# Full training dataset (all RPMs x loads x zones x severities)
python -m src --batch --output training_data.parquet
```

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--rpm` | 1200 | Engine speed (RPM) |
| `--load` | 75 | Load percentage (0-100) |
| `--duration` | 60 | Duration in seconds |
| `--rate` | 10.0 | Sample rate in Hz |
| `--leak` | no_leak | Leak zone (no_leak, zone1, zone2, zone3a, zone3b, zone4) |
| `--severity` | 0 | Leak severity as percent (0-20) |
| `--output` | output.csv | Output file (.csv or .parquet) |
| `--batch` | false | Generate full training dataset |
| `--seed` | 42 | Random seed for noise |

## Leak Zones

| Zone | Location | Primary Affected Sensors |
|------|----------|--------------------------|
| zone1 | Between MAF sensor and compressor | Boost pressure drops, exhaust temps rise |
| zone2 | Between compressor and intake manifold | Torque drops, exhaust temps rise |
| zone3a | Exhaust manifold (before turbine) | Exhaust pressure drops, boost drops |
| zone3b | After turbine | Only backpressure drops |
| zone4 | Test cell ducting at compressor inlet | Compressor inlet pressure drops |

## Running Tests

```bash
cd syn-engine
python -m pytest tests/ -v
```

43 tests across 5 test files covering data loading, subsystems, calibration, leak injection, and end-to-end orchestration.

## Architecture

```
src/
  constants.py            Physical constants, paths, column mappings
  data_loader.py          Load NavicEngine PUMA xlsx, convert units to SI
  calibration.py          Fit 28 coefficients via scipy.optimize against PUMA data
  leak_injection.py       Physics-based sensor perturbations per leak zone
  synthetic_engine.py     Orchestrator: chains subsystems, adds noise, generates DataFrames
  __main__.py             CLI entry point
  subsystems/
    air_intake.py          Conservation of mass -> MAF
    compressor.py          Isentropic compression -> boost pressure, temps
    combustion.py          Energy balance -> fuel flow, torque
    exhaust.py             Mass + energy conservation -> exhaust temps, pressures
    backpressure.py        Pipe flow resistance -> backpressure, auxiliaries
```

## Generating Training Data

```python
engine = SyntheticEngine()
engine.calibrate()

X, y_zone, y_severity, metadata = engine.generate_training_set(
    rpms=[800, 1000, 1200, 1400, 1600, 1800, 2000, 2400],
    loads=[0.25, 0.50, 0.75, 1.00],
    leak_zones=["no_leak", "zone1", "zone2", "zone3a", "zone3b", "zone4"],
    severities=[0.01, 0.02, 0.05, 0.10, 0.15],
    samples_per_point=100,
    seed=42,
)
```

This produces ~83,200 samples (8 RPMs x 4 loads x (1 healthy + 5 zones x 5 severities) x 100 samples).
