import { useRef, useState, useEffect, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, Stars } from "@react-three/drei";
import { AnimatePresence, motion } from "framer-motion";
import * as THREE from "three";
import { X, AlertTriangle, CheckCircle } from "lucide-react";

// ============================================================================
// ENGINE PARTS CONFIGURATION
// ============================================================================

const ENGINE_PARTS = [
  {
    id: "engine_block",
    name: "Engine Block",
    geometry: "box",
    args: [3.5, 1.2, 1.8],
    position: [0, 0, 0],
    rotation: [0, 0, 0],
    baseColor: "#374151",
    zone: null,
    zoneKey: null,
    residualKeys: [],
    description: "Main engine structure",
  },
  {
    id: "compressor",
    name: "Compressor Inlet",
    geometry: "cylinder",
    args: [0.45, 0.45, 1.1, 16],
    position: [-2.4, 0.1, 0],
    rotation: [0, 0, Math.PI / 2],
    baseColor: "#1d4ed8",
    zone: "zone4",
    zoneKey: "zone4",
    residualKeys: ["r1", "r5"],
    description: "Test-cell duct at compressor inlet — unmetered air entering between MAF and compressor.",
  },
  {
    id: "turbocharger",
    name: "Turbocharger",
    geometry: "sphere",
    args: [0.5, 16, 16],
    position: [-1.0, 1.2, 0],
    rotation: [0, 0, 0],
    baseColor: "#7c3aed",
    zone: null,
    zoneKey: null,
    residualKeys: [],
    description: "Forces compressed air into the engine using exhaust gases. Reference part — not a leak zone.",
  },
  {
    id: "at_cooler",
    name: "Aftertreatment Inlet",
    geometry: "box",
    args: [1.1, 0.9, 1.4],
    position: [2.5, 0.15, 0],
    rotation: [0, 0, 0],
    baseColor: "#065f46",
    zone: "zone3b",
    zoneKey: "zone3b",
    residualKeys: ["r3", "r4"],
    description:
      "Aftertreatment inlet — exhaust escape between turbine outlet and AT inlet flange.",
  },
  {
    id: "exhaust_manifold",
    name: "Exhaust Manifold",
    geometry: "cylinder",
    args: [0.3, 0.3, 2.8, 12],
    position: [0.6, -1.0, 0],
    rotation: [0, 0, Math.PI / 2],
    baseColor: "#92400e",
    zone: "zone3a",
    zoneKey: "zone3a",
    residualKeys: ["r3", "r6"],
    description: "Exhaust manifold gasket / pre-turbine — hot exhaust escape upstream of the turbine.",
  },
  {
    id: "intercooler",
    name: "Intercooler",
    geometry: "box",
    args: [0.8, 0.5, 1.6],
    position: [-1.0, -0.9, 0],
    rotation: [0, 0, 0],
    baseColor: "#1e3a5f",
    zone: "zone2",
    zoneKey: "zone2",
    residualKeys: ["r1", "r2", "r6"],
    description: "Post-compressor / intercooler joints — charge air bypassing the intercooler before reaching the manifold.",
  },
  {
    id: "intake_manifold",
    name: "Intake Manifold",
    geometry: "box",
    args: [2.2, 0.35, 0.5],
    position: [0, 0.85, -0.7],
    rotation: [0, 0, 0],
    baseColor: "#374151",
    zone: "zone1",
    zoneKey: "zone1",
    residualKeys: ["r1", "r2", "r5"],
    description: "Intake manifold gasket — air leaving the intake or unmetered air entering pre-compressor.",
  },
];

// ============================================================================
// COLOR LOGIC
// ============================================================================

function getZoneColor(zoneKey, zoneProbabilities, detectedZone, zoneConfig) {
  if (!zoneKey) return zoneConfig.baseColor;

  const zoneName = zoneConfig.zone;
  const prob = zoneProbabilities[zoneKey] || 0;
  const isDetected = detectedZone === zoneName;

  if (isDetected) return "#ef4444"; // bright red — confirmed leak
  if (prob > 0.5) return "#f59e0b"; // amber — high suspicion
  if (prob > 0.2) return "#84cc16"; // yellow-green — watch
  return zoneConfig.baseColor; // default color — healthy
}

// ============================================================================
// RESIDUAL NAME MAPPING
// ============================================================================

const RESIDUAL_NAMES = {
  r1: "Intake Mass Balance",
  r2: "Boost Balance",
  r3: "Exhaust Mass Balance",
  r4: "AT Pressure Drop",
  r5: "Lambda Balance",
  r6: "Thermal Balance",
};

// ============================================================================
// ZONE CAMERA POSITIONS (backend keys)
// ============================================================================

