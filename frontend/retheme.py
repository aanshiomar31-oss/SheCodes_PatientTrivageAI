import pathlib

SUBS = [
    # card shells — longest first, order matters
    ("overflow-hidden rounded-2xl border border-slate-700/50 bg-white/5 backdrop-blur-md", "overflow-hidden panel"),
    ("overflow-hidden rounded-xl border border-slate-700/50 bg-white/5 backdrop-blur-sm", "overflow-hidden panel"),
    ("space-y-4 rounded-2xl border border-slate-700/50 bg-white/5 p-6 backdrop-blur-md", "space-y-4 panel p-6"),
    ("rounded-2xl border border-slate-700/50 bg-white/5 p-6 backdrop-blur-md", "panel p-6"),
    ("rounded-2xl border border-slate-700/50 bg-white/5 p-5 backdrop-blur-md", "panel p-5"),
    ("rounded-2xl border border-slate-700/50 bg-white/5 p-4 backdrop-blur-md", "panel p-4"),
    ("rounded-2xl border border-slate-700/50 bg-white/5 backdrop-blur-md", "panel"),
    ("rounded-xl border border-slate-700/50 bg-white/5 p-6 backdrop-blur-sm", "panel p-6"),
    ("rounded-xl border border-slate-700/50 bg-white/5 px-4 py-3 backdrop-blur-sm", "panel px-4 py-3"),
    ("rounded-xl border border-slate-700/50 bg-white/5 backdrop-blur-sm", "panel"),
    ("rounded-xl border border-surface-border bg-white px-4 py-3 text-sm text-surface-muted backdrop-blur-sm", "panel px-4 py-3 text-sm text-surface-muted"),
    ("rounded-xl border border-surface-border bg-white p-6 text-sm text-surface-muted backdrop-blur-sm", "panel p-6 text-sm text-surface-muted"),
    ("rounded-2xl border border-surface-border bg-white p-6 text-sm text-surface-muted backdrop-blur-md", "panel p-6 text-sm text-surface-muted"),

    # alerts
    ("border border-red-500/40 bg-red-500/10", "border border-red-200 bg-red-50"),
    ("border-red-500/40 bg-red-500/10", "border-red-200 bg-red-50"),
    ("hover:bg-red-500/20", "hover:bg-red-100"),
    ("border border-orange-500/40 bg-orange-500/10", "border border-amber-200 bg-amber-50"),
    ("border-orange-500/40 bg-orange-500/10", "border-amber-200 bg-amber-50"),
    ("text-orange-200", "text-amber-700"),
    ("text-red-300", "text-red-600"),
    ("text-red-400", "text-red-500"),
    ("text-green-400", "text-accent-mintInk"),
    ("bg-green-400", "bg-accent-mint"),
    ("text-purple-300", "text-violet-600"),
    ("border-purple-500/40 bg-purple-500/10", "border-violet-200 bg-violet-50"),
    ("text-emerald-300", "text-accent-mintInk"),

    # sky accent -> mint
    ("border-sky-400 bg-sky-500/20 text-sky-200", "border-accent-mint bg-accent-wash text-accent-mintInk"),
    ("border-sky-500/40 bg-sky-500/15 text-sky-200", "border-accent-mint/40 bg-accent-wash text-accent-mintInk"),
    ("border border-sky-500/30 bg-sky-500/10", "border border-accent-mint/30 bg-accent-wash"),
    ("border border-sky-500/40 bg-sky-500/10", "border border-accent-mint/40 bg-accent-wash"),
    ("border-sky-500/30 bg-sky-500/10", "border-accent-mint/30 bg-accent-wash"),
    ("border-sky-500/40 bg-sky-500/10", "border-accent-mint/40 bg-accent-wash"),
    ("w-full rounded-lg bg-sky-500 px-5 py-3 text-sm font-semibold text-white shadow-glow transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60", "btn-primary w-full"),
    ("hover:bg-sky-500/20", "hover:bg-accent-mint/15"),
    ("bg-sky-500/20", "bg-accent-wash"),
    ("bg-sky-500/15", "bg-accent-wash"),
    ("bg-sky-500/10", "bg-accent-wash"),
    ("bg-sky-500 text-white", "bg-accent-mint text-white"),
    ('bg-sky-500"', 'bg-accent-mint"'),
    ("bg-sky-600", "bg-accent-mint"),
    ("hover:bg-sky-500", "hover:brightness-95"),
    ("ring-sky-400", "ring-accent-mint"),
    ("focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500", "focus:border-accent-mint focus:outline-none focus:ring-1 focus:ring-accent-mint/40"),
    ("focus:border-sky-500 focus:outline-none", "focus:border-accent-mint focus:outline-none"),
    ("border-sky-500/30", "border-accent-mint/30"),
    ("text-sky-300", "text-accent-mintInk"),
    ("text-sky-200", "text-accent-mintInk"),
    ("text-sky-400", "text-accent-mintInk"),

    # surfaces
    ("border border-slate-700/50", "border border-surface-border"),
    ("border-slate-700/50", "border-surface-border"),
    ("border border-slate-700", "border border-surface-border"),
    ("border-slate-700", "border-surface-border"),
    ("border-slate-800", "border-surface-border"),
    ("border-slate-600", "border-surface-border"),
    ("border-slate-300", "border-surface-border"),
    ("bg-slate-900/60", "bg-[#FAFBFC]"),
    ("bg-slate-900", "bg-white"),
    ("bg-slate-800/60", "bg-slate-100"),
    ("bg-slate-800", "bg-slate-100"),
    ("hover:bg-white/10", "hover:bg-slate-100"),
    ("hover:bg-white/5", "hover:bg-slate-50"),
    ("bg-white/10", "bg-slate-100"),
    ("bg-white/40", "bg-white"),
    ("bg-white/5", "bg-white"),
    ("divide-slate-800", "divide-surface-border"),
    ("divide-slate-700", "divide-surface-border"),
    ("border-t border-white/10", "border-t border-surface-border"),

    # legacy already-light pages, onto the same tokens
    ("rounded-xl border border-slate-200 bg-white p-6 shadow-sm", "panel p-6"),
    ("overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm", "overflow-hidden panel"),

    # type
    ("text-white", "text-surface-ink"),
    ("text-slate-100", "text-surface-ink"),
    ("text-slate-200", "text-surface-ink"),
    ("text-slate-900", "text-surface-ink"),
    ("text-slate-300", "text-slate-600"),
    ("text-slate-700", "text-slate-600"),
    ("text-slate-400", "text-surface-muted"),
    ("text-slate-500", "text-surface-muted"),
    ("placeholder-slate-500", "placeholder-surface-muted"),
    ("shadow-glow", "shadow-card"),

    # recharts
    ('background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 12',
     'background: "#fff", border: "1px solid #ECEFF3", borderRadius: 16, fontSize: 12, boxShadow: "0 8px 30px -12px rgba(16,24,40,0.18)", color: "#1A1D1F"'),
    ('stroke="#1e293b"', 'stroke="#ECEFF3"'),
    ('stroke="#334155"', 'stroke="#ECEFF3"'),
    ('stroke="#e2e8f0"', 'stroke="#ECEFF3"'),
    ('axisLine={{ stroke: "#334155" }}', 'axisLine={{ stroke: "#E4E8EE" }}'),
    ('fill: "#94a3b8"', 'fill: "#9AA1A9"'),
    ('"#38bdf8"', '"#34D07F"'),
]

for p in sorted(pathlib.Path("src").rglob("*.jsx")):
    t = orig = p.read_text()
    for a, b in SUBS:
        t = t.replace(a, b)
    if t != orig:
        p.write_text(t)
        print("changed", p)

print("Done.")
