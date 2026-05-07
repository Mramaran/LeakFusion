import { useEffect, useState } from "react";

export default function SamplePicker({ value, onSelectSample, disabled }) {
  const [samples, setSamples] = useState([]);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch("/api/samples");
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const body = await r.json();
        if (!cancelled) setSamples(body);
      } catch (err) {
        if (!cancelled) setLoadError(err.message || "Failed to load samples");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <label
        style={{
          fontSize: "10px",
          color: "#999",
          fontWeight: "bold",
          letterSpacing: "0.5px",
        }}
      >
        SAMPLE
      </label>
      <select
        value={value || ""}
        onChange={(e) => onSelectSample(e.target.value)}
        disabled={disabled || samples.length === 0}
        style={{
          background: "#1a1d27",
          color: "#FFCC00",
          border: "1px solid #FFCC00",
          borderRadius: "4px",
          padding: "6px 10px",
          fontSize: "12px",
          fontWeight: "600",
          cursor: disabled ? "not-allowed" : "pointer",
          minWidth: "180px",
        }}
      >
        {samples.length === 0 && (
          <option value="">{loadError ? "API offline" : "Loading…"}</option>
        )}
        {samples.map((s) => (
          <option key={s.key} value={s.key}>
            {s.label}
          </option>
        ))}
      </select>
      {loadError && (
        <span style={{ fontSize: "10px", color: "#ef4444" }}>{loadError}</span>
      )}
    </div>
  );
}
