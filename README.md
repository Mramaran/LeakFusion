# LeakFusion — Engine Air-Path Leak Detection

A 3-stage pipeline that detects air-path leaks on a Navistar DT 7.6L diesel engine from raw sensor data:

1. **Stage 1 — Physics residuals.** Six closed-form residuals (R1..R6) computed against per-op-point calibration: intake mass, boost balance, exhaust mass, aftertreatment dP, lambda, thermal balance.
2. **Stage 2 — CUSUM gating.** Sequential change detection on z-scored residuals; emits `WARN` and `CRITICAL` events with a sustained-signature requirement.
3. **Stage 3 — ML zone + severity.** Random-forest zone classifier + XGBoost severity regressor augment each `CRITICAL` event with the predicted leak zone, confidence, and severity (with CI).

Single-page Streamlit dashboard renders the verdict: status banner, 6 residual bars with status badges, predicted zone + severity, recommended inspection action, and event timeline.

---

## Quick start

```bash
# 1. Install deps
pip install -r leakfusion/requirements.txt

# 2. Download pre-fit models from Google Drive (NOT in this repo)
#    Drive link: <PASTE-LINK-HERE>
#    Extract the archive directly into leakfusion/models/   (5 files)
#    Expected files after extraction:
#      leakfusion/models/calibration.json
#      leakfusion/models/cusum_config.json
#      leakfusion/models/stage3_features_schema.json
#      leakfusion/models/stage3_severity_xgb.joblib
#      leakfusion/models/stage3_zone_rf.joblib

# 3. Run the test suite (verifies pipeline + components)
python -m pytest leakfusion/tests/ -q

# 4. Launch the demo UI
python -m streamlit run leakfusion/ui/streamlit_app.py
```

> **Models are not in this repo** — they total ~78 MB and we share them via Google Drive instead (the repo is private, but joblibs are awkward to push and clone). The 5-file `leakfusion/models/` folder above is everything the dashboard needs.

The UI offers 4 pre-built sample CSVs (Healthy Run, Zone 1 Leak, Zone 3a Leak, Zone 4 Leak) and an "Advanced: upload your own CSV" expander that accepts any CSV with the 17 SI sensor columns documented in [leakfusion/src/schema.py](leakfusion/src/schema.py).

---

## Repository layout

```
.
|-- leakfusion/
|   |-- src/                   # Stage 1/2/3 implementation
|   |   |-- residuals/         # R1..R6 closed-form residuals + orchestrator
|   |   |-- detection/         # Stage 2 CUSUM + AlertEvent emission
|   |   |-- ml/                # Stage 3 zone classifier + severity regressor + features
|   |   |-- calibration/       # Per-op-point calibration fit + persistence
|   |   |-- demo/              # CSV upload pipeline + UI helpers (NEW for round-2 demo)
|   |   |-- schema.py          # Required SI column schema
|   |   |-- syn_fill.py        # Synthetic fill for sensors NavicEngine doesn't expose
|   |   |-- steady_state.py    # Steady-state classifier
|   |   `-- load_estimator.py  # Engine-load estimator
|   |-- scripts/               # build_healthy, build_leaks, fit_calibration, run_stage2,
|   |                          # train_stage3, evaluate_stage3, build_demo_samples, ...
|   |-- tests/                 # 237 pytest tests covering every stage
|   |   `-- demo/              # 51 tests for the round-2 demo pipeline + UI components
|   |-- ui/
|   |   |-- streamlit_app.py         # Single-page verdict dashboard
|   |   `-- dashboard_components.py  # Render components + pure payload builders
|   |-- models/                # Pre-fit calibration + Stage 3 models — NOT in repo, see Quick start
|   |-- data/
|   |   |-- leak_labeled.parquet     # Labeled training/eval data (12 MB)
|   |   `-- demo_samples/            # 4 pre-built demo CSVs for the UI
|   |-- requirements.txt
|   |-- conftest.py            # Adds repo root + ../syn-engine to sys.path
|   |-- pytest.ini
|   `-- RUN.md                 # Phase 1 dataset build runbook
|-- syn-engine/                # Sibling dependency: synthetic engine model
|   `-- ...                    # leakfusion's conftest.py adds this to sys.path
|-- README.md                  # this file
`-- .gitignore
```

`syn-engine/` is required: `leakfusion/conftest.py` puts it on `sys.path` so a few residual constants and the synthetic-fill helpers can import from it.

---

## Demo predictions

End-to-end on the 4 pre-built demo CSVs (test results from the implementation plan's Task 21):

| Sample CSV                  | Predicted Zone | True Zone | Severity (predicted / true) |
|-----------------------------|----------------|-----------|-----------------------------|
| `healthy_run.csv`           | (no CRITICAL)  | no_leak   | n/a                         |
| `zone1_intake_leak.csv`     | **zone1**      | zone1     | 0.102 / 0.10                |
| `zone3a_exhaust_leak.csv`   | **zone3a**     | zone3a    | 0.050 / 0.05                |
| `zone4_testcell_leak.csv`   | **zone4**      | zone4     | 0.098 / 0.10                |

3/3 leak zones predicted correctly; severity error <0.005 in all cases.

---

## Test suite

237 pytest tests pass on a clean checkout (full run takes ~17 minutes due to the Stage-3 evaluation tests):

```bash
python -m pytest leakfusion/tests/ -q
# 237 passed, 4 xfailed
```

The 51 demo-pipeline tests (CSV validation, derived fields, dashboard payload builders, sample loader, recommendations) run in under 4 seconds:

```bash
python -m pytest leakfusion/tests/demo/ -q
# 51 passed
```

Coverage on `leakfusion/src/demo/`: 90% (96-100% on every module except `samples.py:load_sample()` which is exercised by Streamlit at runtime).
