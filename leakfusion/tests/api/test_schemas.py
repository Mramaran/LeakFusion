from leakfusion.api.schemas import Reading, Residuals, ZoneProbabilities


def test_reading_has_five_backend_zones():
    zp = ZoneProbabilities(zone1=0.2, zone2=0.2, zone3a=0.2, zone3b=0.2, zone4=0.2)
    r = Reading(
        timestamp="2026-05-03T10:00:00Z",
        reading_index=1,
        rpm=1800,
        load_percent=65.0,
        is_steady_state=True,
        residuals=Residuals(r1=0.0, r2=0.0, r3=0.0, r4=0.0, r5=0.0, r6=0.0),
        zone_probabilities=zp,
        detected_zone=None,
        severity=0,
        cusum_score=0.0,
        hdbscan_status="Known Pattern",
        alert_triggered=False,
        leak_probability=0,
    )
    payload = r.model_dump()
    assert set(payload["zone_probabilities"].keys()) == {
        "zone1", "zone2", "zone3a", "zone3b", "zone4"
    }
