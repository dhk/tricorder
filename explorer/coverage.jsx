// coverage.jsx — Tab: Pattern Coverage
// Reviewers (Y) × 9 categories (X). Cell fill = coverage depth (discrete green shades).
// Click a cell -> drawer with quoted evidence.

function buildCoverage() {
  const cats = DATA.CATEGORIES;
  const revs = DATA.reviewers.map(r => r.login);
  const m = {};
  revs.forEach(r => { m[r] = {}; cats.forEach(c => { m[r][c] = { count: 0, items: [] }; }); });
  DATA.patterns.forEach(p => {
    if (!m[p.reviewer] || !m[p.reviewer][p.category]) return;
    const cell = m[p.reviewer][p.category];
    const ev = p.evidence || [];
    cell.count += ev.length;
    ev.forEach(e => cell.items.push({ ...e, signal: p.signal, category: p.category, citation: p.standard_citation }));
  });
  return { m, revs, cats };
}

// Discrete coverage shades — not a continuous heat map.
// white -> 0.12 -> 0.30 -> 0.55 green.
function coverageStep(count) {
  if (count <= 0) return { fill: "#ffffff", border: "var(--border)", on: false, level: 0 };
  if (count === 1) return { fill: "rgba(22,163,74,0.12)", border: "rgba(22,163,74,0.22)", on: true, level: 1 };
  if (count === 2) return { fill: "rgba(22,163,74,0.30)", border: "rgba(22,163,74,0.34)", on: true, level: 2 };
  return { fill: "rgba(22,163,74,0.55)", border: "rgba(22,163,74,0.50)", on: true, level: 3 };
}

function CoverageCell({ data, label, onClick }) {
  const [hover, setHover] = useState(false);
  const step = coverageStep(data.count);
  return (
    <button
      onClick={step.on ? onClick : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={step.on ? `${label} — ${data.count} reviewed for this dimension` : `${label} — no coverage`}
      style={{
        all: "unset",
        position: "relative",
        height: 46,
        borderRadius: "var(--border-radius)",
        background: step.fill,
        border: `1px solid ${step.border}`,
        cursor: step.on ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: hover && step.on ? "0 0 0 2px var(--accent)" : "none",
        transition: "box-shadow 120ms ease, transform 120ms ease",
        transform: hover && step.on ? "translateY(-1px)" : "none",
        zIndex: hover && step.on ? 2 : 1,
      }}>
      {step.on && (
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12,
          fontWeight: 500,
          color: step.level >= 3 ? "#fff" : "var(--text-dim)",
        }}>{data.count}</span>
      )}
    </button>
  );
}

