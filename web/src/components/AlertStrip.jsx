import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";
import { AlertCircle, AlertTriangle, CheckCircle } from "lucide-react";
import { labelFor } from "../data/zones";

// Mirror Streamlit's 3-state status banner:
//   tier "CRITICAL" -> red    "LEAK DETECTED"
//   tier "WARN"     -> yellow "EARLY WARNING - investigate"
//   no event        -> green  "All systems healthy"
const STATE_STYLES = {
  critical: { bg: "#3a2020", fg: "#ff6666", iconColor: "#ff6666" },
  warn:     { bg: "#3a3a1a", fg: "#FFCC00", iconColor: "#FFCC00" },
  healthy:  { bg: "#1a3a1a", fg: "#66ff66", iconColor: "#66ff66" },
};

function pickState(reading) {
  if (reading?.alert_triggered) return "critical";
  if (reading?.event_tier === "WARN") return "warn";
  return "healthy";
}

export default function AlertStrip({ reading }) {
  const state = pickState(reading);
  const style = STATE_STYLES[state];
  const [secondsSinceAlert, setSecondsSinceAlert] = useState(0);
  const [previousAlertState, setPreviousAlertState] = useState(false);

  useEffect(() => {
    if (reading.alert_triggered && !previousAlertState) {
      setSecondsSinceAlert(0);
      setPreviousAlertState(true);
    } else if (!reading.alert_triggered && previousAlertState) {
      setPreviousAlertState(false);
    }
  }, [reading.alert_triggered, previousAlertState]);

  useEffect(() => {
    if (!reading.alert_triggered) return;
    const interval = setInterval(() => {
      setSecondsSinceAlert((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [reading.alert_triggered]);

  const headline =
    state === "critical"
      ? "LEAK DETECTED"
      : state === "warn"
        ? "EARLY WARNING — investigate"
        : "All systems healthy — No leak detected";

  const Icon =
    state === "critical"
      ? AlertCircle
      : state === "warn"
        ? AlertTriangle
        : CheckCircle;

  return (
    <AnimatePresence>
      <motion.div
        key={state}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20 }}
        transition={{ duration: 0.3 }}
        style={{
          width: "100%",
          padding: "16px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          backgroundColor: style.bg,
          color: style.fg,
        }}
      >
        {/* Left section — icon + headline */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <motion.div
            animate={
              state === "critical"
                ? { scale: [1, 1.2, 1] }
                : state === "warn"
                  ? { scale: [1, 1.1, 1] }
                  : { scale: [1, 1.15, 1] }
            }
            transition={{
              duration: state === "critical" ? 0.8 : 1.5,
              repeat: Infinity,
            }}
          >
            <Icon size={28} style={{ color: style.iconColor }} />
          </motion.div>
          <div
            style={{
              fontSize: "16px",
              fontWeight: state === "critical" ? "bold" : "600",
              color: style.fg,
            }}
          >
            {headline}
          </div>
        </div>

        {/* Center section — zone + severity + HDBSCAN (alert states only) */}
        {(state === "critical" || state === "warn") && reading.detected_zone && (
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div style={{ fontSize: "14px", fontWeight: "500", color: "#ccc" }}>
              Zone: {labelFor(reading.detected_zone)}
            </div>
            {state === "critical" && (
              <div style={{ display: "flex", gap: "4px" }}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    style={{
                      width: "10px",
                      height: "10px",
                      borderRadius: "2px",
                      backgroundColor:
                        i < reading.severity
                          ? reading.severity >= 4
                            ? "#ff3333"
                            : "#FFCC00"
                          : "#666",
                    }}
                  />
                ))}
              </div>
            )}
            <div
              style={{
                fontSize: "12px",
                fontWeight: "600",
                padding: "4px 8px",
                borderRadius: "4px",
                backgroundColor:
                  reading.hdbscan_status === "Known Pattern"
                    ? "#1a3a1a"
                    : "#3a3a1a",
                color:
                  reading.hdbscan_status === "Known Pattern"
                    ? "#66ff66"
                    : "#FFCC00",
                border: `1px solid ${
                  reading.hdbscan_status === "Known Pattern"
                    ? "#66ff66"
                    : "#FFCC00"
                }`,
              }}
            >
              {state === "warn" ? "Watching" : reading.hdbscan_status}
            </div>
          </div>
        )}

        {/* Right section — confidence + timer (CRITICAL only) */}
        {state === "critical" && (
          <div className="text-xs text-gray-100 text-right">
            <div className="font-semibold">
              Confidence:{" "}
              {Math.round(
                Math.max(...Object.values(reading.zone_probabilities)) * 100,
              )}
              %
            </div>
            <div className="text-gray-300">
              {secondsSinceAlert}s since detection
            </div>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
