import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export default function ResidualChart({ history }) {
  const chartData = history.map((reading) => ({
    index: reading.reading_index,
    r1: parseFloat(reading.residuals.r1.toFixed(2)),
    r2: parseFloat(reading.residuals.r2.toFixed(2)),
    r3: parseFloat(reading.residuals.r3.toFixed(2)),
    r4: parseFloat(reading.residuals.r4.toFixed(2)),
    r5: parseFloat(reading.residuals.r5.toFixed(2)),
    r6: parseFloat(reading.residuals.r6.toFixed(2)),
    alert_triggered: reading.alert_triggered,
  }));

  // Find the alert trigger point
  const alertIndex = chartData.findIndex((d) => d.alert_triggered);

  const residualColors = {
    r1: "#60a5fa",
    r2: "#34d399",
    r3: "#f87171",
    r4: "#fb923c",
    r5: "#a78bfa",
    r6: "#facc15",
  };

  const residualNames = {
    r1: "R1: Intake Mass Balance",
    r2: "R2: Boost Balance",
    r3: "R3: Exhaust Mass Balance",
    r4: "R4: AT Pressure Drop",
    r5: "R5: Lambda Balance",
    r6: "R6: Thermal Balance",
  };

  return (
    <div className="w-full h-full bg-[#0f1117] rounded-lg border border-[#30363d] p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
          <XAxis
            dataKey="index"
            stroke="#6b7280"
            style={{ fontSize: "12px" }}
          />
          <YAxis
            domain={[-1, 4.5]}
            stroke="#6b7280"
            style={{ fontSize: "12px" }}
            label={{ value: "Sigma (σ)", angle: -90, position: "insideLeft" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1a1d27",
              border: "1px solid #30363d",
              borderRadius: "8px",
              color: "#fff",
            }}
            formatter={(value) => value?.toFixed(2)}
          />
          <Legend
            wrapperStyle={{ paddingTop: "16px" }}
            formatter={(value) => residualNames[value]}
            contentStyle={{
              color: "#fff",
              fontSize: "12px",
              backgroundColor: "#1a1d27",
              border: "1px solid #30363d",
              borderRadius: "6px",
            }}
          />

          {/* Threshold line */}
          <ReferenceLine
            y={1.5}
            stroke="#ff0000"
            strokeDasharray="5 5"
            label={{
              value: "Threshold (1.5σ)",
              position: "top",
              fill: "#f87171",
              fontSize: 12,
            }}
          />

          {/* Alert trigger line */}
          {alertIndex >= 0 && (
            <ReferenceLine
              x={chartData[alertIndex].index}
              stroke="#fb923c"
              strokeDasharray="5 5"
              label={{
                value: "Alert",
                position: "top",
                fill: "#fb923c",
                fontSize: 12,
              }}
            />
          )}

          {/* Residual lines */}
          <Line
            type="monotone"
            dataKey="r1"
            stroke={residualColors.r1}
            dot={false}
            strokeWidth={2}
            isAnimationActive={true}
          />
          <Line
            type="monotone"
            dataKey="r2"
            stroke={residualColors.r2}
            dot={false}
            strokeWidth={2}
            isAnimationActive={true}
          />
          <Line
            type="monotone"
            dataKey="r3"
            stroke={residualColors.r3}
            dot={false}
            strokeWidth={2}
            isAnimationActive={true}
          />
          <Line
            type="monotone"
            dataKey="r4"
            stroke={residualColors.r4}
            dot={false}
            strokeWidth={2}
            isAnimationActive={true}
          />
          <Line
            type="monotone"
            dataKey="r5"
            stroke={residualColors.r5}
            dot={false}
            strokeWidth={2}
            isAnimationActive={true}
          />
          <Line
            type="monotone"
            dataKey="r6"
            stroke={residualColors.r6}
            dot={false}
            strokeWidth={2}
            isAnimationActive={true}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
