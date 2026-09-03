// intro.jsx — Tab 0: Start Here (orientation)
// What this is, what it does, how to read the other tabs, and the way back to the repo.

const INTRO_PIPELINE = [
  { n: "01", title: "Harvest",
    body: "Pull every merged PR in the window from the GitHub API — description, reviews, inline comments — into a local cache." },
  { n: "02", title: "Extract",
    body: "One model pass per PR turns review threads into named patterns, each tagged with a category, a maturity level, and the quoted comment it came from." },
  { n: "03", title: "Profile",
    body: "Per reviewer: what they consistently catch and apparently miss. Per author: strengths, growth areas, and trajectory over time." },
  { n: "04", title: "Map gaps",
    body: "Across the whole record: where the team is strong, where coverage is thin, and which patterns are ready to become tooling." },
];

const INTRO_READ_GUIDE = [
  { tab: "pipeline", label: "Maturity Pipeline", lead: "Start here for action.",
    body: "Columns run left to right from judgment to deterministic. The two green-washed columns on the right hold patterns already consistent enough to become a lint rule or a CI gate." },
  { tab: "coverage", label: "Pattern Coverage", lead: "Who reviews for what.",
    body: "Rows are reviewers, columns are the review dimensions. Deeper green means that reviewer raises it more often. Click any cell to read the quoted comments behind it." },
  { tab: "gaps", label: "Team Gaps", lead: "What nobody is catching.",
    body: "Three panels — coverage gaps, knowledge gaps, blind spots — most critical first. Each names the standard it maps to and a concrete fix." },
  { tab: "fingerprints", label: "Reviewer Fingerprints", lead: "The shape of each reviewer's attention.",
    body: "A radar over the dimensions, plus focus areas, apparent blind spots, and a signal-quality grade that says how far to trust the fingerprint." },
  { tab: "profiles", label: "Author Profiles", lead: "Individual growth, kept private.", private: true,
    body: "Strengths, persistent growth areas, and a support recommendation per author. Rendered only when the run was generated with private visibility." },
];

const INTRO_MATURITY_DEFS = {
  judgment:      "a reviewer noticed it once",
  guidance:      "written down somewhere",
  convention:    "the team does it consistently",
  rule:          "a documented requirement",
  deterministic: "a tool enforces it",
};

const INTRO_COLOR_LEGEND = [
  { group: "pattern", label: "patterns" },
  { group: "tool",    label: "reviewers · tools" },
  { group: "data",    label: "data · analysis" },
  { group: "team",    label: "team · gaps" },
];

function IntroCard({ title, children, style }) {
  return (
    <section style={{
      background: "#fff", border: "1px solid var(--border)",
      borderRadius: "var(--border-radius)", padding: "22px 24px 20px",
      ...style,
    }}>
      <h3 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 20, margin: "0 0 12px" }}>{title}</h3>
      {children}
    </section>
  );
}

function IntroProse({ children, dim, style }) {
  return (
    <p style={{
      margin: "0 0 10px", fontFamily: "var(--font-sans)",
      fontWeight: dim ? 300 : 400, fontSize: dim ? 14 : 15, lineHeight: 1.6,
      color: dim ? "var(--text-dim)" : "var(--text)", ...style,
    }}>{children}</p>
  );
}

function IntroLink({ href, children }) {
  return (
    <a href={href} target="_blank" rel="noopener" style={{
      fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--accent)",
      textDecoration: "none", borderBottom: "1px solid transparent", transition: "border-color 120ms",
    }}
      onMouseEnter={(e) => e.currentTarget.style.borderBottomColor = "var(--accent)"}
      onMouseLeave={(e) => e.currentTarget.style.borderBottomColor = "transparent"}
    >{children}</a>
  );
}

function IntroStat({ label, value, hint }) {
  if (value === undefined || value === null || value === "") return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 0 }}>
      <Mono dim style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.07em" }}>{label}</Mono>
      <Mono style={{ fontSize: 14, overflowWrap: "anywhere" }}>{value}</Mono>
      {hint && (
        <span style={{
          fontFamily: "var(--font-sans)", fontWeight: 300, fontSize: 12,
          lineHeight: 1.4, color: "var(--text-dim)", marginTop: 2,
        }}>{hint}</span>
      )}
    </div>
  );
}

const VISIBILITY_HINT = {
  private: "What the run includes, not who can see it: per-person author profiles are kept.",
  team:    "What the run includes, not who can see it: per-person author profiles are left out.",
  public:  "What the run includes, not who can see it: author profiles left out. Not an anonymization guarantee.",
  demo:    "A demo render: names replaced by aliases from a name map.",
};

function lensHint(lens) {
  if (!lens || !lens.name) return undefined;
  return lens.status === "validated"
    ? "The rubric this run was read through. Validated: it has passed a production-repo evaluation."
    : "The rubric this run was read through: which standards can be cited and which review dimensions count. Experimental: not yet validated on a production repo.";
}

