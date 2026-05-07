import { motion } from "framer-motion";
import { recommendedAction } from "../data/zones";

// Per-frame z-score view: each bar shows the residual at the current
// (scrubber-selected) frame. Stability comes from the user controlling
// the frame via the Scrubber — no windowing needed.
const RESIDUAL_LABELS = [
  { key: "r1", name: "R1: Intake Mass Balance" },
  { key: "r2", name: "R2: Boost Balance" },
  { key: "r3", name: "R3: Exhaust Mass Balance" },
  { key: "r4", name: "R4: AT Pressure Drop" },
  { key: "r5", name: "R5: Lambda Balance" },
  { key: "r6", name: "R6: Thermal Balance" },
];

export default function ResidualsBarChart({ reading }) {
  const residuals = RESIDUAL_LABELS.map(({ key, name }) => ({
    key,
    name,
    value: reading?.residuals?.[key] ?? 0,
  }));

  const getResidualStatus = (value) => {
    const absValue = Math.abs(value);
    if (absValue < 0.5)
      return { status: "NORMAL", color: "#22c55e", bgColor: "#dcfce7" };
    if (absValue < 1.5)
      return { status: "WATCH", color: "#f59e0b", bgColor: "#fef3c7" };
    if (absValue < 3.0)
      return { status: "WARNING", color: "#f97316", bgColor: "#ffedd5" };
    return { status: "CRITICAL", color: "#ef4444", bgColor: "#fee2e2" };
  };

  const getBarColor = (value) => {
    const absValue = Math.abs(value);
    if (absValue < 0.5) return "#22c55e";
    if (absValue < 1.5) return "#f59e0b";
    if (absValue < 3.0) return "#f97316";
    return "#ef4444";
  };

  const getBarWidth = (value) => {
    const absValue = Math.abs(value);
    return Math.min((absValue / 4.5) * 100, 100);
  };

  return (
    <div
      style={{
        width: "100%",
        backgroundColor: "#0a0a0a",
        borderRadius: "8px",
        border: "2px solid #333",
        padding: "16px",
      }}
    >
      <div style={{ marginBottom: "16px" }}>
        <h3
          style={{
            fontSize: "14px",
            fontWeight: "bold",
            color: "#000",
            backgroundColor: "#FFCC00",
            padding: "6px 12px",
            display: "inline-block",
            borderRadius: "4px",
          }}
        >
          RESIDUAL SIGNALS
        </h3>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {residuals.map((residual) => {
          const status = getResidualStatus(residual.value);
          const barColor = getBarColor(residual.value);
          const barWidth = getBarWidth(residual.value);

          return (
            <motion.div
              key={residual.key}
              style={{ display: "flex", alignItems: "center", gap: "16px" }}
              initial={{ opacity: 0.8 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
            >
              {/* Label */}
              <div
                style={{
                  width: "140px",
                  fontSize: "13px",
                  fontWeight: "500",
                  color: "#ccc",
                }}
              >
                {residual.name}
              </div>

              {/* Horizontal Bar */}
              <div
                style={{
                  flex: 1,
                  height: "28px",
                  backgroundColor: "#333",
                  borderRadius: "4px",
                  overflow: "hidden",
                  position: "relative",
                }}
              >
                <motion.div
                  style={{
                    height: "100%",
                    borderRadius: "4px",
                    backgroundColor: barColor,
                    width: `${barWidth}%`,
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${barWidth}%` }}
                  transition={{ duration: 0.5, type: "spring", stiffness: 50 }}
                />
              </div>

              {/* Value */}
              <div style={{ width: "60px", textAlign: "right" }}>
                <span
                  style={{ fontSize: "13px", fontWeight: "600", color: "#fff" }}
                >
                  {residual.value >= 0 ? "+" : ""}
                  {residual.value.toFixed(1)}σ
                </span>
              </div>

              {/* Status Badge */}
              <div
                style={{
                  padding: "4px 10px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: "600",
                  color: "#000",
                  whiteSpace: "nowrap",
                  backgroundColor: status.color,
                }}
              >
                {status.status}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Recommended Action */}
      <div
        style={{
          marginTop: "16px",
          padding: "12px",
          backgroundColor: "#222",
          border: "2px solid #FFCC00",
          borderRadius: "4px",
        }}
      >
        <h4
          style={{
            fontSize: "13px",
            fontWeight: "bold",
            color: "#FFCC00",
            marginBottom: "8px",
          }}
        >
          Recommended Action:
        </h4>
        <p style={{ fontSize: "13px", color: "#ccc", margin: 0 }}>
          {recommendedAction(reading)}
        </p>
      </div>

      {/* Status Indicators */}
      <div
        style={{
          marginTop: "12px",
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "8px",
        }}
      >
        <div
          style={{
            padding: "10px",
            backgroundColor: "#1a3a1a",
            border: "1px solid #22c55e",
            borderRadius: "4px",
            textAlign: "center",
          }}
        >
          <div
            style={{ fontSize: "13px", fontWeight: "bold", color: "#22c55e" }}
          >
            GREEN
          </div>
          <div
            style={{ fontSize: "11px", fontWeight: "600", color: "#22c55e" }}
          >
            All Status
          </div>
          <div style={{ fontSize: "10px", color: "#888" }}>
            Less than 2 sigma
          </div>
        </div>
        <div
          style={{
            padding: "10px",
            backgroundColor: "#3a3a1a",
            border: "1px solid #f59e0b",
            borderRadius: "4px",
            textAlign: "center",
          }}
        >
          <div
            style={{ fontSize: "13px", fontWeight: "bold", color: "#f59e0b" }}
          >
            WATCH
          </div>
          <div
            style={{ fontSize: "11px", fontWeight: "600", color: "#f59e0b" }}
          >
            Alert Level
          </div>
          <div style={{ fontSize: "10px", color: "#888" }}>2 to 3 sigma</div>
        </div>
        <div
          style={{
            padding: "10px",
            backgroundColor: "#3a2a1a",
            border: "1px solid #f97316",
            borderRadius: "4px",
            textAlign: "center",
          }}
        >
          <div
            style={{ fontSize: "13px", fontWeight: "bold", color: "#f97316" }}
          >
            WARNING
          </div>
          <div
            style={{ fontSize: "11px", fontWeight: "600", color: "#f97316" }}
          >
            High Level
          </div>
          <div style={{ fontSize: "10px", color: "#888" }}>
            Multiple above 3 sigma
          </div>
        </div>
        <div
          style={{
            padding: "10px",
            backgroundColor: "#3a1a1a",
            border: "1px solid #ef4444",
            borderRadius: "4px",
            textAlign: "center",
          }}
        >
          <div
            style={{ fontSize: "13px", fontWeight: "bold", color: "#ef4444" }}
          >
            CRITICAL
          </div>
          <div
            style={{ fontSize: "11px", fontWeight: "600", color: "#ef4444" }}
          >
            Urgent Action
          </div>
          <div style={{ fontSize: "10px", color: "#888" }}>
            RF confidence greater 80 percent
          </div>
        </div>
      </div>
    </div>
  );
}
