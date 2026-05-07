from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from leakfusion.api.adapter import residuals_and_events_to_readings
from leakfusion.api.schemas import ProcessResponse, SampleListItem
from leakfusion.src.calibration.persist import load_calibration
from leakfusion.src.demo.csv_pipeline import CsvValidationError, process_sensor_csv
from leakfusion.src.demo.samples import SAMPLE_BUTTONS, load_sample
from leakfusion.src.load_estimator import add_load_fraction_column

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "leakfusion" / "models"
SAMPLES_DIR = PROJECT_ROOT / "leakfusion" / "data" / "demo_samples"

_artifacts_cache: dict = {}


def _load_artifacts() -> dict:
    if _artifacts_cache:
        return _artifacts_cache
    cal = load_calibration(str(MODELS_DIR / "calibration.json"))
    cusum = json.loads((MODELS_DIR / "cusum_config.json").read_text())
    predictor = None
    z = MODELS_DIR / "stage3_zone_rf.joblib"
    s = MODELS_DIR / "stage3_severity_xgb.joblib"
    f = MODELS_DIR / "stage3_features_schema.json"
    if z.exists() and s.exists() and f.exists():
        from leakfusion.src.ml.predict import ZoneSeverityPredictor
        zone_clf = joblib.load(z)
        sev_bundle = joblib.load(s)
        schema = json.loads(f.read_text())
        predictor = ZoneSeverityPredictor(
            zone_clf=zone_clf,
            severity_reg=sev_bundle["model"],
            severity_sigma=float(sev_bundle["sigma"]),
            feature_columns=schema["feature_columns"],
        )
    _artifacts_cache.update(cal=cal, cusum=cusum, predictor=predictor)
    return _artifacts_cache

app = FastAPI(title="LeakFusion API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "stage": "ready"}


@app.get("/api/samples", response_model=list[SampleListItem])
def list_samples():
    return [
        {"key": b["key"], "label": b["label"], "icon": b["icon"]}
        for b in SAMPLE_BUTTONS
    ]


@app.get("/api/sample/{key}", response_model=ProcessResponse)
def get_sample(key: str):
    if not any(b["key"] == key for b in SAMPLE_BUTTONS):
        raise HTTPException(404, f"Unknown sample: {key}")
    df = load_sample(SAMPLES_DIR, key)
    art = _load_artifacts()
    residuals_df, events = process_sensor_csv(
        df, art["cal"], art["cusum"], predictor=art["predictor"],
    )
    if "load_fraction" not in df.columns:
        df = add_load_fraction_column(df)
    readings = residuals_and_events_to_readings(
        residuals_df, events, df.reset_index(drop=True),
    )
    return {
        "sample_label": f"{key}.csv",
        "readings": [r.model_dump() for r in readings],
        "event_count": len(events),
    }


@app.post("/api/process", response_model=ProcessResponse)
async def process_upload(file: UploadFile = File(...)):
    raw = (await file.read()).decode("utf-8")
    try:
        df = pd.read_csv(StringIO(raw))
    except Exception as e:
        raise HTTPException(400, f"Failed to parse CSV: {e}")
    art = _load_artifacts()
    try:
        residuals_df, events = process_sensor_csv(
            df, art["cal"], art["cusum"], predictor=art["predictor"],
        )
    except CsvValidationError as e:
        raise HTTPException(400, str(e))
    if "load_fraction" not in df.columns:
        df = add_load_fraction_column(df)
    readings = residuals_and_events_to_readings(
        residuals_df, events, df.reset_index(drop=True),
    )
    return {
        "sample_label": file.filename or "uploaded.csv",
        "readings": [r.model_dump() for r in readings],
        "event_count": len(events),
    }