function IntroTab({ onSelect }) {
  const contributors = Array.isArray(DATA.contributors) ? DATA.contributors.length : undefined;
  const dims = Array.isArray(DATA.CATEGORIES) ? DATA.CATEGORIES.length : undefined;

  const go = (tab) => (e) => { e.preventDefault(); if (onSelect) onSelect(tab); };
  const startTour = () => window.dispatchEvent(new Event("tricorder:tour"));

  return (
    <div style={{ padding: "28px 32px 56px", animation: "fadeIn 200ms ease" }}>
      <div style={{ maxWidth: 980, margin: "0 auto" }}>

        {/* header */}
        <div style={{ marginBottom: 22 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h2 style={{ fontFamily: "var(--font-cond)", fontWeight: 700, fontSize: 28, margin: 0 }}>Start here</h2>
            <WipMark />
          </div>
          <p style={{ margin: "4px 0 0", color: "var(--text-dim)", fontSize: 14.5, maxWidth: 640 }}>
            An orientation for first-time readers. Everything else in this explorer is derived from one analysis run, summarized below.
          </p>
        </div>

        {/* run summary */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: "16px 28px",
          padding: "16px 20px", marginBottom: 22,
          background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--border-radius)",
        }}>
          <IntroStat label="repository" value={DATA.repo}
            hint="The GitHub repository whose merged PRs were read." />
          <IntroStat label="window" value={DATA.window}
            hint="Merge dates of the PRs in this run. Nothing outside it was read." />
          <IntroStat label="merged PRs" value={DATA.pr_count}
            hint="PRs merged in the window and pulled into the local cache." />
          <IntroStat label="with reviews" value={DATA.prs_with_reviews}
            hint="Of those, PRs with at least one review or inline comment. Only these carry signal." />
          <IntroStat label="contributors" value={contributors}
            hint="Distinct people who authored or reviewed in the window." />
          <IntroStat label="dimensions" value={dims}
            hint="Review categories used in the coverage grid and radar. Set by the lens." />
          <IntroStat label="visibility" value={DATA.visibility}
            hint={VISIBILITY_HINT[DATA.visibility] || "What the run includes, not who can see it."} />
          <IntroStat label="lens" value={DATA.lens && DATA.lens.name ? `${DATA.lens.name} v${DATA.lens.version || 1} · ${DATA.lens.status || "experimental"}` : undefined}
            hint={lensHint(DATA.lens)} />
          <IntroStat label="tricorder version" value={DATA.version ? `v${DATA.version}` : undefined}
            hint="The build of tricorder that produced this data. Prompts and lenses change between builds, so two runs compare only at the same version." />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 18, alignItems: "start" }}>

          {/* what's this about */}
          <IntroCard title="What is this about?">
            <IntroProse>
              Code review is a team's most honest knowledge base. Every "please add a test for the empty case" and
              "this belongs in the service layer" is a standard the team actually holds, stated at the moment it mattered.
              Almost all of it is buried in closed PR threads.
            </IntroProse>
            <IntroProse dim style={{ margin: 0 }}>
              tricorder reads those threads for a repository and returns a structured map of three things:
              what the team knows, what it misses, and what is consistent enough to stop relying on people to remember.
            </IntroProse>
          </IntroCard>

          {/* what does it do */}
          <IntroCard title="What does it do?">
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {INTRO_PIPELINE.map(s => (
                <div key={s.n} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <Mono dim style={{ fontSize: 11, marginTop: 4, flexShrink: 0 }}>{s.n}</Mono>
                  <div>
                    <div style={{ fontFamily: "var(--font-cond)", fontWeight: 600, fontSize: 16, lineHeight: 1.2 }}>{s.title}</div>
                    <div style={{ color: "var(--text-dim)", fontSize: 13.5, fontWeight: 300, lineHeight: 1.5, marginTop: 2 }}>{s.body}</div>
                  </div>
                </div>
              ))}
            </div>
            <IntroProse dim style={{ margin: "14px 0 0", fontSize: 13 }}>
              The output is this explorer plus a Markdown report. Nothing here was written by hand.
            </IntroProse>
          </IntroCard>
        </div>

        {/* how to read it */}
        <IntroCard title="How to read it" style={{ marginTop: 18 }}>
          <IntroProse dim>
            The tabs are ordered by how actionable they are. Read them left to right the first time.
          </IntroProse>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {INTRO_READ_GUIDE.map((g, i) => (
              <div key={g.tab} style={{
                display: "grid", gridTemplateColumns: "220px 1fr", gap: 16, alignItems: "baseline",
                padding: "12px 0", borderTop: i === 0 ? "1px solid var(--border)" : "none",
                borderBottom: "1px solid var(--border)",
              }}>
                <div>
                  <a href={`#${g.tab}`} onClick={go(g.tab)} style={{
                    fontFamily: "var(--font-mono)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.07em",
                    color: "var(--text)", textDecoration: "none", borderBottom: "1px solid var(--border)",
                  }}>{g.label}</a>
                  {g.private && <PrivateBadge />}
                </div>
                <div>
                  <span style={{ fontFamily: "var(--font-sans)", fontWeight: 500, fontSize: 14 }}>{g.lead} </span>
                  <span style={{ color: "var(--text-dim)", fontSize: 13.5, fontWeight: 300, lineHeight: 1.5 }}>{g.body}</span>
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: 24, marginTop: 20 }}>
            {/* maturity ladder */}
            <div>
              <CardHeading style={{ marginBottom: 10 }}>Maturity ladder</CardHeading>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {MATURITY_ORDER.map(m => (
                  <div key={m} style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                    <Tag group={MATURITY[m].group} style={{ minWidth: 104, textAlign: "center" }}>{MATURITY[m].label}</Tag>
                    <span style={{ color: "var(--text-dim)", fontSize: 13, fontWeight: 300 }}>{INTRO_MATURITY_DEFS[m]}</span>
                  </div>
                ))}
              </div>
              <IntroProse dim style={{ margin: "10px 0 0", fontSize: 12.5 }}>
                Every pattern sits on one rung. The point of the pipeline is to find the ones ready to move right.
              </IntroProse>
            </div>

            {/* gap types + colours */}
            <div>
              <CardHeading style={{ marginBottom: 10 }}>Gap types</CardHeading>
              <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
                {[
                  { g: "data",    t: "coverage gap",  d: "a standard exists but is not enforced everywhere" },
                  { g: "pattern", t: "knowledge gap", d: "reviewers raise it, but shallowly or inconsistently" },
                  { g: "team",    t: "blind spot",    d: "a named best practice no reviewer ever mentions" },
                ].map(x => (
                  <div key={x.t} style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                    <Tag group={x.g} style={{ minWidth: 104, textAlign: "center" }}>{x.t}</Tag>
                    <span style={{ color: "var(--text-dim)", fontSize: 13, fontWeight: 300 }}>{x.d}</span>
                  </div>
                ))}
              </div>
              <CardHeading style={{ margin: "16px 0 8px" }}>Colour</CardHeading>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {INTRO_COLOR_LEGEND.map(c => <Tag key={c.group} group={c.group}>{c.label}</Tag>)}
              </div>
            </div>
          </div>
        </IntroCard>

        {/* read with care + back to source */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 18, marginTop: 18, alignItems: "start" }}>
          <IntroCard title="Read with care">
            <ul style={{ margin: 0, padding: "0 0 0 18px", color: "var(--text-dim)", fontSize: 13.5, fontWeight: 300, lineHeight: 1.55 }}>
              <li style={{ marginBottom: 6 }}>Every finding is model-generated from review comments. The quotes are real; the interpretation is a model's. Treat standard citations as leads, not verdicts.</li>
              <li style={{ marginBottom: 6 }}>Signal scales with review volume. A reviewer with a handful of PRs gets a low signal-quality grade for a reason.</li>
              <li>{DATA.lens && DATA.lens.name
                ? `Findings are read through the ${DATA.lens.name} lens (${DATA.lens.status || "experimental"}). ${DATA.lens.status === "validated" ? "It has passed a production-repository evaluation." : "It has not yet passed a production-repository evaluation, so treat domain citations as leads."}`
                : "Findings are read through a discipline lens. This run predates lens tracking; on repositories that are not dbt/SQL projects, citations can drift off-domain."}</li>
            </ul>
          </IntroCard>

          <IntroCard title="Back to the source">
            <IntroProse dim>
              This explorer is one output of an open, self-hostable tool. The repository holds the code, the README, and the
              agent-facing spec that describes every phase in detail.
            </IntroProse>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 18 }}>
              {[
                { label: "repo",   value: REPO_URL.replace("https://", ""), href: REPO_URL },
                { label: "readme", value: "README.md",  href: `${REPO_URL}#readme` },
                { label: "spec",   value: "SKILL.md",   href: `${REPO_URL}/blob/main/SKILL.md` },
                { label: "how-to", value: "HOWTO.md",   href: `${REPO_URL}/blob/main/HOWTO.md` },
              ].map(({ label, value, href }) => (
                <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                  <Mono dim style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.07em", minWidth: 62 }}>{label}</Mono>
                  <IntroLink href={href}>{value}</IntroLink>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <TourButton onClick={go("pipeline")}>Open the pipeline →</TourButton>
              <TourButton variant="ghost" onClick={startTour}>Take the 60-second tour</TourButton>
            </div>
          </IntroCard>
        </div>

      </div>
    </div>
  );
}

window.IntroTab = IntroTab;
