import { ZONE_KEYS } from "./zones";

const _uniformZoneProbs = () => {
  const zp = {};
  for (const k of ZONE_KEYS) zp[k] = 1 / ZONE_KEYS.length; // 0.2 each
  return zp;
};

export class MockEngineStream {
  constructor() {
    this.readingIndex = 0;
  }

  getNextReading() {
    this.readingIndex++;

    // Loop back after cycle completes
    if (this.readingIndex > 101) {
      this.readingIndex = 1;
    }

    const timestamp = new Date().toISOString();

    // Base RPM with small noise
    const rpmNoise = (Math.random() - 0.5) * 20;
    const rpm = 1800 + rpmNoise;

    const loadPercent = 65 + (Math.random() - 0.5) * 10;

    // Steady state for most readings
    let isReadySteadyState = true;

    let residuals = {
      r1: (Math.random() - 0.5) * 0.3,
      r2: (Math.random() - 0.5) * 0.3,
      r3: (Math.random() - 0.5) * 0.3,
      r4: (Math.random() - 0.5) * 0.3,
      r5: (Math.random() - 0.5) * 0.3,
      r6: (Math.random() - 0.5) * 0.3,
    };

    let zoneProbs = _uniformZoneProbs();

    let detectedZone = null;
    let severity = 0;
    let cusumScore = 0;
    let hdbscanStatus = "Known Pattern";
    let alertTriggered = false;
    let leakProbability = 0;

    if (this.readingIndex <= 40) {
      // Healthy phase
      residuals = {
        r1: (Math.random() - 0.5) * 0.3,
        r2: (Math.random() - 0.5) * 0.3,
        r3: (Math.random() - 0.5) * 0.3,
        r4: (Math.random() - 0.5) * 0.3,
        r5: (Math.random() - 0.5) * 0.3,
        r6: (Math.random() - 0.5) * 0.3,
      };
      severity = 0;
      detectedZone = null;
      alertTriggered = false;
      leakProbability = 0;
      cusumScore = 0;
    } else if (this.readingIndex >= 41 && this.readingIndex <= 59) {
      // Leak developing phase — zone3b (post-turbine, AT inlet) signature: R3 + R4
      const progress = (this.readingIndex - 40) / 20; // 0 to 1

      residuals = {
        r1: (Math.random() - 0.5) * 0.3,
        r2: (Math.random() - 0.5) * 0.3,
        r3: 0.25 * progress + (Math.random() - 0.5) * 0.2,
        r4: 0.25 * progress + (Math.random() - 0.5) * 0.2,
        r5: (Math.random() - 0.5) * 0.3,
        r6: (Math.random() - 0.5) * 0.3,
      };

      cusumScore = 15 * progress;
      detectedZone = "zone3b";
      severity = Math.floor(1.5 * progress);
      leakProbability = 20 + 50 * progress;
      alertTriggered = false;

      zoneProbs = {
        zone1:  0.04,
        zone2:  0.04,
        zone3a: 0.02 + 0.12 * progress,
        zone3b: 0.6 + 0.28 * progress,
        zone4:  0.04,
      };
    } else if (this.readingIndex >= 60 && this.readingIndex <= 100) {
      // Leak confirmed phase — with unknown pattern scenario at 75-85
      const progress = Math.min(1, (this.readingIndex - 60) / 40);

      // Unknown pattern scenario at reading 75-85
      if (this.readingIndex >= 75 && this.readingIndex <= 85) {
        residuals = {
          r1: 0.6 + (Math.random() - 0.5) * 0.2,
          r2: 0.55 + (Math.random() - 0.5) * 0.2,
          r3: 0.58 + (Math.random() - 0.5) * 0.2,
          r4: 0.62 + (Math.random() - 0.5) * 0.2,
          r5: 0.59 + (Math.random() - 0.5) * 0.2,
          r6: 0.61 + (Math.random() - 0.5) * 0.2,
        };

        cusumScore = 4.7;
        detectedZone = null;
        severity = 0;
        leakProbability = 35;
        alertTriggered = true;
        hdbscanStatus = "Unknown — flag for review";

        // Roughly even — five-keys-equal-weight (~0.2 each)
        zoneProbs = {
          zone1:  0.21,
          zone2:  0.20,
          zone3a: 0.20,
          zone3b: 0.20,
          zone4:  0.19,
        };
      } else {
        // Normal confirmed leak phase — zone3b
        residuals = {
          r1: (Math.random() - 0.5) * 0.2,
          r2: (Math.random() - 0.5) * 0.2,
          r3: 2.5 + 1 * progress + (Math.random() - 0.5) * 0.3,
          r4: 2.0 + 0.8 * progress + (Math.random() - 0.5) * 0.3,
          r5: (Math.random() - 0.5) * 0.2,
          r6: (Math.random() - 0.5) * 0.2,
        };

        cusumScore = 15 + 25 * progress;
        detectedZone = "zone3b";
        severity = Math.min(5, 3 + Math.floor(1.5 * progress));
        leakProbability = 85 + 10 * progress;
        alertTriggered = true;
        hdbscanStatus = "Known Pattern";

        zoneProbs = {
          zone1:  0.02,
          zone2:  0.02,
          zone3a: 0.06,
          zone3b: 0.88,
          zone4:  0.02,
        };
      }
    }

    return {
      timestamp,
      reading_index: this.readingIndex,
      rpm: Math.round(rpm),
      load_percent: Math.round(loadPercent * 10) / 10,
      is_steady_state: isReadySteadyState,
      residuals,
      zone_probabilities: zoneProbs,
      detected_zone: detectedZone,
      severity,
      cusum_score: Math.round(cusumScore * 100) / 100,
      hdbscan_status: hdbscanStatus,
      alert_triggered: alertTriggered,
      leak_probability: Math.round(leakProbability),
    };
  }
}
