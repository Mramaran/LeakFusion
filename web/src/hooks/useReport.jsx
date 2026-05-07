import { Document, Page, Text, View, StyleSheet } from "@react-pdf/renderer";
import { pdf } from "@react-pdf/renderer";
import { labelFor } from "../data/zones";

const ACTIONS = {
  zone1:
    "Inspect intake manifold gasket and pre-compressor ducting. Check MAF placement; look for unmetered air ingress between MAF and intake manifold.",
  zone2:
    "Inspect post-compressor / intercooler joints and hose clamps. Verify intercooler core integrity; charge air may be bypassing the intercooler before the manifold.",
  zone3a:
    "Inspect exhaust manifold gaskets, studs, and pre-turbine seals. Check for carbon deposits indicating hot exhaust escape upstream of the turbine.",
  zone3b:
    "Inspect post-turbine pipe and aftertreatment inlet flange. Check ΔP sensor placement; exhaust may be escaping between turbine outlet and AT inlet.",
  zone4:
    "Inspect test-cell duct at the compressor inlet. Verify cell-side seals; unmetered air entering between MAF and compressor.",
};

const PRIORITY = {
  1: "LOW — Monitor for 24h before scheduling inspection",
  2: "LOW — Schedule inspection within 72h",
  3: "HIGH — Schedule inspection within 24h",
  4: "URGENT — Reduce engine load, inspect within 4h",
  5: "CRITICAL — Stop engine, immediate inspection required",
};

const styles = StyleSheet.create({
  page: {
    padding: 40,
    fontFamily: "Courier",
    fontSize: 10,
  },
  header: {
    marginBottom: 20,
    borderBottom: "1 solid #000",
    paddingBottom: 10,
    textAlign: "center",
    fontSize: 16,
    fontWeight: "bold",
  },
  divider: {
    marginVertical: 10,
    borderBottom: "1 solid #000",
  },
  section: {
    marginBottom: 15,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: "bold",
    marginBottom: 8,
    borderBottom: "1 solid #000",
    paddingBottom: 4,
  },
  row: {
    display: "flex",
    flexDirection: "row",
    marginBottom: 4,
    fontSize: 10,
  },
  label: {
    width: "30%",
    fontWeight: "bold",
  },
  value: {
    width: "70%",
  },
  residualRow: {
    display: "flex",
    flexDirection: "row",
    marginBottom: 6,
    fontSize: 9,
  },
  residualLabel: {
    width: "15%",
    fontWeight: "bold",
  },
  residualName: {
    width: "30%",
  },
  residualValue: {
    width: "25%",
  },
  residualStatus: {
    width: "30%",
    textAlign: "right",
  },
  footer: {
    marginTop: 30,
    fontSize: 8,
    textAlign: "center",
    borderTop: "1 solid #000",
    paddingTop: 10,
    color: "#666",
  },
});

const ReportDocument = ({ reading }) => (
  <Document>
    <Page size="A4" style={styles.page}>
      {/* Header */}
      <View style={styles.header}>
        <Text>CATERPILLAR ENGINE DIAGNOSTIC REPORT</Text>
      </View>

      {/* Report Info */}
      <View style={styles.section}>
        <View style={styles.row}>
          <Text style={styles.label}>Report ID:</Text>
          <Text style={styles.value}>CAT-RPT-{Date.now()}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Generated:</Text>
          <Text style={styles.value}>{new Date().toLocaleString()}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Engine ID:</Text>
          <Text style={styles.value}>CAT-3516B-042</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>System:</Text>
          <Text style={styles.value}>Leak Detection v1.0</Text>
        </View>
      </View>

      <View style={styles.divider} />

      {/* Alert Summary */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>ALERT SUMMARY</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Status:</Text>
          <Text style={styles.value}>
            {reading.alert_triggered ? "LEAK DETECTED" : "HEALTHY"}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Zone:</Text>
          <Text style={styles.value}>
            {reading.detected_zone ? labelFor(reading.detected_zone) : "N/A"}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Severity:</Text>
          <Text style={styles.value}>{reading.severity} / 5</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Confidence:</Text>
          <Text style={styles.value}>
            {Math.round(reading.leak_probability)}%
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>HDBSCAN:</Text>
          <Text style={styles.value}>{reading.hdbscan_status}</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Detection:</Text>
          <Text style={styles.value}>60s confirmation window elapsed</Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Engine RPM:</Text>
          <Text style={styles.value}>
            {reading.rpm}{" "}
            {reading.is_steady_state ? "(Steady State)" : "(Transient)"}
          </Text>
        </View>
      </View>

      <View style={styles.divider} />

      {/* Residual Values */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>RESIDUAL VALUES AT DETECTION</Text>
        {[
          { key: "r1", name: "Intake Mass Balance" },
          { key: "r2", name: "Boost Balance" },
          { key: "r3", name: "Exhaust Mass Balance" },
          { key: "r4", name: "AT Pressure Drop" },
          { key: "r5", name: "Lambda Balance" },
          { key: "r6", name: "Thermal Balance" },
        ].map((res) => {
          const value = reading.residuals[res.key] || 0;
          const absValue = Math.abs(value);
          let status = "[NORMAL]";
          if (absValue > 1.5) status = "[ELEVATED ⚠]";
          return (
            <View key={res.key} style={styles.residualRow}>
              <Text style={styles.residualLabel}>{res.key.toUpperCase()}</Text>
              <Text style={styles.residualName}>{res.name}</Text>
              <Text style={styles.residualValue}>
                {value >= 0 ? "+" : ""}
                {value.toFixed(2)} σ
              </Text>
              <Text style={styles.residualStatus}>{status}</Text>
            </View>
          );
        })}
      </View>

      <View style={styles.divider} />

      {/* Recommended Action */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>RECOMMENDED ACTION</Text>
        <View style={styles.row}>
          <Text style={styles.label}>Priority:</Text>
          <Text style={styles.value}>
            {PRIORITY[reading.severity] || "UNKNOWN"}
          </Text>
        </View>
        <View style={{ marginVertical: 8 }}>
          <Text style={{ fontSize: 10, marginBottom: 4 }}>Action:</Text>
          <Text style={{ fontSize: 9, lineHeight: 1.4, marginLeft: 12 }}>
            {ACTIONS[reading.detected_zone] ||
              "Contact field engineer for guidance."}
          </Text>
        </View>
        <View style={styles.row}>
          <Text style={styles.label}>Downtime est.:</Text>
          <Text style={styles.value}>
            {reading.severity >= 4 ? "Immediate" : "2–4 hours"}
          </Text>
        </View>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text>
          Generated by CAT Leak Detection System — Physics + ML Pipeline
        </Text>
        <Text style={{ marginTop: 4 }}>
          This report is confidential and for authorized Caterpillar technicians
          only.
        </Text>
      </View>
    </Page>
  </Document>
);

export const useReport = () => {
  const generateReport = async (reading) => {
    try {
      const doc = <ReportDocument reading={reading} />;
      const asPdf = pdf(doc);
      const blob = await asPdf.toBlob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      return true;
    } catch (error) {
      console.error("Error generating report:", error);
      return false;
    }
  };

  return { generateReport };
};
