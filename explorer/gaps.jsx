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
        <div style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 16, lineHeight: 1.3, color: "var(--text)" }}>{g.area}</div>
        <Tag group={tagGroup} style={{ flexShrink: 0 }}>{g.gap_type.replace("_", " ")}</Tag>
      </div>
      <div style={{ marginTop: 8, display: "flex", gap: 7, alignItems: "flex-start" }}>
        <span style={{ color: "var(--text-dim)", fontFamily: "var(--font-mono)", fontSize: 11, marginTop: 1 }}>§</span>
        <Mono dim style={{ fontSize: 11, lineHeight: 1.45 }}>{g.standard_citation}</Mono>
      </div>
      <div style={{ marginTop: 9, display: "flex", gap: 6, alignItems: "baseline" }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--accent)",
          textTransform: "uppercase", letterSpacing: "0.05em", flexShrink: 0,
        }}>Fix →</span>
        <span style={{ color: "var(--text-dim)", fontSize: 13.5, fontWeight: 400, lineHeight: 1.5 }}>{g.recommendation}</span>
      </div>
    </div>
  );
}

function GapPanel({ panel, items }) {
  return (
    <div style={{
      background: panel.tinted ? "rgba(224,92,42,0.05)" : "var(--bg)",
      border: `1px solid ${panel.tinted ? "rgba(224,92,42,0.22)" : "var(--border)"}`,
      borderRadius: "var(--radius)",
      padding: "20px 20px 6px",
      display: "flex", flexDirection: "column",
    }}>
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h3 style={{
            fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 20, margin: 0,
            color: panel.tinted ? "var(--accent-orange)" : "var(--text)",
          }}>{panel.title}</h3>
          <span style={{
            fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
            background: panel.tinted ? "rgba(224,92,42,0.10)" : "var(--bg2)",
            border: `1px solid ${panel.tinted ? "rgba(224,92,42,0.22)" : "var(--border)"}`,
            borderRadius: "var(--radius)", padding: "1px 6px",
          }}>{items.length}</span>
        </div>
        <Mono dim style={{ fontSize: 11, marginTop: 6, display: "block", lineHeight: 1.45 }}>{panel.blurb}</Mono>
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
    <div style={{ padding: "28px 32px 48px" }}>
      <div style={{ maxWidth: 1280, margin: "0 auto" }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 28, margin: 0 }}>Team Gaps</h2>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, maxWidth: 640 }}>
            Where the team's collective review coverage falls short — sorted most critical first within each category.
          </p>
        </div>
        <TabExplainer
          read="Three kinds of gap. Coverage gap: a standard exists but nobody enforces it in review. Knowledge gap: reviewers raise it, but shallowly or inconsistently. Blind spot: a named best practice from the lens that never appears in any review. Each panel is ordered most critical first, and each item names the standard it maps to and a fix."
          act="Take the blind spots to the team as candidates for a checklist line or a CI gate. Treat knowledge gaps as training or pairing topics. A coverage gap usually means naming an owner. If a gap concerns something the repo's own tooling already enforces, it is a false positive: say so and move on." />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 18, alignItems: "start" }}>
          {GAP_PANELS.map(p => <GapPanel key={p.key} panel={p} items={grouped[p.key]} />)}
        </div>
      </div>
    </div>
  );
}

window.GapsTab = GapsTab;
