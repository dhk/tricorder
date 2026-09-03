// tour.jsx — onboarding: intro overlay + guided walkthrough + repo CTA
// Frames the explorer as an early work-in-progress and routes people to the repo.

const REPO_URL = "https://github.com/dhk/tricorder";
const TOUR_KEY = "tricorder_tour_seen_v1";

// Step 0 = intro card; steps 1..N anchor to a tab button; last = CTA card.
const TOUR_STEPS = [
  { kind: "intro" },
  { kind: "tab", tab: "pipeline",     title: "Maturity Pipeline",
    body: "Every recurring review pattern, ranked by how close it is to becoming an automatable rule. The two greener columns on the right are the ones ready to act on." },
  { kind: "tab", tab: "coverage",     title: "Pattern Coverage",
    body: "Which review dimensions each reviewer actually covers. Deeper green = reviewed more often. Click any cell to read the exact comments behind it." },
  { kind: "tab", tab: "gaps",         title: "Team Gaps",
    body: "Where the team is collectively blind — coverage holes, knowledge gaps, and risks no one is consistently catching, each with a concrete fix." },
  { kind: "tab", tab: "fingerprints", title: "Reviewer Fingerprints",
    body: "The shape of each reviewer's attention across the nine dimensions, plus their apparent blind spots and signal quality." },
  { kind: "tab", tab: "profiles",     title: "Author Profiles",
    body: "Private by default. Individual growth profiles only render when a run is generated with --visibility private." },
  { kind: "cta" },
];

function WipMark({ style }) {
  return (
    <span style={{
      fontFamily: "var(--font-mono)", fontSize: 9.5, fontWeight: 500,
      textTransform: "uppercase", letterSpacing: "0.08em",
      color: "var(--accent-orange)", background: "rgba(217,79,42,0.08)",
      border: "1px solid rgba(217,79,42,0.25)", borderRadius: "var(--border-radius)",
      padding: "2px 7px", lineHeight: 1.3, whiteSpace: "nowrap", ...style,
    }}>work in progress</span>
  );
}

function TourButton({ children, onClick, variant = "primary", style }) {
  const base = {
    all: "unset", cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: 12,
    textTransform: "uppercase", letterSpacing: "0.06em", padding: "9px 16px",
    borderRadius: "var(--border-radius)", textAlign: "center", lineHeight: 1,
    transition: "background 120ms ease, border-color 120ms ease, color 120ms ease",
  };
  const variants = {
    primary: { background: "var(--accent)", color: "#fff", border: "1px solid var(--accent)" },
    ghost:   { background: "transparent", color: "var(--text-dim)", border: "1px solid var(--border)" },
  };
  return (
    <a onClick={onClick} role="button" style={{ ...base, ...variants[variant], ...style }}>{children}</a>
  );
}

// Spotlight + tooltip anchored to a tab button.
function TabCoach({ step, idx, total, rect, onNext, onPrev, onSkip }) {
  if (!rect) return null;
  const pad = 6;
  const tipTop = rect.bottom + 14;
  const tipLeft = Math.max(16, Math.min(rect.left - 8, window.innerWidth - 360));
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 90 }}>
      {/* spotlight hole over the tab */}
      <div style={{
        position: "fixed",
        top: rect.top - pad, left: rect.left - pad,
        width: rect.width + pad * 2, height: rect.height + pad * 2,
        borderRadius: "var(--border-radius)",
        border: "1.5px solid var(--accent)",
        boxShadow: "0 0 0 9999px rgba(10,10,9,0.55)",
        pointerEvents: "none",
        transition: "all 220ms cubic-bezier(0.22,1,0.36,1)",
      }} />
      {/* tooltip */}
      <div style={{
        position: "fixed", top: tipTop, left: tipLeft, width: 332,
        background: "var(--bg)", border: "1px solid var(--border)",
        borderRadius: "var(--border-radius)", padding: "16px 18px 14px",
        boxShadow: "0 14px 34px rgba(10,10,9,0.18)",
        animation: "fadeIn 160ms ease",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <Mono dim style={{ fontSize: 10.5, letterSpacing: "0.07em" }}>{String(idx).padStart(2, "0")} / {String(total).padStart(2, "0")}</Mono>
          <a onClick={onSkip} style={{ all: "unset", cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Skip tour</a>
        </div>
        <div style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 21, lineHeight: 1.1, marginBottom: 7 }}>{step.title}</div>
        <p style={{ margin: 0, fontFamily: "var(--font-sans)", fontWeight: 300, fontSize: 14, lineHeight: 1.5, color: "var(--text-dim)" }}>{step.body}</p>
        <div style={{ display: "flex", gap: 8, marginTop: 14, justifyContent: "flex-end" }}>
          {idx > 1 && <TourButton variant="ghost" onClick={onPrev}>Back</TourButton>}
          <TourButton onClick={onNext}>{idx === total ? "Finish" : "Next"}</TourButton>
        </div>
      </div>
    </div>
  );
}

