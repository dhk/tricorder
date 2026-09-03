// profiles.jsx — Tab 3: Author Profiles

const TRAJECTORY = {
  improving:  { glyph: "↑", label: "improving",  color: "var(--accent)" },
  stable:     { glyph: "→", label: "stable",     color: "var(--text-dim)" },
  regressing: { glyph: "↓", label: "regressing", color: "var(--accent-orange)" },
};

function AuthorCard({ a }) {
  const [hover, setHover] = useState(false);
  const traj = TRAJECTORY[a.trajectory] || TRAJECTORY.stable;
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        background: "var(--bg)",
        border: "1px solid var(--border)",
        borderLeft: `3px solid ${hover ? "var(--accent)" : "transparent"}`,
        borderRadius: "var(--radius)",
        padding: "20px 22px 22px",
        transition: "color 0.15s, background 0.15s, border-color 0.15s",
      }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", paddingBottom: 16, borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 18, lineHeight: 1.2 }}>{a.login}</div>
        <Mono style={{ fontSize: 12.5, color: traj.color, display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ fontSize: 15 }}>{traj.glyph}</span>{traj.label}
        </Mono>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 18, marginTop: 16 }}>
        <div>
          <CardHeading style={{ color: "var(--accent)" }}>Strengths</CardHeading>
          <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
            {a.strengths.map((s, i) => (
              <li key={i} style={{ display: "flex", gap: 9, alignItems: "baseline" }}>
                <span style={{ color: "var(--accent)", fontSize: 13, lineHeight: 1.5 }}>▪</span>
                <div>
                  <span style={{ fontSize: 14.5, lineHeight: 1.45 }}>{s.area}</span>
                  <Mono dim style={{ fontSize: 11, marginLeft: 8, textTransform: "uppercase", letterSpacing: "0.04em" }}>{s.persistence}</Mono>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <CardHeading style={{ color: "var(--accent-orange)" }}>Growth Areas</CardHeading>
          <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "flex", flexDirection: "column", gap: 14 }}>
            {a.growth_areas.map((g, i) => (
              <li key={i} style={{ display: "flex", gap: 9, alignItems: "baseline" }}>
                <span style={{ color: "var(--accent-orange)", fontSize: 13, lineHeight: 1.5 }}>▪</span>
                <div>
                  <div>
                    <span style={{ fontSize: 14.5, lineHeight: 1.45 }}>{g.area}</span>
                    <Mono dim style={{ fontSize: 11, marginLeft: 8, textTransform: "uppercase", letterSpacing: "0.04em" }}>{g.persistence}</Mono>
                  </div>
                  <div style={{ marginTop: 5, display: "flex", gap: 6 }}>
                    <Mono dim style={{ fontSize: 11, fontWeight: 500, flexShrink: 0 }}>→ Support:</Mono>
                    <span style={{ color: "var(--text-dim)", fontSize: 13, lineHeight: 1.45, fontWeight: 400 }}>{g.support_recommendation}</span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function VisibilityNotice() {
  return (
    <div style={{
      maxWidth: 560, margin: "40px auto 0", background: "var(--bg2)",
      border: "1px solid var(--border)", borderRadius: "var(--radius)",
      padding: "28px 30px", textAlign: "center",
    }}>
      <div style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 16, marginBottom: 8 }}>
        Author profiles withheld
      </div>
      <p style={{ margin: 0, color: "var(--text-dim)", fontSize: 14, fontWeight: 400, lineHeight: 1.55 }}>
        Individual author profiles are omitted in team-visibility reports. Run with
        {" "}<Mono style={{ fontSize: 13, color: "var(--text)" }}>--visibility private</Mono>{" "}to include them.
      </p>
    </div>
  );
}

function ProfilesTab() {
  const isPrivate = DATA.visibility === "private";
  return (
    <div style={{ padding: "28px 32px 48px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: 28, margin: 0 }}>Author Profiles</h2>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, fontWeight: 400, maxWidth: 640 }}>
            What each contributor does well and where review feedback keeps recurring — with a concrete way to support each growth area.
          </p>
        </div>
        <TabExplainer
          read="One card per author: strengths that recur across their PRs, growth areas that persisted rather than appeared once, and a trajectory read from the chronological record. This describes the review feedback a person received in the window. It is not a performance rating and should not be used as one."
          act="Use the support line as the opener for a one-to-one, not as a verdict. A growth area marked consistent that also appears as a team blind spot is a team problem, not a personal one: fix the checklist, not the person. Keep this tab out of anything shared beyond the people in it." />
        {!isPrivate ? <VisibilityNotice /> : (
          <div style={{
            display: "grid", gap: 18,
            gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))",
          }}>
            {DATA.authors.map((a, i) => <AuthorCard key={i} a={a} />)}
          </div>
        )}
      </div>
    </div>
  );
}

window.ProfilesTab = ProfilesTab;
