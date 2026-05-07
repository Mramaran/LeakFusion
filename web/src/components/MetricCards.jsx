import { motion } from "framer-motion";

export default function MetricCards({ reading }) {
  const getColor = (value, thresholds) => {
    if (value < thresholds[0]) return "#FFCC00"; // Yellow
    if (value < thresholds[1]) return "#FFB300"; // Orange-Yellow
    return "#ff6600"; // Orange-Red
  };

  const leakProbColor = getColor(reading.leak_probability, [20, 60]);
  const confidenceColor = getColor(
    Math.max(...Object.values(reading.zone_probabilities)) * 100,
    [50, 80],
  );
  const rpmColor = reading.is_steady_state ? "#FFCC00" : "#FFB300";

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Leak Probability Card */}
      <motion.div
        style={{
          backgroundColor: "#222222",
          borderRadius: "8px",
          padding: "16px",
          border: `2px solid #333333`,
          cursor: "pointer",
        }}
        whileHover={{ borderColor: "#FFCC00" }}
      >
        <div
          style={{
            fontSize: "12px",
            color: "#999",
            fontWeight: "600",
            marginBottom: "12px",
          }}
        >
          LEAK PROBABILITY
        </div>
        <motion.div
          style={{
            fontSize: "32px",
            fontWeight: "bold",
            color: leakProbColor,
          }}
          key={reading.leak_probability}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {reading.leak_probability}%
        </motion.div>
      </motion.div>

      {/* RF Confidence Card */}
      <motion.div
        style={{
          backgroundColor: "#222222",
          borderRadius: "8px",
          padding: "16px",
          border: `2px solid #333333`,
          cursor: "pointer",
        }}
        whileHover={{ borderColor: "#FFCC00" }}
      >
        <div
          style={{
            fontSize: "12px",
            color: "#999",
            fontWeight: "600",
            marginBottom: "12px",
          }}
        >
          RF CONFIDENCE
        </div>
        <motion.div
          style={{
            fontSize: "32px",
            fontWeight: "bold",
            color: confidenceColor,
          }}
          key={Math.max(...Object.values(reading.zone_probabilities))}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {Math.round(
            Math.max(...Object.values(reading.zone_probabilities)) * 100,
          )}
          %
        </motion.div>
      </motion.div>

      {/* Engine RPM Card */}
      <motion.div
        style={{
          backgroundColor: "#222222",
          borderRadius: "8px",
          padding: "16px",
          border: `2px solid #333333`,
          cursor: "pointer",
        }}
        whileHover={{ borderColor: "#FFCC00" }}
      >
        <div
          style={{
            fontSize: "12px",
            color: "#999",
            fontWeight: "600",
            marginBottom: "12px",
          }}
        >
          ENGINE RPM
        </div>
        <motion.div
          style={{
            fontSize: "32px",
            fontWeight: "bold",
            color: rpmColor,
            marginBottom: "8px",
          }}
          key={reading.rpm}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {reading.rpm.toLocaleString()}
        </motion.div>
        <div style={{ fontSize: "12px", fontWeight: "500", color: rpmColor }}>
          {reading.is_steady_state ? "Steady" : "Transient"}
        </div>
      </motion.div>

      {/* Alert Status Card */}
      <motion.div
        className={`rounded-xl p-6 border-2 ${
          reading.alert_triggered
            ? "bg-red-900/20 border-red-500"
            : "bg-blue-900/20 border-blue-500 bg-[#1a1d27]"
        }`}
        animate={reading.alert_triggered ? { borderColor: "#ef4444" } : {}}
        transition={
          reading.alert_triggered
            ? { duration: 1, repeat: Infinity, repeatType: "reverse" }
            : {}
        }
      >
        <div className="text-xs text-gray-400 font-semibold mb-3">
          ALERT STATUS
        </div>
        <motion.div
          className={`text-2xl font-bold ${
            reading.alert_triggered ? "text-red-400" : "text-blue-400"
          }`}
          key={reading.alert_triggered}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {reading.alert_triggered ? "LEAK DETECTED" : "Monitoring"}
        </motion.div>
      </motion.div>
    </div>
  );
}
