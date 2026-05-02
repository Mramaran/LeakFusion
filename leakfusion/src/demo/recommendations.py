"""Enriched per-zone inspection actions for the demo dashboard."""
from __future__ import annotations


ZONE_ACTIONS: dict[str, dict] = {
    "zone1": {
        "headline": "Inspect intake manifold gasket and pre-compressor ducting",
        "bullets": [
            "Check intake manifold-to-head gasket for cracks",
            "Inspect MAF sensor housing seal",
            "Verify air filter housing clamp torque",
        ],
    },
    "zone2": {
        "headline": "Inspect post-compressor / intercooler joints",
        "bullets": [
            "Check intercooler inlet and outlet hose clamps",
            "Inspect intercooler core for fin damage or thermal fatigue",
            "Verify charge-air pipe gasket integrity",
        ],
    },
    "zone3a": {
        "headline": "Inspect exhaust manifold gasket and pre-turbine seals",
        "bullets": [
            "Check manifold-to-turbine flange bolts",
            "Verify turbine inlet connection integrity",
            "Inspect exhaust manifold studs for thermal stress",
        ],
    },
    "zone3b": {
        "headline": "Inspect post-turbine pipe and aftertreatment inlet flange",
        "bullets": [
            "Check turbine outlet V-band clamp",
            "Inspect DPF inlet flange gasket",
            "Verify aftertreatment housing mounting bolts",
        ],
    },
    "zone4": {
        "headline": "Inspect test-cell ducting at compressor inlet",
        "bullets": [
            "Verify intake duct flange seal at compressor inlet",
            "Check test-cell to engine adapter clamps",
            "Inspect for cell-side ducting cracks",
        ],
    },
}

_NO_LEAK_ACTION = {
    "headline": "No action required - continue monitoring",
    "bullets": [
        "All 6 residuals within +/-2 sigma tolerance",
        "Schedule next routine inspection per maintenance plan",
    ],
}


def get_action(zone: str) -> dict:
    """Return the recommended action dict for a zone. Safe for unknown zones."""
    if zone == "no_leak":
        return _NO_LEAK_ACTION
    return ZONE_ACTIONS.get(zone, {
        "headline": f"Unknown zone '{zone}' - manual investigation required",
        "bullets": ["Cross-check with maintenance log", "Escalate to lead engineer"],
    })
