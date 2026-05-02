"""Computed display strings + status badges for the demo dashboard."""
from __future__ import annotations


def severity_label(sev: float) -> str:
    pct = sev * 100
    if sev < 0.05:
        bucket = "Low"
    elif sev < 0.10:
        bucket = "Moderate"
    else:
        bucket = "High"
    return f"{bucket} (~{pct:.1f}% flow loss)"


def decision(event: dict) -> str:
    if event.get("tier") == "CRITICAL" and event.get("predicted_severity") is not None \
            and event["predicted_severity"] >= 0.075:
        return "NO-GO"
    return "GO"


def confidence_pct(proba: float | None) -> str:
    if proba is None:
        return "n/a"
    return f"{proba * 100:.1f}%"


ZONE_DISPLAY: dict[str, str] = {
    "zone1":   "Zone 1 — Intake Manifold",
    "zone2":   "Zone 2 — Post-Compressor / Intercooler",
    "zone3a":  "Zone 3a — Exhaust Pre-Aftertreatment",
    "zone3b":  "Zone 3b — Post-Turbine / AT Inlet",
    "zone4":   "Zone 4 — Test-Cell Ducting",
    "no_leak": "No Leak Detected",
    "unknown": "Unknown",
}


def residual_status_badge(
    name: str,
    z: float,
    fired_residuals: set[str],
    primary: str | None,
) -> tuple[str, str]:
    """Return (label, color) for one residual.

    label  in {NORMAL, LOW-SUPPORTING, LOW-CONFIRMING, HIGH-PRIMARY, HIGH-CONFIRMING}
    color  in {green, orange, red}
    """
    abs_z = abs(z)
    if abs_z < 2.0:
        return ("NORMAL", "green")
    if abs_z >= 3.0:
        if name == primary:
            return ("HIGH-PRIMARY", "red")
        return ("HIGH-CONFIRMING", "red")
    # 2.0 <= abs_z < 3.0
    if name in fired_residuals:
        return ("LOW-CONFIRMING", "orange")
    return ("LOW-SUPPORTING", "orange")
