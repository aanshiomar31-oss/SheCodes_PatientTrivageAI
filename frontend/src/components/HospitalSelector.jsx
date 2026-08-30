const HOSPITALS = [
  {
    id: "rural",
    name: "Rural Emergency Center",
    flow: "100 pts/day",
    beds: 12,
    nurses: 4,
    desc: "Single physician, local community coverage, restricted critical trauma beds.",
    icon: "🏡",
  },
  {
    id: "district",
    name: "District General Hospital",
    flow: "250 pts/day",
    beds: 40,
    nurses: 15,
    desc: "Multi-specialty secondary care center with intermediate ICU capabilities.",
    icon: "🏢",
  },
  {
    id: "urban",
    name: "Urban Trauma Center",
    flow: "600 pts/day",
    beds: 120,
    nurses: 45,
    desc: "Level 1 regional trauma hub, full stroke/cardiac response capabilities.",
    icon: "🏥",
  },
];

export default function HospitalSelector({ selectedId, onSelect }) {
  return (
    <div className="panel p-5 space-y-4">
      <div>
        <h3 className="label">Active Facility Nodes</h3>
        <p className="text-xs text-surface-muted mt-1">Switch nodes to inspect localized queue capacities.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {HOSPITALS.map((h) => {
          const active = selectedId === h.id;
          return (
            <button
              key={h.id}
              onClick={() => onSelect(h.id)}
              className={`w-full text-left p-4 rounded-xl border transition-all ${
                active
                  ? "bg-accent-wash border-accent-mint/30 shadow-sm"
                  : "border-surface-border bg-surface-bg/10 hover:bg-surface-bg/25"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-2xl">{h.icon}</span>
                <span className="text-[10px] font-bold text-accent-mint bg-[#10241B] px-2 py-0.5 rounded border border-accent-mint/20">
                  {h.flow}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white mt-3">{h.name}</h4>
              <p className="text-xs text-surface-muted mt-1 leading-relaxed">{h.desc}</p>
              
              <div className="mt-4 flex gap-3 text-[10px] text-surface-muted font-bold uppercase tracking-wider">
                <span>Beds: {h.beds}</span>
                <span>•</span>
                <span>Nurses: {h.nurses}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