function CoverageDrawer({ payload, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!payload) return null;
  const { reviewer, category, cell } = payload;
  const grp = groupForCategory(category);
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50 }}>
      <div onClick={onClose}
        style={{ position: "absolute", inset: 0, background: "rgba(10,10,9,0.28)", animation: "fadeIn 160ms ease" }} />
      <aside style={{
        position: "absolute", top: 0, right: 0, height: "100%", width: "min(460px, 92vw)",
        background: "var(--bg)", borderLeft: "1px solid var(--border)",
        boxShadow: "-18px 0 40px rgba(10,10,9,0.10)",
        animation: "drawerIn 220ms cubic-bezier(0.22,1,0.36,1)",
        display: "flex", flexDirection: "column",
      }}>
        <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <Mono dim style={{ fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase" }}>Coverage evidence</Mono>
              <div style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 26, lineHeight: 1.05, marginTop: 4 }}>
                {reviewer}
              </div>
            </div>
            <button onClick={onClose} style={{
              all: "unset", cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: 18,
              color: "var(--text-dim)", padding: "2px 8px", borderRadius: "var(--border-radius)",
              lineHeight: 1,
            }} title="Close (Esc)">✕</button>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "center" }}>
            <Tag group={grp} size="md">{category}</Tag>
            <Mono dim style={{ fontSize: 12 }}>{cell.count} reviewed for this dimension</Mono>
          </div>
        </div>
        <div style={{ overflowY: "auto", padding: "8px 24px 32px", flex: 1 }}>
          {cell.items.map((it, i) => (
            <div key={i} style={{
              padding: "16px 0",
              borderBottom: i < cell.items.length - 1 ? "1px solid var(--border)" : "none",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8, gap: 10 }}>
                <Mono style={{ fontSize: 12.5, color: "var(--accent-blue)" }}>{it.pr}</Mono>
                <Mono dim style={{ fontSize: 11.5 }}>{it.date}</Mono>
              </div>
              <div style={{
                fontFamily: "var(--font-sans)", fontWeight: 400, fontSize: 14.5, lineHeight: 1.55,
                color: "var(--text)", paddingLeft: 14, borderLeft: "2px solid var(--accent)",
              }}>“{it.quote}”</div>
              <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <Mono dim style={{ fontSize: 11.5 }}>on {it.author}'s PR</Mono>
                <span style={{ color: "var(--border)" }}>·</span>
                <Mono dim style={{ fontSize: 11.5 }}>{it.citation}</Mono>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}

function CoverageTab() {
  const { m, revs, cats } = useMemo(buildCoverage, []);
  const [sel, setSel] = useState(null);
  const labelW = 132;

  return (
    <div style={{ padding: "28px 32px 48px", animation: "fadeIn 200ms ease" }}>
      <div style={{ maxWidth: 1040, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 8, flexWrap: "wrap", gap: 16 }}>
          <div>
            <h2 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 28, margin: 0, letterSpacing: "0.01em" }}>Pattern Coverage</h2>
            <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, fontWeight: 300, maxWidth: 560 }}>
              Which review dimensions each reviewer actually covers. Deeper green = reviewed more often. Click a cell to read the evidence.
            </p>
          </div>
          {/* legend */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Mono dim style={{ fontSize: 10 }}>none</Mono>
            <div style={{ display: "flex", gap: 2 }}>
              {[0, 1, 2, 3].map((n) => (
                <div key={n} style={{ width: 22, height: 14, background: coverageStep(n).fill, border: `1px solid ${coverageStep(n).border}`, borderRadius: 2 }} />
              ))}
            </div>
            <Mono dim style={{ fontSize: 10 }}>reviewed</Mono>
          </div>
        </div>

        <div style={{
          background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--border-radius)",
          padding: "20px 22px 22px", marginTop: 20, overflowX: "auto",
        }}>
          <div style={{ minWidth: 640 }}>
            {/* header row of category labels */}
            <div style={{
              display: "grid",
              gridTemplateColumns: `${labelW}px repeat(${cats.length}, minmax(54px, 1fr))`,
              gap: 4, alignItems: "end", height: 84, marginBottom: 4,
            }}>
              <div />
              {cats.map(c => (
                <div key={c} style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", height: "100%" }}>
                  <span style={{
                    fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-dim)",
                    transform: "rotate(-48deg)", transformOrigin: "left bottom",
                    whiteSpace: "nowrap", display: "inline-block",
                  }}>{c}</span>
                </div>
              ))}
            </div>

            {/* one row per reviewer */}
            {revs.map(r => (
              <div key={r} style={{
                display: "grid",
                gridTemplateColumns: `${labelW}px repeat(${cats.length}, minmax(54px, 1fr))`,
                gap: 4, marginBottom: 4, alignItems: "center",
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 12 }}>
                  <Mono style={{ fontSize: 13 }}>{r}</Mono>
                </div>
                {cats.map(c => {
                  const cell = m[r][c];
                  return (
                    <CoverageCell key={c} data={cell}
                      label={`${r} · ${c}`}
                      onClick={() => setSel({ reviewer: r, category: c, cell })} />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <CoverageDrawer payload={sel} onClose={() => setSel(null)} />
    </div>
  );
}

window.CoverageTab = CoverageTab;
