import { motion } from "framer-motion";
import { ZONES } from "../data/zones";

export default function ZoneSeverity({ reading }) {
  const getColor = (probability) => {
    if (probability < 0.2) return { bg: "#22c55e", dot: "#22c55e" };
    if (probability < 0.5) return { bg: "#f59e0b", dot: "#f59e0b" };
    return { bg: "#ef4444", dot: "#ef4444" };
  };

  const probValues = Object.values(reading.zone_probabilities);
  const maxProb = probValues.length > 0 ? Math.max(...probValues) : 0;

  return (
    <div className="space-y-4">
      {ZONES.map((zone) => {
        const probability = reading.zone_probabilities[zone.key] ?? 0;
        const percentage = Math.round(probability * 100);
        const colors = getColor(probability);
        const isMax = probability === maxProb && maxProb > 0;

        return (
          <motion.div
            key={zone.key}
            className={`rounded-lg p-3 ${
              isMax ? "bg-[#1a1d27]/50 ring-1 ring-[#30363d]" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              {/* Dot Indicator */}
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: colors.dot }}
              />

              {/* Zone Name */}
              <div className="w-44 text-sm font-medium text-white">
                {zone.label}
              </div>

              {/* Progress Bar */}
              <div className="flex-1 h-2 bg-[#1a1d27] rounded-full overflow-hidden">
                <motion.div
                  className="h-full"
                  style={{ backgroundColor: colors.bg }}
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{ duration: 0.5, type: "spring", stiffness: 50 }}
                />
              </div>

              {/* Percentage Label */}
              <div className="w-12 text-right text-sm font-semibold text-gray-300">
                {percentage}%
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
