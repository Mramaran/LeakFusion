import { useRef } from "react";

export default function CsvUploader({ onUpload, disabled }) {
  const inputRef = useRef(null);

  const handleChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    // Reset so re-uploading the same file fires the change event again.
    e.target.value = "";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <label
        style={{
          fontSize: "10px",
          color: "#999",
          fontWeight: "bold",
          letterSpacing: "0.5px",
        }}
      >
        UPLOAD CSV
      </label>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
        style={{
          background: "#1a1d27",
          color: "#FFCC00",
          border: "1px solid #FFCC00",
          borderRadius: "4px",
          padding: "6px 10px",
          fontSize: "12px",
          fontWeight: "600",
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      >
        Choose file…
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        onChange={handleChange}
        disabled={disabled}
        style={{ display: "none" }}
      />
    </div>
  );
}
