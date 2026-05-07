"""End-to-end smoke tests: real Stage 1 -> Stage 2 -> Stage 3 pipeline through
the FastAPI surface. Slow (~5-10s each on a warm cache) — they fully exercise
the predictor on the demo CSV samples.
"""
from fastapi.testclient import TestClient

from leakfusion.api.main import app


def test_e2e_zone3a_sample_predicts_zone3a():
    c = TestClient(app)
    body = c.get("/api/sample/zone3a_exhaust_leak").json()
    leak_frames = [r for r in body["readings"] if r["alert_triggered"]]
    assert len(leak_frames) > 0
    assert any(r["detected_zone"] == "zone3a" for r in leak_frames)


def test_e2e_zone1_sample_predicts_zone1():
    c = TestClient(app)
    body = c.get("/api/sample/zone1_intake_leak").json()
    leak_frames = [r for r in body["readings"] if r["alert_triggered"]]
    assert any(r["detected_zone"] == "zone1" for r in leak_frames)


def test_e2e_healthy_run_no_critical_alerts():
    """The Stage 3 model has occasional WARN-tier false positives on
    healthy_run.csv (macro-F1 ~0.85). Those WARN events surface as the yellow
    'EARLY WARNING' state (event_tier='WARN', alert_triggered=False) — same as
    Streamlit. The CRITICAL leak path must NEVER fire on healthy data.
    """
    c = TestClient(app)
    body = c.get("/api/sample/healthy_run").json()
    assert len(body["readings"]) > 50
    alerted = [r for r in body["readings"] if r["alert_triggered"]]
    assert alerted == [], (
        f"Healthy CSV produced {len(alerted)} alerted frames (should be 0 — "
        "WARN events must not trigger alert_triggered)"
    )
    # WARN events on healthy_run are expected; just confirm none escalate.
    critical_tiered = [
        r for r in body["readings"] if r.get("event_tier") == "CRITICAL"
    ]
    assert critical_tiered == [], (
        f"Healthy CSV produced {len(critical_tiered)} CRITICAL-tiered frames"
    )
