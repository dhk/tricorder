// pipeline.jsx — Tab 2: Maturity Pipeline (read-only kanban)
// Columns: judgment -> guidance -> convention -> rule -> deterministic

function PatternCard({ p }) {
  const [hover, setHover] = useState(false);
  const grp = groupForCategory(p.category);
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: "#fff",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${hover ? "var(--accent)" : "var(--border)"}`,
        borderRadius: "var(--border-radius)",
        padding: "12px 13px 13px",
        transition: "border-color 120ms ease, box-shadow 120ms ease",
        boxShadow: hover ? "0 4px 12px rgba(10,10,9,0.06)" : "none",
      }}>
      <div style={{ marginBottom: 9 }}>
        <Tag group={grp}>{p.category}</Tag>
      </div>
      <div style={{
        fontFamily: "var(--font-cond)", fontWeight: 600, fontSize: 17, lineHeight: 1.18,
        letterSpacing: "0.005em", color: "var(--text)",
      }}>{p.signal}</div>
      <div style={{ marginTop: 10, display: "flex", gap: 7, alignItems: "flex-start" }}>
        <span style={{ color: "var(--text-dim)", fontFamily: "var(--font-mono)", fontSize: 11, marginTop: 1 }}>§</span>
        <Mono dim style={{ fontSize: 11.5, lineHeight: 1.45 }}>{p.standard_citation}</Mono>
      </div>
    </div>
  );
}

function PipelineColumn({ stage, items }) {
  const meta = MATURITY[stage];
  return (
    <div style={{ display: "flex", flexDirection: "column", minWidth: 0, height: "100%" }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 4px 10px", borderBottom: "2px solid var(--border)", marginBottom: 12,
      }}>
        <Mono style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 500 }}>{stage}</Mono>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
          background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--border-radius)",
          padding: "1px 6px",
        }}>{items.length}</span>
      </div>
      <div style={{
        display: "flex", flexDirection: "column", gap: 10,
        overflowY: "auto", paddingRight: 4, flex: 1, minHeight: 0,
      }}>
        {items.length === 0 ? (
          <div style={{
            border: "1px dashed var(--border)", borderRadius: "var(--border-radius)",
            padding: "18px 12px", textAlign: "center",
          }}>
            <Mono dim style={{ fontSize: 11.5, lineHeight: 1.5 }}>no patterns have<br/>reached this stage</Mono>
          </div>
        ) : items.map((p, i) => <PatternCard key={i} p={p} />)}
      </div>
    </div>
  );
}

function PipelineTab() {
  const byStage = useMemo(() => {
    const g = {}; MATURITY_ORDER.forEach(s => { g[s] = []; });
    DATA.patterns.forEach(p => { if (g[p.maturity]) g[p.maturity].push(p); });
    return g;
  }, []);

  return (
    <div style={{ padding: "28px 32px 36px", height: "100%", display: "flex", flexDirection: "column", animation: "fadeIn 200ms ease" }}>
      <div style={{ maxWidth: 1320, margin: "0 auto", width: "100%", display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 28, margin: 0 }}>Maturity Pipeline</h2>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, maxWidth: 640 }}>
            How far each review pattern has progressed from human judgment toward a deterministic, automatable check.
          </p>
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 18,
          flex: 1, minHeight: 0, alignItems: "stretch",
        }}>
          {MATURITY_ORDER.map(stage => (
            <PipelineColumn key={stage} stage={stage} items={byStage[stage]} />
          ))}
        </div>
      </div>
    </div>
  );
}

window.PipelineTab = PipelineTab;
