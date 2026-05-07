from fastapi.testclient import TestClient

from leakfusion.api.main import SAMPLES_DIR, app


def test_health():
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "stage": "ready"}


def test_list_samples():
    c = TestClient(app)
    r = c.get("/api/samples")
    assert r.status_code == 200
    keys = {it["key"] for it in r.json()}
    assert keys == {
        "healthy_run",
        "zone1_intake_leak",
        "zone3a_exhaust_leak",
        "zone4_testcell_leak",
    }


def test_get_sample_returns_readings():
    c = TestClient(app)
    r = c.get("/api/sample/zone3a_exhaust_leak")
    assert r.status_code == 200
    body = r.json()
    assert len(body["readings"]) > 0
    leak_frames = [rd for rd in body["readings"] if rd["alert_triggered"]]
    assert len(leak_frames) > 0
    assert any(rd["detected_zone"] == "zone3a" for rd in leak_frames)


def test_get_sample_unknown_returns_404():
    c = TestClient(app)
    assert c.get("/api/sample/nope").status_code == 404


def test_post_process_with_uploaded_csv():
    c = TestClient(app)
    csv_path = SAMPLES_DIR / "healthy_run.csv"
    with open(csv_path, "rb") as f:
        r = c.post("/api/process", files={"file": ("healthy.csv", f, "text/csv")})
    assert r.status_code == 200
    assert len(r.json()["readings"]) > 0


def test_post_process_invalid_csv_returns_400():
    c = TestClient(app)
    r = c.post(
        "/api/process",
        files={"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")},
    )
    assert r.status_code == 400
