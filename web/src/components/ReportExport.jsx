import { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Check, Loader } from "lucide-react";
import { useReport } from "../hooks/useReport";

export default function ReportExport({ reading, disabled }) {
  const [status, setStatus] = useState("idle"); // idle, loading, success
  const { generateReport } = useReport();

  const handleExport = async () => {
    setStatus("loading");
    const success = await generateReport(reading);
    if (success) {
      setStatus("success");
      setTimeout(() => setStatus("idle"), 2000);
    } else {
      setStatus("idle");
    }
  };

  return (
    <motion.button
      whileHover={!disabled ? { scale: 1.02 } : {}}
      whileTap={!disabled ? { scale: 0.98 } : {}}
      onClick={handleExport}
      disabled={disabled}
      style={{
        background:
          status === "success"
            ? "#22c55e"
            : status === "loading"
              ? "#f59e0b"
              : disabled
                ? "#6b7280"
                : "#3b82f6",
        color:
          status === "success" ? "#ffffff" : disabled ? "#9ca3af" : "#ffffff",
        padding: "8px 14px",
        borderRadius: "6px",
        border: "none",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: "12px",
        fontWeight: "bold",
        display: "flex",
        alignItems: "center",
        gap: "6px",
        transition: "all 0.2s ease",
        opacity: disabled ? 0.5 : 1,
      }}
    >
      {status === "loading" && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity }}
        >
          <Loader size={14} />
        </motion.div>
      )}
      {status === "success" && <Check size={14} />}
      {status === "idle" && <FileText size={14} />}

      <span>
        {status === "loading"
          ? "Generating..."
          : status === "success"
            ? "✓ Report Ready"
            : "📄 Export Report"}
      </span>
    </motion.button>
  );
}
