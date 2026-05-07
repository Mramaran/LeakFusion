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
#    Drive link: https://drive.google.com/drive/folders/1iPdk_W1i3OHjIcB5eU37aDXJbuJrJGv0?usp=drive_link
#    Extract the archive directly into leakfusion/models/   (5 files)
#    Expected files after extraction:
#      leakfusion/models/calibration.json
#      leakfusion/models/cusum_config.json
#      leakfusion/models/stage3_features_schema.json
#      leakfusion/models/stage3_severity_xgb.joblib
#      leakfusion/models/stage3_zone_rf.joblib

# 3. Run the test suite (verifies pipeline + components)
python -m pytest leakfusion/tests/ -q

# 4. Launch the demo UI (pick one)
#    a) Streamlit — single-page verdict dashboard (no JS install needed)
python -m streamlit run leakfusion/ui/streamlit_app.py

#    b) React — round-2 demo with 3D engine viewer, FaultInjector, ExplainPanel
cd web && npm install && cd ..      # one-time
scripts/dev.ps1                     # launches FastAPI :8000 + Vite :5173 in 2 windows
```

> **Models are not in this repo** — they total ~78 MB and we share them via Google Drive instead (the repo is private, but joblibs are awkward to push and clone). The 5-file `leakfusion/models/` folder above is everything the dashboard needs.

The UI offers 4 pre-built sample CSVs (Healthy Run, Zone 1 Leak, Zone 3a Leak, Zone 4 Leak) and an "Advanced: upload your own CSV" expander that accepts any CSV with the 17 SI sensor columns documented in [leakfusion/src/schema.py](leakfusion/src/schema.py).

---

## React UI (round-2 demo)

A new React/Vite dashboard lives in [`web/`](web/). It replays backend-computed `Reading` payloads at 800 ms cadence to keep the demo paced like the Streamlit version, but adds:

- **3D engine viewer** (react-three-fiber) — meshes light up red on the predicted leak zone, with smoke particles + auto-camera focus.
- **5 backend-keyed zones** (`zone1`..`zone4`) rendered with physics-correct labels — see [docs/INTEGRATION_DECISIONS.md](docs/INTEGRATION_DECISIONS.md) for the canonical key/label/mesh table.
- **FaultInjector** — manual override that overlays the physics signature for any zone onto the live reading (UI-only mock; does not write back to the backend).
- **ExplainPanel** + **PDF report export** (`@react-pdf/renderer`).
- **HDBSCANAlert** — surfaces frames where Stage 3's signature catalog returns "novel" so the user knows the prediction was withheld.

### How it talks to the backend

`web/` proxies `/api/*` to FastAPI on `127.0.0.1:8000` (configured in [`vite.config.js`](web/vite.config.js)). On mount it `GET /api/sample/zone3a_exhaust_leak`; the SamplePicker dropdown lets you switch to any of the 4 demo samples; the "Choose file…" button uploads any conformant CSV via `POST /api/process`.

### Endpoints

| Method | Path                  | Purpose                                                              |
|--------|-----------------------|----------------------------------------------------------------------|
| GET    | `/api/health`         | Readiness probe.                                                     |
| GET    | `/api/samples`        | List the 4 pre-built demo samples (key/label/icon).                  |
| GET    | `/api/sample/{key}`   | Run the full Stage 1→2→3 pipeline on a demo sample, return readings. |
| POST   | `/api/process`        | Same, but on a CSV uploaded via multipart form.                      |

### Streamlit fallback

The Streamlit dashboard at [`leakfusion/ui/streamlit_app.py`](leakfusion/ui/streamlit_app.py) is unchanged and remains the documented fallback if the React stack is unavailable during the demo.

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
|   |-- api/                   # FastAPI service for the React UI (NEW for round-2 demo)
|   |   |-- main.py            #   /api/health, /api/samples, /api/sample/{key}, /api/process
|   |   |-- adapter.py         #   residuals_df + events -> Reading payloads
|   |   `-- schemas.py         #   Pydantic v2 schemas (5 backend zones)
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
|-- web/                       # React + Vite dashboard (NEW for round-2 demo)
|   |-- src/
|   |   |-- components/        # Dashboard, EngineViewer3D, FaultInjector, ExplainPanel, ...
|   |   |-- data/              # zones.js (source of truth), apiStream.js, mockStream.js
|   |   `-- hooks/             # useReport.jsx (PDF export)
|   |-- vite.config.js         # Proxies /api -> http://127.0.0.1:8000
|   `-- package.json
|-- scripts/
|   `-- dev.ps1                # Launch FastAPI + Vite together (Windows)
|-- docs/
|   `-- INTEGRATION_DECISIONS.md   # Canonical zone keys/labels + mesh map
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

200+ pytest tests pass on a clean checkout (full run takes ~11 minutes due to the Stage-3 evaluation tests):

```bash
python -m pytest leakfusion/tests/ -q
# 200 passed, 33 skipped
```

The 51 demo-pipeline tests (CSV validation, derived fields, dashboard payload builders, sample loader, recommendations) run in under 4 seconds:

```bash
python -m pytest leakfusion/tests/demo/ -q
# 51 passed
```

The 13 API tests cover the FastAPI surface end-to-end, including 3 e2e tests that drive the real Stage 1→2→3 pipeline through the public endpoints:

```bash
python -m pytest leakfusion/tests/api/ -q
# 13 passed in ~12s
```

Coverage on `leakfusion/src/demo/`: 90% (96-100% on every module except `samples.py:load_sample()` which is exercised by Streamlit/FastAPI at runtime).
