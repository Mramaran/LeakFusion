# LeakFusion — Dataset Build Runbook

End-to-end commands to produce the two Phase 1 parquet artifacts from scratch.

**Working directory:** `D:/Hackathons/Caterpillar/leakfusion/` (all commands below assume this CWD — run everything from inside the `leakfusion/` package).

## Outputs

| File | Source | Purpose |
|------|--------|---------|
| `leakfusion/data/healthy_baseline.parquet` | **Hybrid**: NavicEngine NOMINAL xlsx + syn-engine baseline | Steady-state "no leak" reference with full (RPM, load) envelope coverage; `source` column tags each row `navic_real` or `syn_baseline` |
| `leakfusion/data/leak_labeled.parquet` | syn-engine batch simulator | Labeled leak training data (6 zones × 5 severities × grid) |

---

## 1. Prerequisites

- Python 3.13
- NavicEngine xlsx files present at the path resolved by `syn-engine/src/constants.py::PUMA_DIR` (default: `dataset/PUMA/`)
- `syn-engine/` sibling package (used for the physics simulator + xlsx loader)

Install dependencies once:

```bash
pip install -r requirements.txt
```

---

## 2. Build healthy baseline (hybrid real + syn_baseline)

Pipeline:
1. **Real path:** `load_puma_nominal` → steady-state filter → load_fraction → syn-engine fill-in (turbo_speed, t_aftertreatment_inlet) → derived columns → tag `source="navic_real"`.
2. **Augmentation path:** `build_syn_baseline_rows()` runs syn-engine in `no_leak` mode over the (rpm × load) grid that matches leaky → tag `source="syn_baseline"`.
3. Concatenate → write parquet.

Default (full hybrid, matches leaky's 8 RPMs × 4 loads grid — produces the "proper" dataset):

```bash
python -m scripts.build_healthy --out data/healthy_baseline.parquet
```

Real-only (skip augmentation — smaller, high-load-only envelope):

```bash
python -m scripts.build_healthy --out data/healthy_baseline.parquet --no-aug
```

Subset for fast iteration (single real speed, small aug grid):

```bash
python -m scripts.build_healthy --out data/healthy_baseline.parquet \
  --speeds 1200 --aug-rpms 1000 2000 --aug-loads 0.25 0.75 --aug-samples 20
```

First run is slow (~1–2 min) — syn-engine calibrates once, subsequent op-point lookups are cached.

Expected (default hybrid): **~15,800 rows = 12,600 navic_real + 3,200 syn_baseline**, 19 columns (REQUIRED_COLUMNS + `load_fraction` + `source` + optional `timestamp`).

---

## 3. Build leak-labeled dataset (syn-engine batch)

Pipeline: `SyntheticEngine.run` over (rpm × load × zone × severity) grid → derived columns → parquet.

Full grid (8 rpms × 4 loads × (1 no_leak + 5 zones × 5 severities) × 100 samples ≈ 83,200 rows):

```bash
python -m scripts.build_leaks --out data/leak_labeled.parquet
```

Half-size grid (faster, 50 samples/point ≈ 41,600 rows):

```bash
python -m scripts.build_leaks --out data/leak_labeled.parquet --samples 50
```

---

## 4. Verify

Run the full test suite:

```bash
pytest tests/ -v
```

Expected: ~30 green (6 files × ~5 tests each). The schema-consistency smoke test (`test_schema_consistency.py`) auto-runs once both parquets exist.

Quick artifact sanity-check:

```bash
python -c "
import pandas as pd
h = pd.read_parquet('data/healthy_baseline.parquet')
l = pd.read_parquet('data/leak_labeled.parquet')
print(f'healthy: {len(h):,} rows, {len(h.columns)} cols')
print(f'  sources: {h[\"source\"].value_counts().to_dict()}')
print(f'leaks  : {len(l):,} rows, {len(l.columns)} cols')
print('zone counts:'); print(l['leak_zone'].value_counts())
"
```

---

## Schema

Both parquets conform to `leakfusion/src/schema.py::REQUIRED_COLUMNS` (17 SI columns):

- **Operating point:** `engine_rpm` (RPM), `torque` (Nm)
- **Intake:** `maf` (g/s), `boost_pressure`, `intake_manifold_pressure` (kPa abs), `turbo_speed` (RPM — synthetic)
- **Exhaust:** `exhaust_manifold_pressure`, `exhaust_backpressure` (kPa abs), `fuel_flow` (g/s), `lambda_sensor` (ratio)
- **Temperatures:** `t_intake`, `t_boost`, `t_exhaust_manifold`, `t_turbine_outlet`, `t_aftertreatment_inlet` (K — synthetic)
- **Reference:** `ambient_pressure` (kPa abs), `ambient_temperature` (K)

Leak parquet additionally carries `leak_zone`, `leak_severity`, `load_fraction`.

Healthy parquet additionally carries `load_fraction` and `source` (`navic_real` | `syn_baseline`). Optional `timestamp` is present on real rows.

---

## Implementation status

| Task | Module | Status |
|------|--------|--------|
| 1 | Scaffolding | done |
| 2 | `leakfusion/src/schema.py` | done |
| 3 | `leakfusion/src/steady_state.py` | done |
| 4 | `leakfusion/src/load_estimator.py` | done |
| 5 | `leakfusion/src/syn_fill.py` | done |
| 6 | `leakfusion/scripts/build_healthy.py` | done |
| 7 | `leakfusion/scripts/build_leaks.py` | done |
| 8 | `leakfusion/tests/test_schema_consistency.py` | done |

All sections functional. `pytest leakfusion/tests/ -v` → 38 passed. See [docs/plans/2026-04-16-leakfusion-dataset-phase1-plan.md](../docs/plans/2026-04-16-leakfusion-dataset-phase1-plan.md) for the full task list.