const ZONE_CAMERA_POSITIONS = {
  zone1:  [0, 4, 4],     // intake_manifold
  zone2:  [-3, -1, 4],   // intercooler
  zone3a: [2, -2, 5],    // exhaust_manifold
  zone3b: [5, 2, 4],     // at_cooler
  zone4:  [-5, 2, 4],    // compressor
};

// ============================================================================
// SUB-COMPONENT: SINGLE ENGINE PART
// ============================================================================

function EnginePart({ config, reading, isLeaking, onClick }) {
  const meshRef = useRef();
  const colorTarget = getZoneColor(
    config.zoneKey,
    reading.zone_probabilities,
    reading.detected_zone,
    config,
  );

  useFrame(({ clock }) => {
    if (!meshRef.current) return;

    // Pulsing scale when leaking
    if (isLeaking) {
      const scale = 1 + 0.15 * Math.sin(clock.elapsedTime * 3);
      meshRef.current.scale.setScalar(scale);
    } else {
      meshRef.current.scale.setScalar(1);
    }

    // Continuous slow rotation
    meshRef.current.rotation.y += 0.001;
  });

  let geometryArgs = [];
  let GeometryType;

  if (config.geometry === "box") {
    GeometryType = "boxGeometry";
    geometryArgs = config.args;
  } else if (config.geometry === "cylinder") {
    GeometryType = "cylinderGeometry";
    geometryArgs = config.args;
  } else if (config.geometry === "sphere") {
    GeometryType = "sphereGeometry";
    geometryArgs = config.args;
  }

  return (
    <mesh
      ref={meshRef}
      position={config.position}
      rotation={config.rotation}
      onClick={onClick}
      castShadow
      receiveShadow
    >
      {GeometryType === "boxGeometry" && <boxGeometry args={geometryArgs} />}
      {GeometryType === "cylinderGeometry" && (
        <cylinderGeometry args={geometryArgs} />
      )}
      {GeometryType === "sphereGeometry" && (
        <sphereGeometry args={geometryArgs} />
      )}

      <meshStandardMaterial
        color={colorTarget}
        metalness={0.3}
        roughness={0.6}
        emissive={isLeaking ? "#ef4444" : "#000000"}
        emissiveIntensity={isLeaking ? 0.4 : 0}
      />

      {/* Floating HTML Label */}
      <Html position={[0, config.geometry === "cylinder" ? 1.5 : 1.0, 0]}>
        {isLeaking ? (
          <div
            style={{
              background: "rgba(15, 17, 23, 0.95)",
              border: "2px solid #ef4444",
              borderRadius: "8px",
              padding: "8px 12px",
              fontSize: "12px",
              color: "#ffffff",
              fontWeight: "bold",
              whiteSpace: "nowrap",
              boxShadow: "0 4px 12px rgba(239, 68, 68, 0.3)",
            }}
          >
            <div style={{ color: "#ef4444", fontSize: "14px" }}>
              ⚠ {config.name}
            </div>
            <div
              style={{ fontSize: "11px", color: "#f59e0b", marginTop: "4px" }}
            >
              Severity: {reading.severity}/5
            </div>
            <div
              style={{ fontSize: "11px", color: "#ef4444", marginTop: "2px" }}
            >
              Prob: {Math.round(reading.leak_probability)}%
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "rgba(15, 17, 23, 0.8)",
              border: "1px solid #374151",
              borderRadius: "6px",
              padding: "4px 8px",
              fontSize: "10px",
              color: "#9ca3af",
              whiteSpace: "nowrap",
            }}
          >
            ● {config.name}
          </div>
        )}
      </Html>
    </mesh>
  );
}

// ============================================================================
// SUB-COMPONENT: LEAK PARTICLES (SMOKE EFFECT)
// ============================================================================

function LeakParticles({ position, alertTriggered }) {
  const particleRefs = useRef([]);

  // Initialize particles once
  useEffect(() => {
    particleRefs.current = Array.from({ length: 20 }, () => ({
      y: 0,
      baseY: position[1],
      vx: (Math.random() - 0.5) * 0.02,
      vz: (Math.random() - 0.5) * 0.02,
      scale: 0.05 + Math.random() * 0.07,
      offsetX: (Math.random() - 0.5) * 0.3,
      offsetZ: (Math.random() - 0.5) * 0.3,
    }));
  }, [position]);

  useFrame(() => {
    if (!alertTriggered) return;

    particleRefs.current.forEach((particle) => {
      particle.y += 0.01;
      if (particle.y > 2.0) {
        particle.y = 0;
      }
    });
  });

  if (!alertTriggered) return null;

  return (
    <>
      {particleRefs.current.map((particle, idx) => (
        <mesh
          key={idx}
          position={[
            position[0] + particle.offsetX,
            position[1] + particle.y,
            position[2] + particle.offsetZ,
          ]}
        >
          <sphereGeometry args={[particle.scale, 8, 8]} />
          <meshBasicMaterial color="#94a3b8" transparent opacity={0.4} />
        </mesh>
      ))}
    </>
  );
}

