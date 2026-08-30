import { motion } from "framer-motion";

export default function NetworkMap({ activeHospitalId }) {
  // Define positions for nodes
  // Node 1: Rural (Left)
  // Node 2: District (Center-Top)
  // Node 3: Urban (Right)
  const isRuralActive = activeHospitalId === "rural";
  const isDistrictActive = activeHospitalId === "district";
  const isUrbanActive = activeHospitalId === "urban";

  return (
    <div className="panel p-5 space-y-4">
      <div>
        <h3 className="label">Live Regional Referral & Transfer Network</h3>
        <p className="text-xs text-surface-muted mt-1">Real-time status of capacity-sharing and patient transfer pipelines.</p>
      </div>

      <div className="h-64 relative bg-[#091510] border border-surface-border rounded-xl overflow-hidden flex items-center justify-center">
        <svg className="w-full h-full max-w-lg" viewBox="0 0 500 250">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 2 L 10 5 L 0 8 z" fill="#81C784" />
            </marker>
            <marker id="arrow-active" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 2 L 10 5 L 0 8 z" fill="#4CAF50" />
            </marker>
          </defs>

          {/* Connection Lines (Referral Paths) */}
          {/* Rural to Urban */}
          <path
            d="M 100 150 Q 250 200 400 120"
            fill="none"
            stroke={isRuralActive || isUrbanActive ? "#4CAF50" : "#2C4E3D"}
            strokeWidth={2}
            strokeDasharray="6 4"
            className="animate-pulse"
            markerEnd="url(#arrow)"
          />
          {/* District to Urban */}
          <path
            d="M 250 70 Q 330 80 400 120"
            fill="none"
            stroke={isDistrictActive || isUrbanActive ? "#4CAF50" : "#2C4E3D"}
            strokeWidth={2}
            strokeDasharray="6 4"
            markerEnd="url(#arrow)"
          />
          {/* Rural to District */}
          <path
            d="M 100 150 Q 170 100 250 70"
            fill="none"
            stroke={isRuralActive || isDistrictActive ? "#4CAF50" : "#2C4E3D"}
            strokeWidth={1.5}
            strokeDasharray="4 4"
            markerEnd="url(#arrow)"
          />

          {/* Node 1: Rural Node */}
          <g className="cursor-pointer">
            <circle
              cx="100"
              cy="150"
              r={isRuralActive ? "24" : "18"}
              fill="#1F3A2D"
              stroke={isRuralActive ? "#81C784" : "#2C4E3D"}
              strokeWidth="3"
            />
            <circle cx="100" cy="150" r="6" fill={isRuralActive ? "#81C784" : "#2C4E3D"} />
            <text x="100" y="195" textAnchor="middle" fill="#FFF" className="text-[10px] font-bold">Rural Center</text>
            <text x="100" y="210" textAnchor="middle" fill="#8CA397" className="text-[9px]">Cap: 8/12</text>
          </g>

          {/* Node 2: District Node */}
          <g className="cursor-pointer">
            <circle
              cx="250"
              cy="70"
              r={isDistrictActive ? "24" : "18"}
              fill="#1F3A2D"
              stroke={isDistrictActive ? "#81C784" : "#2C4E3D"}
              strokeWidth="3"
            />
            <circle cx="250" cy="70" r="6" fill={isDistrictActive ? "#81C784" : "#2C4E3D"} />
            <text x="250" y="115" textAnchor="middle" fill="#FFF" className="text-[10px] font-bold">District General</text>
            <text x="250" y="130" textAnchor="middle" fill="#8CA397" className="text-[9px]">Cap: 34/40</text>
          </g>

          {/* Node 3: Urban Node */}
          <g className="cursor-pointer">
            <circle
              cx="400"
              cy="120"
              r={isUrbanActive ? "26" : "20"}
              fill="#1F3A2D"
              stroke={isUrbanActive ? "#81C784" : "#2C4E3D"}
              strokeWidth="3"
            />
            <circle cx="400" cy="120" r="8" fill={isUrbanActive ? "#81C784" : "#2C4E3D"} />
            <text x="400" y="170" textAnchor="middle" fill="#FFF" className="text-[10px] font-bold">Urban Trauma Hub</text>
            <text x="400" y="185" textAnchor="middle" fill="#8CA397" className="text-[9px]">Cap: 104/120</text>
          </g>
        </svg>

        {/* Transfer Indicator */}
        <div className="absolute bottom-4 right-4 bg-accent-wash border border-surface-border rounded-xl p-3 text-[10px] space-y-1">
          <p className="text-white font-bold">📡 Active Capacity Exchange</p>
          <p className="text-surface-muted">Automatic referral suggestions active for P3/P4 overflow.</p>
        </div>
      </div>
    </div>
  );
}
