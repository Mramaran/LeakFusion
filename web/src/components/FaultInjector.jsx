import { useState } from "react";
import { motion } from "framer-motion";
import { Zap, RotateCcw } from "lucide-react";
import { ZONES, labelFor } from "../data/zones";

export default function FaultInjector({ onInject, onReset, isLeakActive }) {
  const [selectedZone, setSelectedZone] = useState(null);
  const [severity, setSeverity] = useState(3);
  const [isShaking, setIsShaking] = useState(false);

  const handleInject = () => {
    if (selectedZone) {
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 500);
      onInject(selectedZone, severity);
    }
  };

  const getSliderColor = () => {
    if (severity <= 2) return "from-green-500 to-green-600";
    if (severity === 3) return "from-amber-500 to-amber-600";
    return "from-red-500 to-red-600";
  };

  return (
    <div
      style={{
        background: "#0a0a0a",
        border: "1px solid #374151",
        borderRadius: "12px",
        padding: "16px",
        marginBottom: "16px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <h3
          style={{
            color: "#ffffff",
            fontSize: "14px",
            fontWeight: "bold",
            margin: 0,
          }}
        >
          FAULT INJECTION SIMULATOR
        </h3>
        {isLeakActive && (
          <motion.button
            initial={{ x: 10, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            onClick={onReset}
            style={{
              background: "transparent",
              border: "1px solid #ef4444",
              color: "#ef4444",
              padding: "8px 12px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: "bold",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "all 0.2s ease",
            }}
            onHoverStart={(e) => {
              e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)";
            }}
            onHoverEnd={(e) => {
              e.currentTarget.style.background = "transparent";
            }}
          >
            <RotateCcw size={14} />
            RESET ENGINE
          </motion.button>
        )}
      </div>

      {/* Zone selector */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            fontSize: "12px",
            color: "#9ca3af",
            fontWeight: "bold",
            marginBottom: "8px",
          }}
        >
          SELECT ZONE:
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
          }}
        >
          {ZONES.map((zone) => (
            <motion.button
              key={zone.key}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedZone(zone.key)}
              style={{
                background:
                  selectedZone === zone.key
                    ? "rgba(239, 68, 68, 0.2)"
                    : "#1a1d27",
                border:
                  selectedZone === zone.key
                    ? "2px solid #ef4444"
                    : "1px solid #374151",
                color: selectedZone === zone.key ? "#ff6b6b" : "#d1d5db",
                padding: "10px",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: "bold",
                transition: "all 0.2s ease",
              }}
            >
              {zone.label}
            </motion.button>
          ))}
        </div>
      </div>

      {/* Severity slider */}
      <div style={{ marginBottom: "16px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "8px",
          }}
        >
          <div
            style={{ fontSize: "12px", color: "#9ca3af", fontWeight: "bold" }}
          >
            SEVERITY:
          </div>
          <div
            style={{
              fontSize: "20px",
              fontWeight: "bold",
              color:
                severity <= 2
                  ? "#22c55e"
                  : severity === 3
                    ? "#f59e0b"
                    : "#ef4444",
            }}
          >
            {severity} / 5
          </div>
        </div>
        <div
          style={{
            position: "relative",
            height: "6px",
            background: "#1a1d27",
            borderRadius: "3px",
            overflow: "hidden",
          }}
        >
          <motion.div
            animate={{
              width: `${(severity / 5) * 100}%`,
              background:
                severity <= 2
                  ? "#22c55e"
                  : severity === 3
                    ? "#f59e0b"
                    : "#ef4444",
            }}
            style={{
              height: "100%",
              borderRadius: "3px",
            }}
          />
        </div>
        <input
          type="range"
          min="1"
          max="5"
          step="1"
          value={severity}
          onChange={(e) => setSeverity(parseInt(e.target.value))}
          style={{
            width: "100%",
            height: "6px",
            marginTop: "-32px",
            cursor: "pointer",
            opacity: 0,
            position: "absolute",
          }}
        />
      </div>

      {/* Inject button */}
      <motion.button
        animate={isShaking ? { x: [-4, 4, -4, 4, 0] } : {}}
        transition={{ duration: 0.4 }}
        onClick={handleInject}
        disabled={!selectedZone}
        style={{
          width: "100%",
          background: selectedZone ? "#f59e0b" : "#6b7280",
          color: "#000000",
          padding: "12px",
          borderRadius: "6px",
          border: "none",
          cursor: selectedZone ? "pointer" : "not-allowed",
          fontSize: "14px",
          fontWeight: "bold",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          transition: "all 0.2s ease",
          marginBottom: "16px",
          opacity: selectedZone ? 1 : 0.5,
        }}
      >
        <Zap size={16} />
        INJECT LEAK
      </motion.button>

      {/* Status bar */}
      <motion.div
        layout
        style={{
          padding: "12px",
          borderRadius: "6px",
          fontSize: "12px",
          textAlign: "center",
          background: isLeakActive ? "#1c1400" : "#1a1d27",
          border: `1px solid ${isLeakActive ? "#ef9f27" : "#374151"}`,
          color: isLeakActive ? "#f59e0b" : "#9ca3af",
        }}
      >
        {isLeakActive ? (
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            <span style={{ color: "#ef4444", fontSize: "16px" }}>●</span>
            <span>
              Leak active — {selectedZone ? labelFor(selectedZone) : "unknown zone"}, Severity{" "}
              {severity}/5
            </span>
          </motion.div>
        ) : (
          "No fault injected — engine healthy"
        )}
      </motion.div>
    </div>
  );
}