// ============================================================================
// SUB-COMPONENT: CAMERA CONTROLLER FOR AUTO-FOCUS
// ============================================================================

function CameraController({ alertTriggered, detectedZone }) {
  const { camera } = useThree();
  const targetPositionRef = useRef(null);

  useEffect(() => {
    if (alertTriggered && detectedZone && ZONE_CAMERA_POSITIONS[detectedZone]) {
      targetPositionRef.current = ZONE_CAMERA_POSITIONS[detectedZone];
    }
  }, [alertTriggered, detectedZone]);

  useFrame(() => {
    if (!targetPositionRef.current) return;

    const target = new THREE.Vector3(...targetPositionRef.current);
    camera.position.lerp(target, 0.02);
    camera.lookAt(0, 0, 0);
  });

  return null;
}

// ============================================================================
// SUB-COMPONENT: ZONE POPUP (CLICK INFO PANEL)
// ============================================================================

function ZonePopup({ part, reading, onClose }) {
  const isLeaking =
    reading.alert_triggered && reading.detected_zone === part.zone;
  const residualValues = part.residualKeys.map((key) => ({
    key,
    name: RESIDUAL_NAMES[key] || key,
    value: reading.residuals[key] || 0,
  }));

  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: "absolute",
        top: "16px",
        right: "16px",
        width: "280px",
        background: "#0f1117",
        border: "1px solid #374151",
        borderRadius: "12px",
        padding: "16px",
        zIndex: 100,
        boxShadow: "0 4px 16px rgba(0, 0, 0, 0.8)",
      }}
    >
      {/* Header with close button */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "12px",
        }}
      >
        <h3
          style={{
            margin: 0,
            color: "#ffffff",
            fontSize: "14px",
            fontWeight: "bold",
          }}
        >
          {part.name}
        </h3>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#6b7280",
            padding: "0",
            display: "flex",
            alignItems: "center",
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Description */}
      <p
        style={{
          margin: "0 0 12px 0",
          fontSize: "11px",
          color: "#9ca3af",
          lineHeight: "1.4",
        }}
      >
        {part.description}
      </p>

      {/* Status section */}
      {part.zone && (
        <>
          <div
            style={{
              fontSize: "10px",
              fontWeight: "bold",
              color: "#d1d5db",
              marginBottom: "6px",
            }}
          >
            STATUS
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              fontSize: "12px",
              color: isLeaking ? "#ef4444" : "#22c55e",
              marginBottom: "4px",
            }}
          >
            {isLeaking ? (
              <AlertTriangle
                size={14}
                style={{ marginRight: "6px", color: "#ef4444" }}
              />
            ) : (
              <CheckCircle
                size={14}
                style={{ marginRight: "6px", color: "#22c55e" }}
              />
            )}
            <span style={{ fontWeight: "bold" }}>
              {isLeaking ? "LEAK DETECTED" : "Healthy"}
            </span>
          </div>

          <div
            style={{ fontSize: "11px", color: "#d1d5db", marginBottom: "6px" }}
          >
            Severity:{" "}
            <span style={{ color: "#f59e0b" }}>{reading.severity}/5</span>
          </div>
          <div
            style={{ fontSize: "11px", color: "#d1d5db", marginBottom: "8px" }}
          >
            Confidence:{" "}
            <span style={{ color: "#ffffff" }}>
              {Math.round(reading.leak_probability)}%
            </span>
          </div>
          <div
            style={{ fontSize: "11px", color: "#d1d5db", marginBottom: "12px" }}
          >
            Pattern:{" "}
            <span style={{ color: "#84cc16" }}>{reading.hdbscan_status}</span>
          </div>

          {/* Residuals section */}
          {residualValues.length > 0 && (
            <>
              <div
                style={{
                  fontSize: "10px",
                  fontWeight: "bold",
                  color: "#d1d5db",
                  marginBottom: "6px",
                }}
              >
                RESIDUALS
              </div>
              {residualValues.map((res) => {
                const absVal = Math.abs(res.value);
                const barWidth = Math.min((absVal / 4.5) * 100, 100);
                const barColor = absVal > 1.5 ? "#ef4444" : "#22c55e";
                return (
                  <div key={res.key} style={{ marginBottom: "6px" }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: "10px",
                        color: "#d1d5db",
                        marginBottom: "2px",
                      }}
                    >
                      <span>
                        {res.key.toUpperCase()} {res.name}
                      </span>
                      <span style={{ color: barColor, fontWeight: "bold" }}>
                        {res.value >= 0 ? "+" : ""}
                        {res.value.toFixed(1)} σ
                      </span>
                    </div>
                    <div
                      style={{
                        height: "4px",
                        background: "#1f2937",
                        borderRadius: "2px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${barWidth}%`,
                          background: barColor,
                          transition: "width 0.3s ease",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
              <div
                style={{ fontSize: "11px", color: "#d1d5db", marginTop: "8px" }}
              >
                CUSUM Score:{" "}
                <span style={{ color: "#f59e0b" }}>
                  {reading.cusum_score.toFixed(1)}
                </span>
              </div>
            </>
          )}
        </>
      )}
    </motion.div>
  );
}

// ============================================================================
// MAIN COMPONENT: ENGINE VIEWER 3D
// ============================================================================

export default function EngineViewer3D({ reading }) {
  const [selectedPart, setSelectedPart] = useState(null);
  const containerRef = useRef(null);

  const leakingZone = useMemo(() => {
    if (!reading.alert_triggered || !reading.detected_zone) return null;
    return ENGINE_PARTS.find((p) => p.zone === reading.detected_zone);
  }, [reading.alert_triggered, reading.detected_zone]);

  const leakingZonePosition = leakingZone
    ? new THREE.Vector3(...leakingZone.position)
    : new THREE.Vector3(0, 0, 0);

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        borderRadius: "12px",
        overflow: "hidden",
        background: "#0a0c12",
        border: "2px solid #FFCC00",
        boxShadow: "0 0 20px rgba(255, 204, 0, 0.2)",
      }}
    >
      <Canvas
        camera={{ position: [5, 3, 6], fov: 50 }}
        shadows
        style={{ width: "100%", height: "100%" }}
      >
        {/* Lighting */}
        <ambientLight intensity={0.35} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
        <directionalLight
          position={[-5, 3, -5]}
          intensity={0.4}
          color="#93c5fd"
        />
        <pointLight position={[0, 5, 0]} intensity={0.5} color="#ffffff" />

        {/* Red leak light — only when alert triggered */}
        {reading.alert_triggered && (
          <pointLight
            position={leakingZonePosition}
            intensity={3}
            distance={3}
            color="#ef4444"
          />
        )}

        {/* Background */}
        <Stars radius={80} depth={50} count={3000} factor={3} fade />
        <fog attach="fog" args={["#0a0c12", 10, 25]} />

        {/* Camera auto-focus controller */}
        <CameraController
          alertTriggered={reading.alert_triggered}
          detectedZone={reading.detected_zone}
        />

        {/* OrbitControls */}
        <OrbitControls
          enablePan={false}
          minDistance={3}
          maxDistance={12}
          autoRotate={!reading.alert_triggered}
          autoRotateSpeed={0.4}
        />

        {/* Engine parts */}
        {ENGINE_PARTS.map((config) => (
          <EnginePart
            key={config.id}
            config={config}
            reading={reading}
            isLeaking={
              reading.alert_triggered && reading.detected_zone === config.zone
            }
            onClick={() => setSelectedPart(config)}
          />
        ))}

        {/* Leak particles (smoke effect) */}
        {leakingZone && (
          <LeakParticles
            position={leakingZone.position}
            alertTriggered={reading.alert_triggered}
          />
        )}
      </Canvas>

      {/* Click popup panel */}
      <AnimatePresence>
        {selectedPart && (
          <ZonePopup
            part={selectedPart}
            reading={reading}
            onClose={() => setSelectedPart(null)}
          />
        )}
      </AnimatePresence>

      {/* Legend at bottom */}
      <div
        style={{
          position: "absolute",
          bottom: "12px",
          left: "12px",
          fontSize: "11px",
          color: "#d1d5db",
          background: "rgba(15, 17, 23, 0.7)",
          padding: "8px 12px",
          borderRadius: "6px",
          border: "1px solid #374151",
          backdropFilter: "blur(8px)",
        }}
      >
        <span style={{ marginRight: "16px" }}>● Healthy</span>
        <span style={{ color: "#84cc16", marginRight: "16px" }}>
          ● Suspicious
        </span>
        <span style={{ color: "#f59e0b", marginRight: "16px" }}>● Warning</span>
        <span style={{ color: "#ef4444" }}>● Leak Detected</span>
      </div>
    </div>
  );
}
