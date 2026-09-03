// coverage.jsx — Tab: Pattern Coverage
// Reviewers (Y) × 9 categories (X).
//
// Cell fill comes from two sources, merged:
//   1. category_freq on reviewer fingerprints (0-100 score from Phase 2 synthesis)
//      — reliable signal for ALL reviewers regardless of pattern selection.
//   2. Evidence quotes from DATA.patterns — populates the click-through drawer.
//
// Using only patterns caused empty rows for reviewers whose patterns weren't
// selected in the top-20 (e.g. Spock reviewed 40 PRs but had low-count signals).

function buildCoverage() {
  const cats = DATA.CATEGORIES;
  const revs = DATA.reviewers.map(r => r.login);

  // Index reviewer fingerprints by login for O(1) lookup
  const freqIndex = {};
  DATA.reviewers.forEach(r => { freqIndex[r.login] = r.category_freq || {}; });

  // Build evidence items from patterns (for drawer)
  const evidenceIndex = {};  // reviewer → category → [{...}]
  revs.forEach(r => { evidenceIndex[r] = {}; cats.forEach(c => { evidenceIndex[r][c] = []; }); });
  DATA.patterns.forEach(p => {
    if (!evidenceIndex[p.reviewer] || !evidenceIndex[p.reviewer][p.category]) return;
    const ev = p.evidence || [];
    ev.forEach(e => evidenceIndex[p.reviewer][p.category].push(
      { ...e, signal: p.signal, category: p.category, citation: p.standard_citation }
    ));
  });

  // Merge: cell value is category_freq score (0-100); items come from pattern evidence
  const m = {};
  revs.forEach(r => {
    m[r] = {};
    cats.forEach(c => {
      const freq = freqIndex[r]?.[c] ?? 0;
      m[r][c] = { freq, items: evidenceIndex[r]?.[c] ?? [] };
    });
  });

  return { m, revs, cats };
}

// Map category_freq (0-100) → discrete shade level.
// Matches the original 4-level palette but driven by synthesis score.
function freqToLevel(freq) {
  if (freq <= 0)  return 0;
  if (freq < 30)  return 1;
  if (freq < 60)  return 2;
  return 3;
}

// Discrete coverage shades — not a continuous heat map.
function coverageStep(freq) {
  const level = freqToLevel(freq);
  if (level === 0) return { fill: "var(--bg)", border: "var(--border)", on: false, level: 0 };
  if (level === 1) return { fill: "rgba(43,80,232,0.12)", border: "rgba(43,80,232,0.22)", on: true, level: 1 };
  if (level === 2) return { fill: "rgba(43,80,232,0.30)", border: "rgba(43,80,232,0.34)", on: true, level: 2 };
  return { fill: "rgba(43,80,232,0.55)", border: "rgba(43,80,232,0.50)", on: true, level: 3 };
}

