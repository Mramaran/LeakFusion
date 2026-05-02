"""LeakFusion demo UI - single-page verdict dashboard.

Launch from project root:
    python -m streamlit run leakfusion/ui/streamlit_app.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from leakfusion.src.demo.samples import SAMPLE_BUTTONS, load_sample

DATA_DIR = PROJECT_ROOT / "leakfusion" / "data"
SAMPLES_DIR = DATA_DIR / "demo_samples"

st.set_page_config(page_title="LeakFusion - Engine Air-Path Leak Detection", layout="wide")
st.title("LeakFusion - Engine Air-Path Leak Detection")
st.caption("Stage 1 (physics residuals) -> Stage 2 (CUSUM gating) -> Stage 3 (ML zone+severity)")

st.markdown("### Upload Sensor Data")
btn_cols = st.columns(len(SAMPLE_BUTTONS))
selected_csv: pd.DataFrame | None = None
selected_label: str | None = None

if "selected_key" not in st.session_state:
    st.session_state.selected_key = None
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = None

for i, b in enumerate(SAMPLE_BUTTONS):
    if btn_cols[i].button(b["label"], use_container_width=True, key=f"btn_{b['key']}"):
        st.session_state.selected_key = b["key"]
        st.session_state.uploaded_df = None

with st.expander("Advanced: upload your own CSV"):
    up = st.file_uploader("Sensor CSV (17 SI columns)", type=["csv"])
    if up is not None:
        try:
            st.session_state.uploaded_df = pd.read_csv(up)
            st.session_state.selected_key = None
            st.success(f"Uploaded {up.name}: {len(st.session_state.uploaded_df)} rows")
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")

if st.session_state.uploaded_df is not None:
    selected_csv = st.session_state.uploaded_df
    selected_label = "uploaded.csv"
elif st.session_state.selected_key is not None:
    try:
        selected_csv = load_sample(SAMPLES_DIR, st.session_state.selected_key)
        selected_label = f"{st.session_state.selected_key}.csv"
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

if selected_csv is None:
    st.info("Click a sample button above to load engine data, or expand 'Advanced' to upload your own CSV.")
    st.stop()

st.markdown(f"**Currently showing:** `{selected_label}` ({len(selected_csv)} rows)")
st.markdown("---")

import json

import joblib

from leakfusion.src.calibration.persist import load_calibration
from leakfusion.src.demo.csv_pipeline import process_sensor_csv, CsvValidationError
from leakfusion.src.demo.derived_fields import ZONE_DISPLAY
from leakfusion.ui.dashboard_components import (
    render_status_banner,
    render_residual_bars,
    render_recommendation,
    render_timeline_strip,
)

MODELS_DIR = PROJECT_ROOT / "leakfusion" / "models"


@st.cache_resource(show_spinner="Loading models...")
def _load_artifacts():
    cal = load_calibration(str(MODELS_DIR / "calibration.json"))
    cusum = json.loads((MODELS_DIR / "cusum_config.json").read_text())
    predictor = None
    z_path = MODELS_DIR / "stage3_zone_rf.joblib"
    s_path = MODELS_DIR / "stage3_severity_xgb.joblib"
    f_path = MODELS_DIR / "stage3_features_schema.json"
    if z_path.exists() and s_path.exists() and f_path.exists():
        from leakfusion.src.ml.predict import ZoneSeverityPredictor
        zone_clf = joblib.load(z_path)
        sev_bundle = joblib.load(s_path)
        schema = json.loads(f_path.read_text())
        predictor = ZoneSeverityPredictor(
            zone_clf=zone_clf,
            severity_reg=sev_bundle["model"],
            severity_sigma=float(sev_bundle["sigma"]),
            feature_columns=schema["feature_columns"],
        )
    return cal, cusum, predictor


cal, cusum, predictor = _load_artifacts()

try:
    with st.spinner("Computing residuals + running detector..."):
        residuals_df, events = process_sensor_csv(
            selected_csv, cal, cusum, predictor=predictor, persistence_seconds=3.0,
        )
except CsvValidationError as e:
    st.error(f"CSV validation failed: {e}")
    st.stop()

render_status_banner(st, events)

mean_rpm = float(selected_csv["engine_rpm"].mean())
load_pct = float(selected_csv["load_fraction"].mean()) * 100 if "load_fraction" in selected_csv.columns else None
status_str = "Steady State"
load_txt = f"Load: {load_pct:.0f}%" if load_pct is not None else "Load: n/a"
demo_id = pd.Timestamp.utcnow().strftime("%Y%m%d-%H%M")
st.markdown(
    f"_Engine: Navistar DT 7.6L - Demo Run #{demo_id}_ &nbsp;-&nbsp; "
    f"RPM: **{mean_rpm:,.0f}** &nbsp;-&nbsp; **{load_txt}** &nbsp;-&nbsp; Status: **{status_str}**"
)

duration_s = float(residuals_df.index[-1]) / 10.0 if len(residuals_df) else 0.0
if events:
    selected_index = render_timeline_strip(st, events, duration_s, selected_index=None)
    selected_event = events[selected_index] if selected_index is not None else events[-1]
else:
    selected_event = None

st.markdown("### Residual Signals")
if selected_event is not None:
    render_residual_bars(st, residuals_df, selected_event)
else:
    render_residual_bars(st, residuals_df, {"fired_residuals": [], "candidate_zones": []})

st.markdown("### Recommended Action")
render_recommendation(st, selected_event)

if "leak_zone" in selected_csv.columns:
    with st.expander("Show ground truth"):
        true_zone = str(selected_csv["leak_zone"].iloc[0])
        true_sev = float(selected_csv.get("leak_severity", pd.Series([0.0])).iloc[0])
        pred_zone = (selected_event or {}).get("predicted_zone")
        pred_sev = (selected_event or {}).get("predicted_severity")
        st.write({
            "true_zone": ZONE_DISPLAY.get(true_zone, true_zone),
            "true_severity": true_sev,
            "predicted_zone": ZONE_DISPLAY.get(pred_zone, pred_zone) if pred_zone else None,
            "predicted_severity": pred_sev,
            "match": (pred_zone == true_zone) if pred_zone else None,
        })

with st.expander("Show raw event JSON"):
    st.json(selected_event or {"info": "no event"})
