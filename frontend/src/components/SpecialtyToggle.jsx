const SPECIALTIES = [
  { id: "general", label: "General ED", icon: "🏥" },
  { id: "peds", label: "Pediatrics", icon: "👶" },
  { id: "trauma", label: "Trauma Hub", icon: "🚨" },
  { id: "cardiology", label: "Cardiology", icon: "❤️" },
  { id: "stroke", label: "Stroke Unit", icon: "🧠" },
];

export default function SpecialtyToggle({ selectedId, onSelect }) {
  return (
    <div className="space-y-2">
      <span className="text-xs font-bold text-surface-muted block uppercase tracking-wider">Filter Specialty Mix</span>
      <div className="flex flex-wrap gap-2">
        {SPECIALTIES.map((spec) => {
          const active = selectedId === spec.id;
          return (
            <button
              key={spec.id}
              onClick={() => onSelect(spec.id)}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 border ${
                active
                  ? "bg-accent-blue text-white shadow-sm border-accent-blue"
                  : "bg-accent-wash text-surface-muted hover:text-white border-surface-border"
              }`}
            >
              <span>{spec.icon}</span>
              <span>{spec.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
