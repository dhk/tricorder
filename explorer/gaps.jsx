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
    <div style={{ padding: "12px 0", borderBottom: "1px solid var(--border-light)" }}>
      <div style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 14, lineHeight: 1.35, color: "var(--text)" }}>{g.area}</div>
      <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
        <Tag group={tagGroup} size="xs" style={{ flexShrink: 0, marginTop: 1 }}>{g.gap_type.replace("_", " ")}</Tag>
        {g.standard_citation && (
          <Mono dim style={{ fontSize: 11, lineHeight: 1.45, flex: 1, minWidth: 160 }}>§ {g.standard_citation}</Mono>
        )}
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
            fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 16, margin: 0,
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

// Oversight density: computed from the harvested record, no model involved.
// Where human review attention lands per lens axis, and where it does not.
function OversightPanel() {
  const ov = DATA.oversight;
  if (!ov || !ov.summary) return null;
  const s = ov.summary;
  const axes = (ov.per_axis || []).filter(a => a.prs_touching !== null && a.prs_touching !== undefined && a.prs_touching > 0);
  const pct = (v) => v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
  const th = { fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 400, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", textAlign: "left", padding: "8px 12px", borderBottom: "1px solid var(--border)" };
  const td = { fontSize: 14, color: "var(--text-muted)", padding: "10px 12px", borderBottom: "1px solid var(--border-light)", verticalAlign: "top" };
  const num = { ...td, fontFamily: "var(--font-mono)", textAlign: "right", fontVariantNumeric: "tabular-nums" };
  return (
    <section style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "20px 20px 8px", marginBottom: 18 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <h3 style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 16, margin: 0 }}>Oversight density</h3>
        <Mono dim style={{ fontSize: 11 }}>computed from the review record · no model involved</Mono>
      </div>
      <p style={{ margin: "6px 0 12px", fontSize: 14, lineHeight: 1.6, color: "var(--text-muted)", maxWidth: 760 }}>
        In agentic development, review is where human oversight concentrates. This is where it landed in the window:
        <strong style={{ color: "var(--text)" }}> {s.prs_without_human_engagement} of {s.prs} PRs</strong> merged with no human engagement at all, and
        <strong style={{ color: "var(--text)" }}> {s.silent_approvals} of {s.approvals} approvals</strong> carried no comment.
        {s.inline_comments_by_bots !== undefined && (
          <span> Inline comments: <strong style={{ color: "var(--text)" }}>{s.inline_comments_by_human_reviewers}</strong> by human reviewers,
          <strong style={{ color: "var(--text)" }}> {s.inline_comments_by_bots}</strong> by bots, {s.inline_comments_by_pr_authors} by authors replying on their own PRs.
          On <strong style={{ color: "var(--text)" }}>{s.prs_bot_only}</strong> PRs a bot commented and no human reviewer did.</span>
        )}
        {s.prs_with_changed_files ? "" : " Changed-file lists are missing from this cache, so per-axis touch counts are unavailable."}
      </p>
      {axes.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr>
              <th style={th}>Axis</th><th style={th}>Stakes</th>
              <th style={{ ...th, textAlign: "right" }}>PRs touching</th>
              <th style={{ ...th, textAlign: "right" }}>Human reviewer</th>
              <th style={{ ...th, textAlign: "right" }}>Bot only</th>
              <th style={{ ...th, textAlign: "right" }}>Nobody</th>
              <th style={{ ...th, textAlign: "right" }}>Silent share</th>
              <th style={{ ...th, textAlign: "right" }}>Comments</th>
              <th style={{ ...th, textAlign: "right" }}>Reviewers</th>
            </tr></thead>
            <tbody>
              {axes.map(a => (
                <tr key={a.axis}>
                  <td style={{ ...td, fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--text)" }}>{a.axis}</td>
                  <td style={td}>{a.high_stakes ? <Tag group="team" size="xs">high</Tag> : <Mono dim style={{ fontSize: 11 }}>—</Mono>}</td>
                  <td style={num}>{a.prs_touching}</td>
                  <td style={num}>{a.engagement ? (a.engagement.human_and_bot + a.engagement.human_only) : "—"}</td>
                  <td style={num}>{a.engagement ? a.engagement.bot_only : "—"}</td>
                  <td style={num}>{a.engagement ? a.engagement.nobody : "—"}</td>
                  <td style={{ ...num, color: (a.silent_share || 0) >= 0.5 && a.high_stakes ? "var(--accent-orange)" : "var(--text-muted)" }}>{pct(a.silent_share)}</td>
                  <td style={num}>{a.comments}</td>
                  <td style={num}>{a.distinct_reviewers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ margin: "10px 0 8px", fontSize: 12.5, lineHeight: 1.5, color: "var(--text-dim)" }}>
        Silent share: of the PRs that changed files under this axis, the fraction that received no inline comment there from any human. A high-stakes axis with a high silent share is the oversight gap to raise first. Per-reviewer silent-approval shares are on the Reviewer Fingerprints tab.
      </p>
    </section>
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
        <OversightPanel />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 18, alignItems: "start" }}>
          {GAP_PANELS.map(p => <GapPanel key={p.key} panel={p} items={grouped[p.key]} />)}
        </div>
      </div>
    </div>
  );
}

window.GapsTab = GapsTab;
