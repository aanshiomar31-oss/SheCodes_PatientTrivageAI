/**
 * ConfidenceGauge — semicircular gauge for a 0-1 confidence score.
 * Color bands match the platform's convention: below 0.6 is genuinely
 * low confidence (per the uncertainty gate in backend/ml/uncertainty.py),
 * not an arbitrary UI threshold.
 */
export default function ConfidenceGauge({ confidence, size = 160, label = "Confidence" }) {
  const pct = Math.max(0, Math.min(1, confidence ?? 0));
  const angle = Math.PI * (1 - pct);
  const radius = size / 2 - 12;
  const cx = size / 2;
  const cy = size / 2;

  const needleX = cx + radius * 0.82 * Math.cos(angle);
  const needleY = cy - radius * 0.82 * Math.sin(angle);

  const arcPath = (startFrac, endFrac) => {
    const a1 = Math.PI * (1 - startFrac);
    const a2 = Math.PI * (1 - endFrac);
    const x1 = cx + radius * Math.cos(a1);
    const y1 = cy - radius * Math.sin(a1);
    const x2 = cx + radius * Math.cos(a2);
    const y2 = cy - radius * Math.sin(a2);
    return `M ${x1} ${y1} A ${radius} ${radius} 0 0 1 ${x2} ${y2}`;
  };

  const color = pct >= 0.75 ? "#4ade80" : pct >= 0.6 ? "#facc15" : "#f87171";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 24} viewBox={`0 0 ${size} ${size / 2 + 24}`}>
        <path d={arcPath(0, 0.6)} stroke="#f87171" strokeWidth="10" fill="none" opacity="0.35" strokeLinecap="round" />
        <path d={arcPath(0.6, 0.75)} stroke="#facc15" strokeWidth="10" fill="none" opacity="0.35" strokeLinecap="round" />
        <path d={arcPath(0.75, 1)} stroke="#4ade80" strokeWidth="10" fill="none" opacity="0.35" strokeLinecap="round" />
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke={color} strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="5" fill={color} />
      </svg>
      <p className="text-2xl font-bold" style={{ color }}>
        {(pct * 100).toFixed(0)}%
      </p>
      <p className="text-xs uppercase tracking-wide text-surface-muted">{label}</p>
    </div>
  );
}
