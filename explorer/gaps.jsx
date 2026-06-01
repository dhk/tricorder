// gaps.jsx — Tab 4: Team Gaps (three panels)

const GAP_PANELS = [
  { key: "coverage_gap",  title: "Coverage Gaps",  tagGroup: "data",
    blurb: "Standards that exist but aren't enforced everywhere." },
  { key: "knowledge_gap", title: "Knowledge Gaps", tagGroup: "pattern",
    blurb: "Areas where team understanding is thin or uneven." },
  { key: "blind_spot",    title: "Blind Spots",    tagGroup: "team",
    blurb: "Risks no reviewer is consistently catching.", tinted: true },
];

function GapItem({ g, tagGroup }) {
  return (
    <div style={{ padding: "14px 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
        <div style={{ fontFamily: "var(--font-cond)", fontWeight: 600, fontSize: 18, lineHeight: 1.2 }}>{g.area}</div>
        <Tag group={tagGroup} style={{ flexShrink: 0 }}>{g.gap_type.replace("_", " ")}</Tag>
      </div>
      <div style={{ marginTop: 8, display: "flex", gap: 7, alignItems: "flex-start" }}>
        <span style={{ color: "var(--text-dim)", fontFamily: "var(--font-mono)", fontSize: 11, marginTop: 1 }}>§</span>
        <Mono dim style={{ fontSize: 11.5, lineHeight: 1.45 }}>{g.standard_citation}</Mono>
      </div>
      <div style={{ marginTop: 9, display: "flex", gap: 6, alignItems: "baseline" }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)",
          textTransform: "uppercase", letterSpacing: "0.05em", flexShrink: 0,
        }}>Fix →</span>
        <span style={{ color: "var(--text-dim)", fontSize: 13.5, fontWeight: 300, lineHeight: 1.5 }}>{g.recommendation}</span>
      </div>
    </div>
  );
}

function GapPanel({ panel, items }) {
  return (
    <div style={{
      background: panel.tinted ? "rgba(217,79,42,0.05)" : "#fff",
      border: `1px solid ${panel.tinted ? "rgba(217,79,42,0.22)" : "var(--border)"}`,
      borderRadius: "var(--border-radius)",
      padding: "20px 20px 6px",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h3 style={{
            fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 20, margin: 0,
            color: panel.tinted ? "var(--accent-orange)" : "var(--text)",
          }}>{panel.title}</h3>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
            background: panel.tinted ? "rgba(217,79,42,0.10)" : "var(--bg2)",
            border: `1px solid ${panel.tinted ? "rgba(217,79,42,0.22)" : "var(--border)"}`,
            borderRadius: "var(--border-radius)", padding: "1px 6px",
          }}>{items.length}</span>
        </div>
        <Mono dim style={{ fontSize: 11.5, marginTop: 6, display: "block", lineHeight: 1.45 }}>{panel.blurb}</Mono>
      </div>
      <div>
        {items.map((g, i) => <GapItem key={i} g={g} tagGroup={panel.tagGroup} />)}
      </div>
    </div>
  );
}

function GapsTab() {
  const grouped = useMemo(() => {
    const g = {};
    GAP_PANELS.forEach(p => {
      g[p.key] = DATA.gaps
        .filter(x => x.gap_type === p.key)
        .sort((a, b) => (a.criticality ?? 9) - (b.criticality ?? 9)); // most critical first
    });
    return g;
  }, []);

  return (
    <div style={{ padding: "28px 32px 48px", animation: "fadeIn 200ms ease" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 28, margin: 0 }}>Team Gaps</h2>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, maxWidth: 640 }}>
            Where the team's collective review coverage falls short — sorted most critical first within each category.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 18, alignItems: "start" }}>
          {GAP_PANELS.map(p => <GapPanel key={p.key} panel={p} items={grouped[p.key]} />)}
        </div>
      </div>
    </div>
  );
}

window.GapsTab = GapsTab;