function CoverageCell({ data, label, onClick }) {
  const [hover, setHover] = useState(false);
  const step = coverageStep(data.freq);
  const hasEvidence = data.items && data.items.length > 0;
  // All active cells are clickable — drawer shows quotes if available,
  // otherwise shows the reviewer's fingerprint focus areas for this category.
  const clickable = step.on;
  return (
    <button
      onClick={clickable ? onClick : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={step.on
        ? `${label} — score ${data.freq} · click for detail`
        : `${label} — no coverage`}
      style={{
        all: "unset",
        position: "relative",
        height: 46,
        borderRadius: "var(--radius)",
        background: step.fill,
        border: `1px solid ${step.border}`,
        cursor: clickable ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        outline: hover && clickable ? "2px solid var(--accent)" : "none",
        outlineOffset: -2,
        transition: "color 0.15s, background 0.15s, border-color 0.15s",
        zIndex: hover && clickable ? 2 : 1,
      }}>
      {step.on && (
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          fontWeight: 500,
          color: step.level >= 3 ? "#fff" : "var(--text-dim)",
        }}>{data.freq}</span>
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

  // Find this reviewer's fingerprint focus areas relevant to this category
  const reviewerData = DATA.reviewers.find(r => r.login === reviewer);
  const catKeywords = {
    grain: ["grain","dedup","fan-out","fanout","partition"],
    naming: ["naming","convention","snake","prefix"],
    testing: ["test","fixture","uniqueness","not_null","primary key"],
    documentation: ["documentation","docs","description","readme","runbook"],
    style: ["style","cte","qualify","readability","formatting"],
    performance: ["performance","cost","scan","partition","cluster"],
    modeling: ["incremental","microbatch","materialization","model layer","staging","mart","scd","exposure"],
    schema: ["source freshness","schema change","breaking change","exposure","freshness"],
    "business-logic": ["spec","business logic","gtfs","derived field","conditional"],
  };
  const relevantFocus = reviewerData?.primary_focus_areas?.filter(f =>
    (catKeywords[category] || []).some(kw => f.area.toLowerCase().includes(kw))
  ) || [];

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50 }}>
      <div onClick={onClose}
        style={{ position: "absolute", inset: 0, background: "rgba(13,15,26,0.28)" }} />
      <aside style={{
        position: "absolute", top: 0, right: 0, height: "100%", width: "min(460px, 92vw)",
        background: "var(--bg)", borderLeft: "1px solid var(--border)",
        display: "flex", flexDirection: "column",
      }}>
        {/* header */}
        <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid var(--border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <Mono dim style={{ fontSize: 11, letterSpacing: "0.06em", textTransform: "uppercase" }}>Coverage detail</Mono>
              <div style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 26, lineHeight: 1.05, marginTop: 4 }}>
                {reviewer}
              </div>
            </div>
            <button onClick={onClose} style={{
              all: "unset", cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: 18,
              color: "var(--text-dim)", padding: "2px 8px", borderRadius: "var(--radius)",
              lineHeight: 1,
            }} title="Close (Esc)">✕</button>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "center" }}>
            <Tag group={grp} size="md">{category}</Tag>
            <Mono dim style={{ fontSize: 12 }}>focus score {cell.freq} / 100</Mono>
          </div>
        </div>

        <div style={{ overflowY: "auto", padding: "8px 24px 32px", flex: 1 }}>

          {/* fingerprint focus areas for this category */}
          {relevantFocus.length > 0 && (
            <div style={{ paddingTop: 18, paddingBottom: cell.items.length > 0 ? 0 : 8 }}>
              <CardHeading style={{ marginBottom: 10 }}>What this reviewer focuses on</CardHeading>
              {relevantFocus.map((f, i) => (
                <div key={i} style={{
                  padding: "11px 0",
                  borderBottom: i < relevantFocus.length - 1 ? "1px solid var(--border)" : "none",
                }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4 }}>
                    <Mono dim style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.07em" }}>{f.frequency}</Mono>
                  </div>
                  <div style={{ fontSize: 13.5, lineHeight: 1.5, color: "var(--text)" }}>{f.area}</div>
                </div>
              ))}
            </div>
          )}

          {/* divider between focus areas and evidence */}
          {relevantFocus.length > 0 && cell.items.length > 0 && (
            <div style={{ borderTop: "1px solid var(--border)", margin: "18px 0 4px" }}>
              <CardHeading style={{ marginTop: 14, marginBottom: 10 }}>Review quotes</CardHeading>
            </div>
          )}

          {/* pattern evidence quotes */}
          {cell.items.length > 0 ? cell.items.map((it, i) => (
            <div key={i} style={{
              padding: "16px 0",
              borderBottom: i < cell.items.length - 1 ? "1px solid var(--border)" : "none",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8, gap: 10 }}>
                <Mono style={{ fontSize: 12.5, color: "var(--accent-teal)" }}>{it.pr}</Mono>
                <Mono dim style={{ fontSize: 11 }}>{it.date}</Mono>
              </div>
              <div style={{
                fontFamily: "var(--font-sans)", fontWeight: 400, fontSize: 14.5, lineHeight: 1.55,
                color: "var(--text)", paddingLeft: 14, borderLeft: "2px solid var(--accent)",
              }}>"{it.quote}"</div>
              <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <Mono dim style={{ fontSize: 11 }}>on {it.author}'s PR</Mono>
                {it.citation && <><span style={{ color: "var(--border)" }}>·</span>
                <Mono dim style={{ fontSize: 11 }}>{it.citation}</Mono></>}
              </div>
            </div>
          )) : relevantFocus.length === 0 ? (
            <div style={{ paddingTop: 24, color: "var(--text-dim)", fontSize: 13.5, lineHeight: 1.6 }}>
              Focus score {cell.freq}/100 — no specific quotes for this category in the current pattern sample.
            </div>
          ) : null}

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
    <div style={{ padding: "28px 32px 48px" }}>
      <div style={{ maxWidth: 1040, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 8, flexWrap: "wrap", gap: 16 }}>
          <div>
            <h2 style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 28, margin: 0, letterSpacing: "0.01em" }}>Pattern Coverage</h2>
            <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, fontWeight: 400, maxWidth: 560 }}>
              Which review dimensions each reviewer actually covers. Deeper cobalt = reviewed more often. Click a cell to read the evidence.
            </p>
          </div>
          {/* legend */}
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Mono dim style={{ fontSize: 11 }}>none</Mono>
            <div style={{ display: "flex", gap: 2 }}>
              {[0, 1, 2, 3].map((n) => (
                <div key={n} style={{ width: 20, height: 3, background: coverageStep(n).on ? coverageStep(n).border : "var(--border)", borderRadius: 2 }} />
              ))}
            </div>
            <Mono dim style={{ fontSize: 11 }}>reviewed</Mono>
          </div>
        </div>

        <div style={{
          background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
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
                    fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-dim)",
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
