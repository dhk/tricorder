// heatmap.jsx — Tab 1: Pattern Heatmap
// Reviewers (Y) × 15 categories (X). Cell fill = comment frequency.
// Click a cell -> drawer with quoted evidence.

function buildMatrix() {
  const cats = DATA.CATEGORIES;
  const revs = DATA.reviewers.map(r => r.login);
  // map: reviewer -> category -> { count, items[] }
  const m = {};
  revs.forEach(r => { m[r] = {}; cats.forEach(c => { m[r][c] = { count: 0, items: [] }; }); });
  DATA.patterns.forEach(p => {
    if (!m[p.reviewer] || !m[p.reviewer][p.category]) return;
    const cell = m[p.reviewer][p.category];
    const ev = p.evidence || [];
    cell.count += ev.length;
    ev.forEach(e => cell.items.push({ ...e, signal: p.signal, category: p.category, citation: p.standard_citation }));
  });
  let max = 0;
  revs.forEach(r => cats.forEach(c => { if (m[r][c].count > max) max = m[r][c].count; }));
  return { m, revs, cats, max };
}

// white (#f9f8f6) -> solid accent green (#16a34a)
function cellFill(t) {
  if (t <= 0) return "#ffffff";
  const a = { r: 249, g: 248, b: 246 };
  const b = { r: 22, g: 163, b: 74 };
  const k = Math.pow(t, 0.78);
  const r = Math.round(a.r + (b.r - a.r) * k);
  const g = Math.round(a.g + (b.g - a.g) * k);
  const bl = Math.round(a.b + (b.b - a.b) * k);
  return `rgb(${r},${g},${bl})`;
}

function HeatmapCell({ data, t, label, onClick }) {
  const [hover, setHover] = useState(false);
  const active = data.count > 0;
  const textLight = t > 0.5;
  return (
    <button
      onClick={active ? onClick : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={active ? `${label} · ${data.count} comment${data.count > 1 ? "s" : ""}` : `${label} · none`}
      style={{
        all: "unset",
        position: "relative",
        height: 46,
        borderRadius: "var(--border-radius)",
        background: cellFill(t),
        border: `1px solid ${active ? "rgba(22,163,74,0.22)" : "var(--border)"}`,
        cursor: active ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: hover && active ? "0 0 0 2px var(--accent), 0 4px 10px rgba(22,163,74,0.22)" : "none",
        transition: "box-shadow 120ms ease, transform 120ms ease",
        transform: hover && active ? "translateY(-1px)" : "none",
        zIndex: hover && active ? 2 : 1,
      }}>
      {active && (
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: 12.5,
          fontWeight: 500,
          color: textLight ? "#fff" : "var(--text-dim)",
        }}>{data.count}</span>
      )}
    </button>
  );
}

function EvidenceDrawer({ payload, onClose }) {
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
              <Mono dim style={{ fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase" }}>Evidence</Mono>
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
            <Mono dim style={{ fontSize: 12 }}>{cell.count} comment{cell.count > 1 ? "s" : ""}</Mono>
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
                fontFamily: "var(--font-sans)", fontSize: 14.5, lineHeight: 1.55,
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

function HeatmapTab() {
  const { m, revs, cats, max } = useMemo(buildMatrix, []);
  const [sel, setSel] = useState(null);
  const labelW = 132;

  return (
    <div style={{ padding: "28px 32px 48px", animation: "fadeIn 200ms ease" }}>
      <div style={{ maxWidth: 1180, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 8, flexWrap: "wrap", gap: 16 }}>
          <div>
            <h2 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 28, margin: 0, letterSpacing: "0.01em" }}>Pattern Heatmap</h2>
            <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, maxWidth: 560 }}>
              Where each reviewer concentrates their attention. Darker cells = more review comments. Click any cell for the underlying evidence.
            </p>
          </div>
          {/* legend */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Mono dim style={{ fontSize: 11 }}>none</Mono>
            <div style={{ display: "flex", gap: 2 }}>
              {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
                <div key={i} style={{ width: 22, height: 14, background: cellFill(t), border: "1px solid var(--border)", borderRadius: 2 }} />
              ))}
            </div>
            <Mono dim style={{ fontSize: 11 }}>{max} max</Mono>
          </div>
        </div>

        <div style={{
          background: "#fff", border: "1px solid var(--border)", borderRadius: "var(--border-radius)",
          padding: "20px 22px 22px", marginTop: 20, overflowX: "auto",
        }}>
          <div style={{ minWidth: 720 }}>
            {/* header row of angled category labels */}
            <div style={{
              display: "grid",
              gridTemplateColumns: `${labelW}px repeat(${cats.length}, minmax(40px, 1fr))`,
              gap: 4, alignItems: "end", height: 96, marginBottom: 4,
            }}>
              <div />
              {cats.map(c => (
                <div key={c} style={{ display: "flex", justifyContent: "center", alignItems: "flex-end", height: "100%" }}>
                  <span style={{
                    fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
                    transform: "rotate(-52deg)", transformOrigin: "left bottom",
                    whiteSpace: "nowrap", display: "inline-block",
                    color: groupForCategory(c) === "pattern" ? GROUP_COLORS.pattern.fg : "var(--text-dim)",
                  }}>{c}</span>
                </div>
              ))}
            </div>

            {/* one row per reviewer */}
            {revs.map(r => (
              <div key={r} style={{
                display: "grid",
                gridTemplateColumns: `${labelW}px repeat(${cats.length}, minmax(40px, 1fr))`,
                gap: 4, marginBottom: 4, alignItems: "center",
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 12 }}>
                  <Mono style={{ fontSize: 13 }}>{r}</Mono>
                </div>
                {cats.map(c => {
                  const cell = m[r][c];
                  const t = max ? cell.count / max : 0;
                  return (
                    <HeatmapCell key={c} data={cell} t={t}
                      label={`${r} · ${c}`}
                      onClick={() => setSel({ reviewer: r, category: c, cell })} />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <EvidenceDrawer payload={sel} onClose={() => setSel(null)} />
    </div>
  );
}

window.HeatmapTab = HeatmapTab;
