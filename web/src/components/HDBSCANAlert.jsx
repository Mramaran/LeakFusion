import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, XCircle, BookMarked, Phone } from "lucide-react";

export default function HDBSCANAlert({ reading }) {
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  const isUnknown = reading?.hdbscan_status === "Unknown — flag for review";

  if (!isUnknown) return null;

  const handleFlagRetraining = () => {
    setToastMessage("Event logged for retraining pipeline ✓");
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const handleEscalate = () => {
    setShowEscalateModal(true);
    setTimeout(() => setShowEscalateModal(false), 4000);
  };

  return (
    <>
      <motion.div
        initial={{ y: -200, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -200, opacity: 0 }}
        transition={{ duration: 0.4, type: "spring", stiffness: 100 }}
        style={{
          background: "#1c1400",
          border: "1px solid #EF9F27",
          borderRadius: "12px",
          padding: "20px",
          marginBottom: "16px",
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.4)",
        }}
      >
        {/* Blinking dot */}
        <motion.div
          animate={{ opacity: [1, 0.5, 1] }}
          transition={{ duration: 1, repeat: Infinity }}
          style={{
            position: "absolute",
            top: "20px",
            left: "20px",
            width: "12px",
            height: "12px",
            background: "#EF9F27",
            borderRadius: "50%",
          }}
        />

        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "12px",
            marginBottom: "16px",
          }}
        >
          <AlertTriangle
            size={24}
            color="#EF9F27"
            style={{ marginTop: "2px" }}
          />
          <div>
            <h3
              style={{
                margin: 0,
                color: "#EF9F27",
                fontSize: "16px",
                fontWeight: "bold",
                marginBottom: "8px",
              }}
            >
              UNKNOWN FAILURE PATTERN DETECTED
            </h3>
            <p
              style={{
                margin: 0,
                color: "#d1d5db",
                fontSize: "12px",
                lineHeight: "1.4",
              }}
            >
              HDBSCAN novelty detection has flagged this residual fingerprint as
              outside all known failure classes.
            </p>
          </div>
        </div>

        {/* Stat Cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "12px",
            marginBottom: "16px",
          }}
        >
          <div
            style={{
              background: "#0f1117",
              border: "1px solid #374151",
              borderRadius: "8px",
              padding: "12px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                color: "#6b7280",
                marginBottom: "4px",
              }}
            >
              Classifier
            </div>
            <div
              style={{ fontSize: "14px", fontWeight: "bold", color: "#ef4444" }}
            >
              WITHHELD
            </div>
          </div>
          <div
            style={{
              background: "#0f1117",
              border: "1px solid #374151",
              borderRadius: "8px",
              padding: "12px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                color: "#6b7280",
                marginBottom: "4px",
              }}
            >
              Confidence
            </div>
            <div
              style={{ fontSize: "14px", fontWeight: "bold", color: "#f59e0b" }}
            >
              {"< 40%"}
            </div>
          </div>
          <div
            style={{
              background: "#0f1117",
              border: "1px solid #374151",
              borderRadius: "8px",
              padding: "12px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "10px",
                color: "#6b7280",
                marginBottom: "4px",
              }}
            >
              Action
            </div>
            <motion.div
              animate={{ opacity: [1, 0.6, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={{ fontSize: "14px", fontWeight: "bold", color: "#ef4444" }}
            >
              ESCALATE
            </motion.div>
          </div>
        </div>

        {/* Failed Patterns */}
        <div
          style={{
            background: "rgba(0, 0, 0, 0.3)",
            borderRadius: "8px",
            padding: "12px",
            marginBottom: "16px",
            fontSize: "12px",
          }}
        >
          <div
            style={{
              color: "#d1d5db",
              marginBottom: "8px",
              fontWeight: "bold",
            }}
          >
            Residual fingerprint does not match:
          </div>
          {[
            "Zone 1 (intake) leak pattern",
            "Zone 2 (intercooler) leak pattern",
            "Zone 3a (exhaust manifold) leak pattern",
            "Zone 3b (aftertreatment inlet) leak pattern",
            "Zone 4 (test-cell duct) leak pattern",
          ].map((pattern) => (
            <div
              key={pattern}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                color: "#ef4444",
                marginBottom: "6px",
                fontSize: "11px",
              }}
            >
              <XCircle size={14} />
              <span>{pattern}</span>
            </div>
          ))}
        </div>

        {/* Instructions */}
        <div
          style={{
            background: "rgba(0, 0, 0, 0.2)",
            borderRadius: "8px",
            padding: "12px",
            marginBottom: "16px",
            fontSize: "12px",
            color: "#d1d5db",
            lineHeight: "1.5",
          }}
        >
          → Escalate to senior engineer for manual inspection
          <br />→ Log this event for model retraining pipeline
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", gap: "12px" }}>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleFlagRetraining}
            style={{
              flex: 1,
              background: "#1a1d27",
              border: "1px solid #f59e0b",
              color: "#f59e0b",
              padding: "10px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: "bold",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              transition: "all 0.2s ease",
            }}
          >
            <BookMarked size={14} />
            Flag for Retraining
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleEscalate}
            style={{
              flex: 1,
              background: "#ef4444",
              border: "none",
              color: "#ffffff",
              padding: "10px",
              borderRadius: "6px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: "bold",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              transition: "all 0.2s ease",
            }}
          >
            <Phone size={14} />
            Escalate Now
          </motion.button>
        </div>
      </motion.div>

      {/* Toast */}
      <AnimatePresence>
        {showToast && (
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            style={{
              position: "fixed",
              bottom: "20px",
              left: "50%",
              transform: "translateX(-50%)",
              background: "#22c55e",
              color: "#ffffff",
              padding: "12px 20px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: "bold",
              zIndex: 2000,
              boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
            }}
          >
            {toastMessage}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Escalate Modal */}
      <AnimatePresence>
        {showEscalateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0, 0, 0, 0.7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 2000,
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              style={{
                background: "#0f1117",
                border: "1px solid #374151",
                borderRadius: "12px",
                padding: "24px",
                maxWidth: "400px",
                textAlign: "center",
              }}
            >
              <Phone
                size={32}
                style={{ color: "#ef4444", margin: "0 auto 12px" }}
              />
              <h3
                style={{
                  margin: "0 0 12px 0",
                  color: "#ffffff",
                  fontSize: "16px",
                  fontWeight: "bold",
                }}
              >
                Escalation Alert
              </h3>
              <p
                style={{
                  margin: "0 0 16px 0",
                  color: "#d1d5db",
                  fontSize: "12px",
                  lineHeight: "1.5",
                }}
              >
                In production: this would page the on-call senior engineer via
                PagerDuty with critical alert priority.
              </p>
              <div
                style={{
                  background: "#1a1d27",
                  border: "1px solid #374151",
                  borderRadius: "6px",
                  padding: "12px",
                  marginBottom: "16px",
                  fontSize: "11px",
                  color: "#9ca3af",
                }}
              >
                PagerDuty Service: Caterpillar-LeakDetection-Critical
              </div>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowEscalateModal(false)}
                style={{
                  background: "#22c55e",
                  color: "#ffffff",
                  border: "none",
                  padding: "10px 20px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "12px",
                  fontWeight: "bold",
                  width: "100%",
                }}
              >
                Understood
              </motion.button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
