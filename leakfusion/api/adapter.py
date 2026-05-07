from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from leakfusion.api.schemas import Reading, Residuals, ZoneProbabilities

_ZONE_KEYS = ("zone1", "zone2", "zone3a", "zone3b", "zone4")
_UNIFORM = {k: 0.2 for k in _ZONE_KEYS}


def _frame_in_event(idx: int, event: dict) -> bool:
    start = event["timestamp_idx"]
    end = event.get("end_idx", start + 30)  # default 3 s window @ 10 Hz
    return start <= idx <= end


def residuals_and_events_to_readings(
    residuals_df: pd.DataFrame,
    events: list[dict],
    source_df: pd.DataFrame,
    *,
    base_timestamp: datetime | None = None,
) -> list[Reading]:
    """Convert backend residuals + Stage 2/3 events into UI-ready Reading payloads.

    Backend zone keys (zone1..zone4) flow through unchanged — UI keeps backend
    keys as canonical. Frames inside an event window inherit the event's
    predicted zone, severity, and HDBSCAN status; frames outside report
    healthy state with uniform 0.2 zone probabilities.
    """
    base_timestamp = base_timestamp or datetime.now(timezone.utc)
    readings: list[Reading] = []

    for _, row in residuals_df.iterrows():
        idx = int(row["row_index"])
        active_event = next(
            (e for e in events if _frame_in_event(idx, e)), None
        )

        # Mirror Streamlit's 3-state status banner:
        #   - no event             -> ALL CLEAR (green, no alert, no tier)
        #   - WARN event           -> EARLY WARNING (yellow on UI, alert_triggered=False
        #                             so the 3D viewer does not pulse and the HDBSCAN
        #                             escalation popup does not fire — but event_tier="WARN"
        #                             plus detected_zone surface the ML's best guess)
        #   - CRITICAL event       -> LEAK CONFIRMED (red, full alert path)
        tier = active_event.get("tier") if active_event else None
        is_critical = tier == "CRITICAL"
        is_warn = tier == "WARN"

        if active_event is None:
            zp = dict(_UNIFORM)
            detected = None
            severity = 0
            leak_prob = 0
            hdbscan = "Known Pattern"
            alert = False
            event_tier = None
        else:
            backend_zone = active_event.get("predicted_zone")
            proba = float(active_event.get("predicted_zone_proba") or 0.85)
            sev_raw = active_event.get("predicted_severity") or 0.0
            # Round half up so 0.05 → 3 (intuitive for severity 0..5).
            # Python's built-in round() uses banker's rounding which would give 2.
            severity_full = max(0, min(5, int(sev_raw * 50 + 0.5)))
            leak_prob_full = max(0, min(100, int(round(proba * 100))))
            hdbscan_full = (
                "Unknown — flag for review"
                if active_event.get("signature_status") == "novel"
                else "Known Pattern"
            )
            zp = {k: 0.05 for k in _ZONE_KEYS}
            if backend_zone in _ZONE_KEYS:
                zp[backend_zone] = proba
            detected = backend_zone if backend_zone in _ZONE_KEYS else None

            if is_critical:
                # Full leak path: alert + HDBSCAN signal + 3D pulse.
                severity = severity_full
                leak_prob = leak_prob_full
                hdbscan = hdbscan_full
                alert = True
                event_tier = "CRITICAL"
            elif is_warn:
                # Yellow watch state: surface the ML's candidate zone and the
                # event tier, but do NOT trigger the full alert path. HDBSCAN
                # is forced to "Known Pattern" so the escalation popup stays
                # closed (Streamlit's WARN banner doesn't escalate either).
                severity = 0
                leak_prob = leak_prob_full
                hdbscan = "Known Pattern"
                alert = False
                event_tier = "WARN"
            else:
                # Unknown tier — treat as healthy/uniform.
                zp = dict(_UNIFORM)
                detected = None
                severity = 0
                leak_prob = 0
                hdbscan = "Known Pattern"
                alert = False
                event_tier = None

        cusum = max(abs(float(row[f"z_R{j}"])) for j in range(1, 7))

        readings.append(Reading(
            timestamp=base_timestamp.isoformat(),
            reading_index=idx + 1,
            rpm=int(round(float(source_df.iloc[idx]["engine_rpm"]))),
            load_percent=round(float(source_df.iloc[idx]["load_fraction"]) * 100, 1),
            is_steady_state=True,
            residuals=Residuals(
                # Send z-scores, not raw residuals. The UI displays these with a
                # σ suffix and uses z-score thresholds (|x|≥3 = CRITICAL); raw
                # values like R6 in Kelvin (~10-80 K typical) would always show
                # CRITICAL. Streamlit's build_residual_bars_payload also reads
                # the z_R{i} columns — this matches.
                r1=float(row["z_R1"]), r2=float(row["z_R2"]), r3=float(row["z_R3"]),
                r4=float(row["z_R4"]), r5=float(row["z_R5"]), r6=float(row["z_R6"]),
            ),
            zone_probabilities=ZoneProbabilities(**zp),
            detected_zone=detected,
            severity=severity,
            cusum_score=round(cusum, 2),
            hdbscan_status=hdbscan,
            alert_triggered=alert,
            leak_probability=leak_prob,
            event_tier=event_tier,
        ))
    return readings
