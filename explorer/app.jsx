// app.jsx — shell: top bar + tab nav + mount

const TABS = [
  { id: "pipeline",     label: "Maturity Pipeline",     Comp: () => <PipelineTab /> },
  { id: "coverage",     label: "Pattern Coverage",      Comp: () => <CoverageTab /> },
  { id: "gaps",         label: "Team Gaps",             Comp: () => <GapsTab /> },
  { id: "fingerprints", label: "Reviewer Fingerprints", Comp: () => <FingerprintsTab /> },
  { id: "profiles",     label: "Author Profiles",       Comp: () => <ProfilesTab />, private: true },
];

function PrivateBadge() {
  return (
    <span style={{
      fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 500,
      textTransform: "uppercase", letterSpacing: "0.07em",
      color: "#15803d", background: "rgba(22,163,74,0.10)",
      border: "1px solid rgba(22,163,74,0.20)", borderRadius: "var(--border-radius)",
      padding: "1px 5px", lineHeight: 1.3, marginLeft: 7,
    }}>private</span>
  );
}

function TopBar() {
  return (
    <header style={{
      display: "flex", alignItems: "baseline", gap: 18,
      padding: "16px 32px 14px", borderBottom: "1px solid var(--border)",
      background: "var(--bg)", flexWrap: "wrap",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
        <div style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 26, letterSpacing: "0.005em", lineHeight: 1 }}>
          tricorder
        </div>
        <WipMark />
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 14, flexWrap: "wrap", marginLeft: "auto" }}>
        <Mono dim style={{ fontSize: 13, whiteSpace: "nowrap" }}>{DATA.repo}</Mono>
        <span style={{ color: "var(--border)" }}>·</span>
        <Mono dim style={{ fontSize: 13, whiteSpace: "nowrap" }}>{DATA.window}</Mono>
        <span style={{ color: "var(--border)" }}>·</span>
        <Mono dim style={{ fontSize: 13, whiteSpace: "nowrap" }}>{DATA.pr_count} PRs</Mono>
        <span style={{ color: "var(--border)" }}>·</span>
        <a href={REPO_URL} target="_blank" rel="noopener" style={{
          fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--accent)",
          textDecoration: "none", whiteSpace: "nowrap", borderBottom: "1px solid transparent",
        }}
          onMouseEnter={(e) => e.currentTarget.style.borderBottomColor = "var(--accent)"}
          onMouseLeave={(e) => e.currentTarget.style.borderBottomColor = "transparent"}
        >GitHub ↗</a>
      </div>
    </header>
  );
}

function TabBar({ active, onSelect }) {
  return (
    <nav style={{
      display: "flex", gap: 4, padding: "0 24px", borderBottom: "1px solid var(--border)",
      background: "var(--bg)", overflowX: "auto", position: "sticky", top: 0, zIndex: 20,
    }}>
      {TABS.map(t => {
        const on = t.id === active;
        return (
          <button key={t.id} onClick={() => onSelect(t.id)}
            style={{
              all: "unset", cursor: "pointer", whiteSpace: "nowrap",
              display: "inline-flex", alignItems: "center",
              fontFamily: "var(--font-mono)", fontSize: 12, textTransform: "uppercase",
              letterSpacing: "0.07em",
              color: on ? "var(--text)" : "var(--text-dim)",
              padding: "14px 14px 12px",
              borderBottom: `3px solid ${on ? "var(--accent)" : "transparent"}`,
              transition: "color 120ms ease, border-color 120ms ease",
            }}
            onMouseEnter={(e) => { if (!on) e.currentTarget.style.color = "var(--text)"; }}
            onMouseLeave={(e) => { if (!on) e.currentTarget.style.color = "var(--text-dim)"; }}
          >{t.label}{t.private && <PrivateBadge />}</button>
        );
      })}
    </nav>
  );
}

function App() {
  const initial = (window.location.hash || "").replace("#", "");
  const [active, setActive] = useState(TABS.some(t => t.id === initial) ? initial : "pipeline");

  useEffect(() => { window.location.hash = active; }, [active]);

  const tab = TABS.find(t => t.id === active) || TABS[0];
  const needsFullHeight = active === "pipeline";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", minHeight: 0 }}>
      <TopBar />
      <TabBar active={active} onSelect={setActive} />
      <main style={{ flex: 1, minHeight: 0, overflowY: needsFullHeight ? "hidden" : "auto", display: "flex", flexDirection: "column" }}>
        <tab.Comp />
      </main>
      <Onboarding active={active} setActive={setActive} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
