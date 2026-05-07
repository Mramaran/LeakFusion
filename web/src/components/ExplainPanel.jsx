import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { labelFor } from "../data/zones";

const EXPLANATIONS = {
  zone1:
    "R1 spike (intake mass balance) and R5 spike (lambda balance) together indicate air loss from the intake manifold or unmetered air entering pre-compressor — classic Zone 1 signature.",
  zone2:
    "Dominant R6 (thermal balance) anomaly with secondary R1, R2 deviation matches a post-compressor / intercooler joint leak — charge air bypassing the intercooler before reaching the manifold.",
  zone3a:
    "R3 (exhaust mass balance) and R6 (thermal balance) co-firing point to hot exhaust escape upstream of the turbine — exhaust-manifold gasket or pre-turbine seal failure.",
  zone3b:
    "R4 (aftertreatment ΔP) drop with secondary R3 anomaly indicates exhaust escape between the turbine outlet and the aftertreatment inlet flange.",
  zone4:
    "R1 (intake mass balance) deviation with R5 (lambda) shift, but no boost or thermal anomaly, fits a test-cell duct leak at the compressor inlet — unmetered air enters between MAF and compressor.",
};

const RESIDUAL_NAMES = {
  r1: "Intake Mass Balance",
  r2: "Boost Balance",
  r3: "Exhaust Mass Balance",
  r4: "AT Pressure Drop",
  r5: "Lambda Balance",
  r6: "Thermal Balance",
};

export default function ExplainPanel({
  reading,
  visible,
  onClose,
  onExportReport,
}) {
  // Calculate residual contributions
  const residualAbsValues = Object.entries(reading?.residuals || {})
    .map(([key, value]) => ({
      key,
      value,
      absValue: Math.abs(value),
    }))
    .sort((a, b) => b.absValue - a.absValue);

  const totalAbsValue =
    residualAbsValues.reduce((sum, r) => sum + r.absValue, 0) || 1;
  const contributions = residualAbsValues.map((r) => ({
    ...r,
    percentage: ((r.absValue / totalAbsValue) * 100).toFixed(1),
  }));

  const getBarColor = (sigma) => {
    if (sigma > 1.5) return "#ef4444";
    if (sigma > 0.5) return "#f59e0b";
    return "#22c55e";
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ x: 340, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 340, opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            position: "fixed",
            right: 0,
            top: 0,
            width: "340px",
            height: "100vh",
            background: "#0f1117",
            borderLeft: "1px solid #374151",
            overflowY: "auto",
            zIndex: 1000,
            boxShadow: "-4px 0 16px rgba(0, 0, 0, 0.8)",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "16px",
              borderBottom: "1px solid #374151",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <div>
              <h2
                style={{
                  margin: 0,
                  color: "#ffffff",
                  fontSize: "14px",
                  fontWeight: "bold",
                  marginBottom: "8px",
                }}
              >
                WHY DID THE MODEL FLAG THIS?
              </h2>
              <div
                style={{
                  display: "flex",
                  gap: "16px",
                  fontSize: "11px",
                  color: "#9ca3af",
                }}
              >
                <div>
                  Zone:{" "}
                  <span style={{ color: "#f59e0b", fontWeight: "bold" }}>
                    {reading?.detected_zone ? labelFor(reading.detected_zone) : "—"}
                  </span>
                </div>
                <div>
                  Confidence:{" "}
                  <span style={{ color: "#f59e0b", fontWeight: "bold" }}>
                    {Math.round(reading?.leak_probability || 0)}%
                  </span>
                </div>
                <div>
                  Severity:{" "}
                  <span style={{ color: "#f59e0b", fontWeight: "bold" }}>
                    {reading?.severity}/5
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                color: "#6b7280",
                cursor: "pointer",
                padding: "0",
                display: "flex",
                alignItems: "center",
              }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Content */}
          <div style={{ padding: "16px" }}>
            {/* Residual Contributions */}
            <div style={{ marginBottom: "20px" }}>
              <h3
                style={{
                  color: "#d1d5db",
                  fontSize: "12px",
                  fontWeight: "bold",
                  marginBottom: "12px",
                  margin: "0 0 12px 0",
                }}
              >
                RESIDUAL CONTRIBUTIONS
              </h3>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                {contributions.map((r, idx) => (
                  <motion.div
                    key={r.key}
                    initial={{ opacity: 0, width: "0%" }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.08 }}
                    style={{
                      fontSize: "11px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "4px",
                        color: "#d1d5db",
                      }}
                    >
                      <span style={{ fontWeight: "bold" }}>
                        {r.key.toUpperCase()} {RESIDUAL_NAMES[r.key]}
                      </span>
                      <span style={{ color: getBarColor(r.absValue) }}>
                        {r.percentage}%
                      </span>
                    </div>
                    <div
                      style={{
                        height: "6px",
                        background: "#1a1d27",
                        borderRadius: "2px",
                        overflow: "hidden",
                      }}
                    >
                      <motion.div
                        initial={{ width: "0%" }}
                        animate={{ width: `${r.percentage}%` }}
                        transition={{ delay: idx * 0.08 + 0.1, duration: 0.4 }}
                        style={{
                          height: "100%",
                          background: getBarColor(r.absValue),
                        }}
                      />
                    </div>
                    <div
                      style={{
                        color: "#6b7280",
                        fontSize: "10px",
                        marginTop: "2px",
                      }}
                    >
                      {r.value >= 0 ? "+" : ""}
                      {r.value.toFixed(1)}σ
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Plain English Explanation */}
            <div style={{ marginBottom: "20px" }}>
              <h3
                style={{
                  color: "#d1d5db",
                  fontSize: "12px",
                  fontWeight: "bold",
                  marginBottom: "8px",
                  margin: "0 0 8px 0",
                }}
              >
                PLAIN ENGLISH
              </h3>
              <p
                style={{
                  margin: 0,
                  fontSize: "11px",
                  color: "#9ca3af",
                  lineHeight: "1.5",
                }}
              >
                {EXPLANATIONS[reading?.detected_zone] ||
                  "Pattern analysis in progress..."}
              </p>
            </div>

            {/* Stats Row */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "11px",
                color: "#6b7280",
                marginBottom: "20px",
                paddingTop: "12px",
                borderTop: "1px solid #374151",
              }}
            >
              <div>
                <span style={{ fontWeight: "bold" }}>CUSUM:</span>{" "}
                {(reading?.cusum_score || 0).toFixed(1)}
              </div>
              <div style={{ color: "#9ca3af" }}>|</div>
              <div>
                <span style={{ fontWeight: "bold" }}>Pattern:</span>{" "}
                {reading?.hdbscan_status}
              </div>
              <div style={{ color: "#9ca3af" }}>|</div>
              <div>
                <span style={{ fontWeight: "bold" }}>Window:</span> 60s
              </div>
            </div>

            {/* Export Report Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={onExportReport}
              style={{
                width: "100%",
                background: "#f59e0b",
                color: "#000000",
                padding: "10px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: "bold",
                transition: "all 0.2s ease",
              }}
            >
              📋 Export Report
            </motion.button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
