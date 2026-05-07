// Single source of truth for backend zone keys + UI display labels.
// Backend keys are canonical; UI labels are presentation only.
export const ZONES = [
  { key: "zone1",  label: "Zone 1: Intake Manifold",        meshId: "intake_manifold"  },
  { key: "zone2",  label: "Zone 2: Intercooler",            meshId: "intercooler"      },
  { key: "zone3a", label: "Zone 3a: Exhaust Manifold",      meshId: "exhaust_manifold" },
  { key: "zone3b", label: "Zone 3b: Aftertreatment Inlet",  meshId: "at_cooler"        },
  { key: "zone4",  label: "Zone 4: Test-Cell Duct",         meshId: "compressor"       },
];

export const ZONE_KEYS = ZONES.map((z) => z.key);

export const labelFor = (key) => ZONES.find((z) => z.key === key)?.label ?? key;

// Inspection guidance per zone — same wording as the PDF Report Export
// (useReport.jsx) so the in-dashboard panel and the PDF report stay in sync.
export const ZONE_ACTIONS = {
  zone1:
    "Inspect intake manifold gasket and pre-compressor ducting · Check MAF placement · Look for unmetered air ingress between MAF and intake manifold.",
  zone2:
    "Inspect post-compressor / intercooler joints and hose clamps · Verify intercooler core integrity · Charge air may be bypassing the intercooler before the manifold.",
  zone3a:
    "Inspect exhaust manifold gaskets, studs, and pre-turbine seals · Check for carbon deposits indicating hot exhaust escape upstream of the turbine.",
  zone3b:
    "Inspect post-turbine pipe and aftertreatment inlet flange · Check ΔP sensor placement · Exhaust may be escaping between turbine outlet and AT inlet.",
  zone4:
    "Inspect test-cell duct at the compressor inlet · Verify cell-side seals · Unmetered air entering between MAF and compressor.",
};

export const recommendedAction = (reading) => {
  if (!reading)
    return "Continue normal operation · Monitor residuals for anomalies.";
  if (reading.alert_triggered && reading.detected_zone) {
    return (
      ZONE_ACTIONS[reading.detected_zone] ||
      "Contact field engineer for guidance."
    );
  }
  if (reading.event_tier === "WARN") {
    const target = reading.detected_zone
      ? labelFor(reading.detected_zone)
      : "candidate zone";
    return `Early warning — investigate ${target}. Hold current load and monitor; do not escalate yet.`;
  }
  return "Continue normal operation · Monitor residuals for anomalies.";
};