function CenterCard({ children }) {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 95, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,9,0.55)", animation: "fadeIn 180ms ease" }} />
      <div style={{
        position: "relative", width: "min(520px, 100%)", background: "var(--bg)",
        border: "1px solid var(--border)", borderRadius: "var(--border-radius)",
        padding: "34px 36px 30px", boxShadow: "0 24px 60px rgba(10,10,9,0.22)",
        animation: "cellPop 220ms cubic-bezier(0.22,1,0.36,1)",
      }}>{children}</div>
    </div>
  );
}

function Onboarding({ active, setActive }) {
  // -1 = inactive. 0..len-1 = step index.
  const [step, setStep] = useState(-1);
  const [rect, setRect] = useState(null);

  // auto-start once for first-time visitors; ?tour=1 forces it every time
  useEffect(() => {
    let forced = false;
    try { forced = new URLSearchParams(window.location.search).get("tour") === "1"; } catch (e) {}
    if (forced) { setStep(0); return; }
    let seen = false;
    try { seen = localStorage.getItem(TOUR_KEY) === "1"; } catch (e) {}
    if (!seen) setStep(0);
  }, []);

  // the Start Here tab can relaunch the tour
  useEffect(() => {
    const handler = () => setStep(0);
    window.addEventListener("tricorder:tour", handler);
    return () => window.removeEventListener("tricorder:tour", handler);
  }, []);

  const finish = () => {
    try { localStorage.setItem(TOUR_KEY, "1"); } catch (e) {}
    setStep(-1);
    setRect(null);
  };

  const cur = step >= 0 ? TOUR_STEPS[step] : null;

  // when on a tab step, switch to that tab and measure the nav button
  useEffect(() => {
    if (!cur || cur.kind !== "tab") { setRect(null); return; }
    if (active !== cur.tab) setActive(cur.tab);
    const measure = () => {
      // anchor by tab id, so adding or reordering tabs cannot desync the spotlight
      const el = document.querySelector(`nav button[data-tab="${cur.tab}"]`);
      if (el) setRect(el.getBoundingClientRect());
    };
    const raf = requestAnimationFrame(() => requestAnimationFrame(measure));
    window.addEventListener("resize", measure);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", measure); };
  }, [step, active]);

  const launcher = (
    <button onClick={() => setStep(0)} title="Take the tour" style={{
      all: "unset", cursor: "pointer", position: "fixed", right: 20, bottom: 20, zIndex: 60,
      width: 40, height: 40, borderRadius: "var(--border-radius)",
      background: "var(--bg)", border: "1px solid var(--border)",
      boxShadow: "0 6px 18px rgba(10,10,9,0.12)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 19, color: "var(--accent)",
    }}>?</button>
  );

  return (
    <React.Fragment>
      {step === -1 && launcher}

      {cur && cur.kind === "intro" && (
        <CenterCard>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <div style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 30, lineHeight: 1 }}>tricorder</div>
            <WipMark />
          </div>
          <p style={{ margin: "0 0 10px", fontFamily: "var(--font-sans)", fontWeight: 400, fontSize: 16, lineHeight: 1.55 }}>
            Code review is your team's most honest knowledge base — and most of it is buried in threads.
            tricorder reads those threads and returns a structured map of what your team knows, and what it doesn't.
          </p>
          <p style={{ margin: "0 0 22px", fontFamily: "var(--font-sans)", fontWeight: 300, fontSize: 14, lineHeight: 1.55, color: "var(--text-dim)" }}>
            This is a live, early prototype running on an analysis of <Mono style={{ fontSize: 13 }}>{DATA.repo}</Mono>. Take the 60-second tour, or start with the <Mono style={{ fontSize: 13 }}>Start Here</Mono> tab.
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <TourButton onClick={() => setStep(1)}>Take the tour</TourButton>
            <TourButton variant="ghost" onClick={finish}>Explore on my own</TourButton>
          </div>
        </CenterCard>
      )}

      {cur && cur.kind === "tab" && (
        <TabCoach step={cur} idx={step} total={TOUR_STEPS.length - 2} rect={rect}
          onNext={() => setStep(step + 1)}
          onPrev={() => setStep(step - 1)}
          onSkip={finish} />
      )}

      {cur && cur.kind === "cta" && (
        <CenterCard>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
            <div style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 26, lineHeight: 1 }}>Run it on your own repo</div>
          </div>
          <p style={{ margin: "0 0 10px", fontFamily: "var(--font-sans)", fontWeight: 400, fontSize: 15, lineHeight: 1.55 }}>
            tricorder is open and self-hostable. Point it at any GitHub repo, run the cost probe, harvest merged PRs, and synthesize — this explorer is what you get back.
          </p>
          <p style={{ margin: "0 0 22px", fontFamily: "var(--font-sans)", fontWeight: 300, fontSize: 13.5, lineHeight: 1.55, color: "var(--text-dim)" }}>
            Still early and experimental — the README and <Mono style={{ fontSize: 12.5 }}>SKILL.md</Mono> spec are the place to start.
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <TourButton onClick={() => window.open(REPO_URL, "_blank")} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              View the repo →
            </TourButton>
            <TourButton variant="ghost" onClick={finish}>Done</TourButton>
          </div>
        </CenterCard>
      )}
    </React.Fragment>
  );
}

window.Onboarding = Onboarding;
window.WipMark = WipMark;
window.REPO_URL = REPO_URL;
