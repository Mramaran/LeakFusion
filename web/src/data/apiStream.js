// Replay-based stream over a backend-computed list of Reading payloads.
// Same getNextReading() contract as MockEngineStream so Dashboard's 800ms
// tick loop is unchanged. Loops the readings list when it reaches the end.
export class ApiEngineStream {
  constructor() {
    this.readings = [];
    this.idx = 0;
    this.ready = false;
  }

  async load(sampleKey) {
    const r = await fetch(`/api/sample/${sampleKey}`);
    if (!r.ok) {
      throw new Error(`Failed to load sample ${sampleKey}: ${r.status}`);
    }
    const body = await r.json();
    this.readings = body.readings;
    this.idx = 0;
    this.ready = true;
    return body.sample_label;
  }

  async loadFromFile(file) {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch("/api/process", { method: "POST", body: fd });
    if (!r.ok) {
      let msg = "Upload failed";
      try {
        const err = await r.json();
        msg = err.detail || msg;
      } catch {
        // body wasn't JSON; keep the default message
      }
      throw new Error(msg);
    }
    const body = await r.json();
    this.readings = body.readings;
    this.idx = 0;
    this.ready = true;
    return body.sample_label;
  }

  getNextReading() {
    if (!this.ready || !this.readings.length) return null;
    const r = this.readings[this.idx % this.readings.length];
    // Re-index on the client so the displayed counter monotonically increases
    // even after the readings list loops.
    const out = { ...r, reading_index: this.idx + 1 };
    this.idx++;
    return out;
  }
}
