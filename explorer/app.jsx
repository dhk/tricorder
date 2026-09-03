// app.jsx — shell: top bar + tab nav + mount

const TABS = [
  { id: "intro",        label: "Start Here",            Comp: ({ onSelect }) => <IntroTab onSelect={onSelect} /> },
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

function AboutModal({ onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 200,
        background: "rgba(10,10,9,0.35)",
        display: "flex", alignItems: "flex-start", justifyContent: "flex-end",
        padding: "60px 32px 0",
        animation: "fadeIn 120ms ease",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
          background: "var(--bg)", border: "1px solid var(--border)",
          borderRadius: 6, padding: "28px 32px 24px",
          width: 340, boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
          animation: "fadeIn 150ms ease",
        }}
      >
        {/* wordmark + version */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 12 }}>
          <div style={{
            fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 20,
            letterSpacing: "0.005em",
          }}>tricorder</div>
          {DATA.version && (
            <span style={{
              fontFamily: "var(--font-mono)", fontSize: 10.5,
              color: "var(--text-dim)", letterSpacing: "0.04em",
            }}>v{DATA.version}</span>
          )}
        </div>

        {/* one-liner */}
        <p style={{
          margin: "0 0 20px", fontSize: 14, lineHeight: 1.6,
          color: "var(--text)", fontFamily: "var(--font-sans)",
        }}>
          Reads a team's merged PR history and returns a structured map of what the team knows, what it misses, and what's ready to institutionalize.
        </p>

        {/* divider */}
        <div style={{ borderTop: "1px solid var(--border)", margin: "0 0 18px" }} />

        {/* contact */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[
            { label: "email",     value: "tricorder@dhk.io",  href: "mailto:tricorder@dhk.io" },
            { label: "portfolio", value: "www.dhk.io",        href: "https://www.dhk.io"      },
          ].map(({ label, value, href }) => (
            <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--text-dim)",
                textTransform: "uppercase", letterSpacing: "0.07em", minWidth: 62,
              }}>{label}</span>
              <a href={href} target={href.startsWith("http") ? "_blank" : undefined}
                rel="noopener"
                style={{
                  fontFamily: "var(--font-mono)", fontSize: 12.5,
                  color: "var(--accent)", textDecoration: "none",
                  borderBottom: "1px solid transparent", transition: "border-color 120ms",
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderBottomColor = "var(--accent)"}
                onMouseLeave={(e) => e.currentTarget.style.borderBottomColor = "transparent"}
              >{value}</a>
            </div>
          ))}
        </div>

        {/* close */}
        <button onClick={onClose} style={{
          all: "unset", cursor: "pointer", position: "absolute",
          top: 14, right: 16,
          fontFamily: "var(--font-mono)", fontSize: 18,
          color: "var(--text-dim)", lineHeight: 1,
        }}>×</button>
      </div>
    </div>
  );
}

function TopBar({ onAbout }) {
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
        <span style={{ color: "var(--border)" }}>·</span>
        <button onClick={onAbout} style={{
          all: "unset", cursor: "pointer",
          fontFamily: "var(--font-mono)", fontSize: 12.5,
          color: "var(--text-dim)", whiteSpace: "nowrap",
          borderBottom: "1px solid transparent", transition: "color 120ms, border-color 120ms",
        }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "var(--text)"; e.currentTarget.style.borderBottomColor = "var(--border)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-dim)"; e.currentTarget.style.borderBottomColor = "transparent"; }}
        >about</button>
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
          <button key={t.id} data-tab={t.id} onClick={() => onSelect(t.id)}
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
  const [active, setActive] = useState(TABS.some(t => t.id === initial) ? initial : "intro");
  const [showAbout, setShowAbout] = useState(false);

  useEffect(() => { window.location.hash = active; }, [active]);

  const tab = TABS.find(t => t.id === active) || TABS[0];
  const needsFullHeight = active === "pipeline";

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", minHeight: 0 }}>
      <TopBar onAbout={() => setShowAbout(true)} />
      <TabBar active={active} onSelect={setActive} />
      <main style={{ flex: 1, minHeight: 0, overflowY: needsFullHeight ? "hidden" : "auto", display: "flex", flexDirection: "column" }}>
        <tab.Comp onSelect={setActive} />
      </main>
      <Onboarding active={active} setActive={setActive} />
      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
