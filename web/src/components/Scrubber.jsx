import { Play, Pause, SkipBack, SkipForward, Rewind } from "lucide-react";

export default function Scrubber({
  frameIdx,
  totalFrames,
  playing,
  onSeek,
  onPlayPause,
  onStep,
  onReset,
}) {
  const disabled = totalFrames === 0;
  const max = Math.max(0, totalFrames - 1);

  const btnStyle = {
    background: "#1a1d27",
    color: "#FFCC00",
    border: "1px solid #FFCC00",
    borderRadius: "4px",
    padding: "6px 10px",
    cursor: disabled ? "not-allowed" : "pointer",
    fontSize: "12px",
    fontWeight: "600",
    display: "flex",
    alignItems: "center",
    gap: "4px",
    opacity: disabled ? 0.4 : 1,
  };

  return (
    <div
      style={{
        background: "#0a0a0a",
        border: "1px solid #333",
        borderRadius: "8px",
        padding: "10px 14px",
        display: "flex",
        alignItems: "center",
        gap: "12px",
      }}
    >
      <span
        style={{
          fontSize: "11px",
          color: "#999",
          fontWeight: "bold",
          letterSpacing: "0.5px",
          minWidth: "60px",
        }}
      >
        FRAME
      </span>

      <button
        type="button"
        onClick={onReset}
        disabled={disabled}
        style={btnStyle}
        title="Jump to first frame"
      >
        <Rewind size={12} />
      </button>

      <button
        type="button"
        onClick={() => onStep(-1)}
        disabled={disabled}
        style={btnStyle}
        title="Previous frame"
      >
        <SkipBack size={12} />
      </button>

      <button
        type="button"
        onClick={onPlayPause}
        disabled={disabled}
        style={{ ...btnStyle, background: playing ? "#FFCC00" : "#1a1d27", color: playing ? "#000" : "#FFCC00" }}
        title={playing ? "Pause auto-advance" : "Play (800 ms tick)"}
      >
        {playing ? <Pause size={12} /> : <Play size={12} />}
        {playing ? "Pause" : "Play"}
      </button>

      <button
        type="button"
        onClick={() => onStep(1)}
        disabled={disabled}
        style={btnStyle}
        title="Next frame"
      >
        <SkipForward size={12} />
      </button>

      <input
        type="range"
        min={0}
        max={max}
        step={1}
        value={frameIdx}
        onChange={(e) => onSeek(parseInt(e.target.value, 10))}
        disabled={disabled}
        style={{
          flex: 1,
          accentColor: "#FFCC00",
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      />

      <span
        style={{
          fontSize: "12px",
          color: "#FFCC00",
          fontFamily: "monospace",
          minWidth: "90px",
          textAlign: "right",
        }}
      >
        {disabled ? "—" : `${frameIdx + 1} / ${totalFrames}`}
      </span>
    </div>
  );
}
