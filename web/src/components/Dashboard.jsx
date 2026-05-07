import React, { useState, useEffect, useRef } from "react";
import { ApiEngineStream } from "../data/apiStream";
// MockEngineStream is the offline fallback if the FastAPI backend is unavailable.
// eslint-disable-next-line no-unused-vars
import { MockEngineStream } from "../data/mockStream";
import MetricCards from "./MetricCards";
import ZoneSeverity from "./ZoneSeverity";
import ResidualChart from "./ResidualChart";
import ResidualsBarChart from "./ResidualsBarChart";
import AlertStrip from "./AlertStrip";
import EngineViewer3D from "./EngineViewer3D";
import FaultInjector from "./FaultInjector";
import ExplainPanel from "./ExplainPanel";
import ReportExport from "./ReportExport";
import HDBSCANAlert from "./HDBSCANAlert";
import SamplePicker from "./SamplePicker";
import CsvUploader from "./CsvUploader";
import Scrubber from "./Scrubber";
import { useReport } from "../hooks/useReport.jsx";

const DEFAULT_SAMPLE_KEY = "zone3a_exhaust_leak";
const TICK_MS = 800;
const HISTORY_WINDOW = 60;

export default function Dashboard() {
  const [readings, setReadings] = useState([]);          // full backend payload, indexable
  const [frameIdx, setFrameIdx] = useState(0);           // scrubber-controlled cursor
  const [playing, setPlaying] = useState(true);          // auto-advance when true
  const [injectedFault, setInjectedFault] = useState(null);
  const [showExplain, setShowExplain] = useState(false);
  const [sampleKey, setSampleKey] = useState(DEFAULT_SAMPLE_KEY);
  const [sampleLabel, setSampleLabel] = useState(null);
  const [streamError, setStreamError] = useState(null);
  const streamRef = useRef(new ApiEngineStream());
  const { generateReport } = useReport();

  // Auto-advance the cursor at TICK_MS while playing. When the cursor reaches
  // the end of the readings list it loops back to 0 (matches the previous
  // streaming behaviour, just driven by an explicit cursor instead of the
  // ApiEngineStream's internal idx).
  useEffect(() => {
    if (!playing || readings.length === 0) return;
    const id = setInterval(() => {
      setFrameIdx((prev) => (prev + 1) % readings.length);
    }, TICK_MS);
    return () => clearInterval(id);
  }, [playing, readings.length]);

  const adoptReadings = (newReadings) => {
    setReadings(newReadings);
    setFrameIdx(0);
    setPlaying(true);
  };

  // Initial mount: load the default sample.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const label = await streamRef.current.load(DEFAULT_SAMPLE_KEY);
        if (cancelled) return;
        setStreamError(null);
        setSampleLabel(label);
        adoptReadings(streamRef.current.readings);
      } catch (err) {
        if (cancelled) return;
        setStreamError(err.message || "Failed to load default sample");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectSample = async (key) => {
    if (!key || key === sampleKey) return;
    setInjectedFault(null);
    setSampleKey(key);
    streamRef.current = new ApiEngineStream();
    try {
      const label = await streamRef.current.load(key);
      setStreamError(null);
      setSampleLabel(label);
      adoptReadings(streamRef.current.readings);
    } catch (err) {
      setStreamError(err.message || `Failed to load sample ${key}`);
    }
  };

  const handleUpload = async (file) => {
    setInjectedFault(null);
    setSampleKey(`upload:${file.name}`);
    streamRef.current = new ApiEngineStream();
    try {
      const label = await streamRef.current.loadFromFile(file);
      setStreamError(null);
      setSampleLabel(label);
      adoptReadings(streamRef.current.readings);
    } catch (err) {
      setStreamError(err.message || "Upload failed");
    }
  };

  // Scrubber controls — pause auto-advance whenever the user manipulates the
  // cursor manually so they can hold on a frame to point things out.
  const handleSeek = (idx) => {
    setPlaying(false);
    setFrameIdx(Math.max(0, Math.min(readings.length - 1, idx)));
  };
  const handleStep = (delta) => {
    setPlaying(false);
    setFrameIdx((prev) =>
      Math.max(0, Math.min(readings.length - 1, prev + delta)),
    );
  };
  const handlePlayPause = () => setPlaying((p) => !p);
  const handleScrubReset = () => {
    setPlaying(false);
    setFrameIdx(0);
  };

  // Derived values for the rest of the dashboard.
  const reading = readings[frameIdx] ?? null;
  const history = readings.slice(
    Math.max(0, frameIdx - (HISTORY_WINDOW - 1)),
    frameIdx + 1,
  );
  const readingCount = readings.length === 0 ? 0 : frameIdx + 1;

  // Handle fault injection
  const handleInjectFault = (zone, severity) => {
    setInjectedFault({ zone, severity });
  };

  const handleReset = () => {
    setInjectedFault(null);
  };

  // Apply fault injection to reading if active.
  // injectedFault.zone is a backend key (zone1..zone4); the residual spike
  // pattern below mirrors the physics signature catalog (see INTEGRATION_DECISIONS.md).
  let displayReading = reading;
  if (reading && injectedFault) {
    const ZONE_RESIDUALS = {
      zone1: {
        r1: 2.8 + injectedFault.severity * 0.5,
        r2: 2.0 + injectedFault.severity * 0.3,
        r5: 2.4 + injectedFault.severity * 0.3,
      },
      zone2: {
        r1: 2.0 + injectedFault.severity * 0.3,
        r2: 2.2 + injectedFault.severity * 0.4,
        r6: 2.9 + injectedFault.severity * 0.4,
      },
      zone3a: {
        r3: 2.9 + injectedFault.severity * 0.4,
        r6: 2.7 + injectedFault.severity * 0.4,
      },
      zone3b: {
        r3: 2.4 + injectedFault.severity * 0.3,
        r4: 3.1 + injectedFault.severity * 0.4,
      },
      zone4: {
        r1: 2.6 + injectedFault.severity * 0.4,
        r5: 2.5 + injectedFault.severity * 0.4,
      },
    };

    const residualSpikes = ZONE_RESIDUALS[injectedFault.zone] || {};
    displayReading = {
      ...reading,
      detected_zone: injectedFault.zone,
      severity: injectedFault.severity,
      alert_triggered: true,
      leak_probability: 85 + injectedFault.severity * 2,
      hdbscan_status: "Known Pattern",
      residuals: {
        r1: residualSpikes.r1 ?? reading.residuals.r1,
        r2: residualSpikes.r2 ?? reading.residuals.r2,
        r3: residualSpikes.r3 ?? reading.residuals.r3,
        r4: residualSpikes.r4 ?? reading.residuals.r4,
        r5: residualSpikes.r5 ?? reading.residuals.r5,
        r6: residualSpikes.r6 ?? reading.residuals.r6,
      },
    };
  }

  if (!reading) {
    return (
      <div
        className="text-white"
        style={{ padding: "24px", fontFamily: "monospace" }}
      >
        {streamError ? (
          <>
            <div style={{ color: "#ef4444", fontWeight: "bold" }}>
              Failed to load from /api: {streamError}
            </div>
            <div style={{ marginTop: "8px", color: "#999" }}>
              Make sure the FastAPI server is running on port 8000
              (<code>scripts/dev.ps1</code> launches both).
            </div>
          </>
        ) : (
          "Loading…"
        )}
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-screen w-screen text-white"
      style={{ height: "100vh", width: "100vw", backgroundColor: "#1a1a1a" }}
    >
      {/* Top Bar - Caterpillar Yellow & Black */}
      <div
        style={{
          padding: "16px 24px",
          borderBottom: "4px solid #FFCC00",
          backgroundColor: "#000000",
          flexShrink: 0,
        }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h1
              style={{
                fontSize: "28px",
                fontWeight: "bold",
                color: "#FFCC00",
                margin: 0,
              }}
            >
              CAT Engine Leak Detection
            </h1>
            <p style={{ fontSize: "12px", color: "#999", margin: "4px 0 0 0" }}>
              Engine ID: CAT-3516B-042
            </p>
          </div>

          <div style={{ display: "flex", gap: "24px", alignItems: "center" }}>
            {/* Sample Picker + Uploader */}
            <SamplePicker
              value={sampleKey}
              onSelectSample={handleSelectSample}
            />
            <CsvUploader onUpload={handleUpload} />

            {/* Status Badge — 3 states matching Streamlit's status banner */}
            {(() => {
              const isCritical = displayReading.alert_triggered;
              const isWarn =
                !isCritical && displayReading.event_tier === "WARN";
              const bg = isCritical ? "#cc3300" : isWarn ? "#a07a00" : "#006600";
              const ring = isCritical
                ? "#ff6600"
                : isWarn
                  ? "#FFCC00"
                  : "#FFCC00";
              const label = isCritical
                ? "🔴 LEAK ACTIVE"
                : isWarn
                  ? "🟡 EARLY WARNING"
                  : "🟢 HEALTHY";
              return (
                <div
                  style={{
                    padding: "8px 16px",
                    borderRadius: "6px",
                    fontWeight: "600",
                    fontSize: "14px",
                    backgroundColor: bg,
                    color: "#fff",
                    border: `2px solid ${ring}`,
                  }}
                >
                  {label}
                </div>
              );
            })()}

            {/* Steady State Badge */}
            <div
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                fontWeight: "600",
                fontSize: "14px",
                backgroundColor: displayReading.is_steady_state
                  ? "#333333"
                  : "#666600",
                color: displayReading.is_steady_state ? "#FFCC00" : "#FFFF99",
                border: "2px solid #FFCC00",
              }}
            >
              {displayReading.is_steady_state ? "STEADY" : "TRANSIENT"}
            </div>

            {/* Reading Counter */}
            <div style={{ fontSize: "14px", color: "#FFCC00" }}>
              Reading:{" "}
              <span style={{ fontWeight: "600", fontSize: "16px" }}>
                {readingCount}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - 3D Viewer + Metrics */}
      <div
        style={{
          flex: "1 1 auto",
          display: "flex",
          overflow: "hidden",
          minHeight: "400px",
          maxHeight: "calc(100vh - 100px)",
        }}
      >
        {/* Left: 3D Engine Viewer - 60% */}
        <div
          style={{
            width: "60%",
            padding: "16px",
            gap: "16px",
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
            height: "100%",
          }}
        >
          <div style={{ flex: 1, minHeight: 0, width: "100%", height: "100%" }}>
            <EngineViewer3D reading={displayReading} />
          </div>
        </div>

        {/* Right: Metrics and Zone Severity - 40% */}
        <div
          style={{
            width: "40%",
            padding: "16px",
            gap: "16px",
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
            flexShrink: 0,
            height: "100%",
            backgroundColor: "#0a0a0a",
            borderLeft: "2px solid #333333",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: "14px",
                fontWeight: "600",
                color: "#FFCC00",
                marginBottom: "12px",
              }}
            >
              SYSTEM METRICS
            </h2>
            <MetricCards reading={displayReading} />
          </div>

          <div>
            <h2
              style={{
                fontSize: "14px",
                fontWeight: "600",
                color: "#FFCC00",
                marginBottom: "12px",
              }}
            >
              ZONE SEVERITY
            </h2>
            <ZoneSeverity reading={displayReading} />
          </div>

          <div>
            <FaultInjector
              onInject={handleInjectFault}
              onReset={handleReset}
              isLeakActive={!!injectedFault}
            />
          </div>
        </div>
      </div>

      {/* Frame Scrubber — pause/play + seek to any row of the CSV */}
      <div
        style={{
          padding: "8px 16px",
          backgroundColor: "#0a0a0a",
          borderTop: "2px solid #333",
          flexShrink: 0,
        }}
      >
        <Scrubber
          frameIdx={frameIdx}
          totalFrames={readings.length}
          playing={playing}
          onSeek={handleSeek}
          onStep={handleStep}
          onPlayPause={handlePlayPause}
          onReset={handleScrubReset}
        />
      </div>

      {/* Middle: Residual Signals Bar Chart */}
      <div
        style={{
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
          backgroundColor: "#0a0a0a",
          borderTop: "2px solid #333",
        }}
      >
        <ResidualsBarChart reading={displayReading} />
      </div>

      {/* Residual Trends Line Chart */}
      <div
        style={{
          height: "256px",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
          backgroundColor: "#0a0a0a",
          borderTop: "2px solid #333",
        }}
      >
        <h2
          style={{
            fontSize: "14px",
            fontWeight: "600",
            color: "#FFCC00",
            marginBottom: "12px",
          }}
        >
          RESIDUAL TRENDS (Last 60 Readings)
        </h2>
        <div style={{ flex: 1, minHeight: 0 }}>
          <ResidualChart history={history} />
        </div>
      </div>

      {/* Bottom: Alert Strip */}
      <div
        style={{
          borderTop: "3px solid #FFCC00",
          backgroundColor: "#000000",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: "12px",
            padding: "16px 24px",
            alignItems: "center",
          }}
        >
          <div style={{ flex: 1 }}>
            <AlertStrip reading={displayReading} />
          </div>
          {displayReading.alert_triggered && (
            <>
              <button
                onClick={() => setShowExplain(true)}
                style={{
                  background: "#3b82f6",
                  color: "#ffffff",
                  padding: "8px 14px",
                  borderRadius: "6px",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: "bold",
                  whiteSpace: "nowrap",
                }}
              >
                Why this zone? →
              </button>
              <ReportExport reading={displayReading} disabled={false} />
            </>
          )}
        </div>
      </div>

      {/* HDBSCANAlert - slides down when unknown pattern */}
      <div
        style={{
          position: "absolute",
          top: "80px",
          left: "24px",
          right: "24px",
          zIndex: 500,
        }}
      >
        <HDBSCANAlert reading={displayReading} />
      </div>

      {/* ExplainPanel - slides in from right */}
      <ExplainPanel
        reading={displayReading}
        visible={showExplain}
        onClose={() => setShowExplain(false)}
        onExportReport={() => {
          generateReport(displayReading);
          setShowExplain(false);
        }}
      />
    </div>
  );
}
