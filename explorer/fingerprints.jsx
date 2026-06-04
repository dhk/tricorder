// fingerprints.jsx — Tab 5: Reviewer Fingerprints (Recharts radar)

const SIGNAL = {
  high:   { color: "var(--accent)",       label: "high" },
  medium: { color: "var(--accent-blue)",  label: "medium" },
  low:    { color: "var(--text-dim)",     label: "low" },
};

function SignalBadge({ q }) {
  const s = SIGNAL[q] || SIGNAL.low;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <Mono dim style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>signal</Mono>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 11.5, color: s.color, fontWeight: 500,
        textTransform: "uppercase", letterSpacing: "0.04em",
        border: `1px solid ${s.color}`, borderRadius: "var(--border-radius)",
        padding: "1px 7px", opacity: q === "low" ? 0.85 : 1,
      }}>{s.label}</span>
    </span>
  );
}

function FreqBadge({ frequency }) {
  return (
    <span style={{
      fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--text-dim)",
      textTransform: "uppercase", letterSpacing: "0.05em",
      background: "var(--bg2)", border: "1px solid var(--border)",
      borderRadius: "var(--border-radius)", padding: "1px 7px",
    }}>{frequency}</span>
  );
}

function ReviewerCard({ r }) {
  const {
    RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, PolarRadiusAxis,
  } = Recharts;

  const chartData = DATA.RADAR_CATEGORIES.map(c => ({
    category: c,
    value: r.category_freq[c] ?? 0,
  }));

  return (
    <div style={{
      background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--border-radius)",
      padding: "20px 22px 22px", display: "flex", flexDirection: "column",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 24, lineHeight: 1 }}>{r.login}</div>
          <Mono dim style={{ fontSize: 11.5, marginTop: 5, textTransform: "uppercase", letterSpacing: "0.04em" }}>{r.review_style} reviewer</Mono>
        </div>
        <SignalBadge q={r.signal_quality} />
      </div>

      <div style={{ height: 244, margin: "8px -6px 6px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData} outerRadius="72%" margin={{ top: 14, right: 18, bottom: 14, left: 18 }}>
            <PolarGrid stroke="#e3e1dc" />
            <PolarAngleAxis dataKey="category"
              tick={{ fontFamily: "DM Mono, monospace", fontSize: 10, fill: "#5a5850" }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar dataKey="value" stroke="#16a34a" strokeWidth={2}
              fill="#16a34a" fillOpacity={0.15} isAnimationActive={true} animationDuration={500} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16, marginTop: 4 }}>
        <div>
          <CardHeading style={{ color: "var(--accent)" }}>Focus Areas</CardHeading>
          <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {r.primary_focus_areas.map((f, i) => (
              <li key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10 }}>
                <span style={{ fontSize: 14, lineHeight: 1.4, flex: 1, minWidth: 0 }}>{f.area}</span>
                <FreqBadge frequency={f.frequency} />
              </li>
            ))}
          </ul>
        </div>
        <div>
          <CardHeading style={{ color: "var(--text-dim)" }}>Blind Spots</CardHeading>
          <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {r.apparent_blind_spots.map((b, i) => (
              <li key={i} style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
                <span style={{ color: "var(--text-dim)", fontSize: 12, lineHeight: 1.4 }}>◦</span>
                <div>
                  <span style={{ fontSize: 13.5, color: "var(--text-dim)", fontStyle: "italic", lineHeight: 1.4 }}>{b.area}</span>
                  <span style={{ fontSize: 12.5, color: "var(--text-dim)", fontStyle: "italic", opacity: 0.85 }}> — {b.basis}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Composite radar ───────────────────────────────────────────────────────────
// All reviewers on one chart. High/medium signal = bold stroke + fill.
// Low signal = faint outline. Immediately shows who covers what and the gaps.

const COMPOSITE_PALETTE = [
  "#16a34a", "#2970d6", "#7c5ce0", "#d94f2a", "#0ea5e9",
  "#f59e0b", "#10b981", "#8b5cf6", "#ef4444", "#06b6d4",
  "#84cc16", "#f97316", "#6366f1", "#14b8a6",
];

function CompositeRadar() {
  const {
    RadarChart, PolarGrid, PolarAngleAxis, Radar,
    ResponsiveContainer, PolarRadiusAxis, Legend,
  } = Recharts;

  const revs = DATA.reviewers.filter(r => r.category_freq);

  const chartData = DATA.RADAR_CATEGORIES.map(cat => {
    const row = { category: cat };
    revs.forEach(r => { row[r.login] = r.category_freq[cat] ?? 0; });
    return row;
  });

  return (
    <div style={{
      background: "#fff", border: "1px solid var(--border)",
      borderRadius: "var(--border-radius)", padding: "20px 24px 16px",
      marginBottom: 28,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
        <CardHeading>Team overview</CardHeading>
        <Mono dim style={{ fontSize: 10.5 }}>bold = high / medium signal &nbsp; faint = low signal</Mono>
      </div>
      <div style={{ height: 380, margin: "0 -6px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData} outerRadius="68%" margin={{ top: 16, right: 32, bottom: 0, left: 32 }}>
            <PolarGrid stroke="#e8e6e1" />
            <PolarAngleAxis dataKey="category"
              tick={{ fontFamily: "DM Mono, monospace", fontSize: 10, fill: "#5a5850" }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            {revs.map((r, i) => {
              const isHigh = r.signal_quality === "high";
              const isMed  = r.signal_quality === "medium";
              const color  = COMPOSITE_PALETTE[i % COMPOSITE_PALETTE.length];
              return (
                <Radar key={r.login} name={r.login} dataKey={r.login}
                  stroke={color} strokeWidth={isHigh ? 2.5 : isMed ? 1.8 : 1}
                  strokeOpacity={isHigh ? 1 : isMed ? 0.75 : 0.28}
                  fill={color}
                  fillOpacity={isHigh ? 0.13 : isMed ? 0.07 : 0.02}
                  isAnimationActive={false} />
              );
            })}
            <Legend iconType="line" iconSize={16}
              wrapperStyle={{ fontFamily: "DM Mono, monospace", fontSize: 10.5, paddingTop: 10 }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function FingerprintsTab() {
  return (
    <div style={{ padding: "28px 32px 48px", animation: "fadeIn 200ms ease" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 28, margin: 0 }}>Reviewer Fingerprints</h2>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, maxWidth: 640 }}>
            The shape of each reviewer's attention across nine categories. Team overview first, then individual fingerprints.
          </p>
        </div>
        <CompositeRadar />
        <div style={{
          display: "grid", gap: 18,
          gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))",
        }}>
          {DATA.reviewers.map((r, i) => <ReviewerCard key={i} r={r} />)}
        </div>
      </div>
    </div>
  );
}

window.FingerprintsTab = FingerprintsTab;
