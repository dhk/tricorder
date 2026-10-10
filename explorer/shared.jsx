// shared.jsx — design-system primitives shared across tabs
const { useState, useEffect, useRef, useMemo } = React;

const DATA = window.TRICORDER_DATA;

// --- colour families per content-type group -------------------------------
// DHK design system semantic accents, read from the tokens in index.html:
//   patterns -> cobalt (--accent)   tools/reviewers -> purple (--accent-purple)
//   data/analysis -> teal (--accent-teal)   team/gaps -> orange (--accent-orange)
// Tag tint = 10-12% alpha of the accent; text = the accent at full strength.
const tint = (v, pct) => `color-mix(in srgb, var(${v}) ${pct}%, transparent)`;
const GROUP_COLORS = {
  pattern: { fg: "var(--accent)",        bg: tint("--accent", 10),        bd: tint("--accent", 30) },
  tool:    { fg: "var(--accent-purple)", bg: tint("--accent-purple", 10), bd: tint("--accent-purple", 30) },
  data:    { fg: "var(--accent-teal)",   bg: tint("--accent-teal", 10),   bd: tint("--accent-teal", 30) },
  team:    { fg: "var(--accent-orange)", bg: tint("--accent-orange", 10), bd: tint("--accent-orange", 28) },
};

// Resolved token value, for SVG chart props (Recharts) that need a literal colour.
const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function groupForCategory(cat) {
  return DATA.CATEGORY_GROUP[cat] || "pattern";
}

// A tag/label chip. DM Mono, uppercase, rectangular (no pills).
function Tag({ children, group = "pattern", size = "sm", style }) {
  const c = GROUP_COLORS[group] || GROUP_COLORS.pattern;
  // one tag size in the system: mono 11px, 0.08em; padding is the only variant
  const sizes = {
    xs: { fontSize: 11, padding: "2px 6px", letterSpacing: "0.08em" },
    sm: { fontSize: 11, padding: "2px 7px", letterSpacing: "0.08em" },
    md: { fontSize: 11, padding: "3px 9px", letterSpacing: "0.08em" },
  };
  return (
    <span style={{
      fontFamily: "var(--font-mono)",
      textTransform: "uppercase",
      color: c.fg,
      background: c.bg,
      border: `1px solid ${c.bd}`,
      borderRadius: "var(--radius)",
      whiteSpace: "nowrap",
      lineHeight: 1.3,
      ...sizes[size],
      ...style,
    }}>{children}</span>
  );
}

// Maturity stage -> tone. Pipeline progresses judgment -> deterministic.
const MATURITY = {
  judgment:      { label: "judgment",      group: "team"    },
  guidance:      { label: "guidance",      group: "data"    },
  convention:    { label: "convention",    group: "tool"    },
  rule:          { label: "rule",          group: "pattern" },
  deterministic: { label: "deterministic", group: "pattern" },
};
const MATURITY_ORDER = ["judgment", "guidance", "convention", "rule", "deterministic"];

// frequency words -> numeric (for radar + sorting)
const FREQ_NUM = { always: 100, often: 72, sometimes: 46, rarely: 22, never: 0 };
function freqToNum(f) { return typeof f === "number" ? f : (FREQ_NUM[f] ?? 0); }

// A small monospace key/label used on axes and metadata.
function Mono({ children, dim, style }) {
  return (
    <span style={{
      fontFamily: "var(--font-mono)",
      color: dim ? "var(--text-dim)" : "var(--text)",
      ...style,
    }}>{children}</span>
  );
}

// Section label inside a card: mono, uppercase, 11px (design-system "meta").
function CardHeading({ children, style }) {
  return (
    <div style={{
      fontFamily: "var(--font-mono)",
      fontWeight: 400,
      textTransform: "uppercase",
      letterSpacing: "0.1em",
      fontSize: 11,
      color: "var(--text-dim)",
      ...style,
    }}>{children}</div>
  );
}

// Two-part explainer at the top of every data tab: how to read it, what to do with it.
// Note strip on --bg2 with mono labels (design-system "prompt block" idiom).
function TabExplainer({ read, act }) {
  const cell = (label, text) => (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
      <Mono dim style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</Mono>
      <p style={{ margin: 0, fontFamily: "var(--font-sans)", fontSize: 14, lineHeight: 1.6, color: "var(--text-muted)" }}>{text}</p>
    </div>
  );
  return (
    <section aria-label="How to read this tab" style={{
      display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px 32px",
      background: "var(--bg2)", border: "1px solid var(--border)", borderLeft: "2px solid var(--accent)",
      borderRadius: "var(--radius)", padding: "14px 20px 16px", marginBottom: 20,
    }}>
      {cell("How to read it", read)}
      {cell("What to do with it", act)}
    </section>
  );
}

Object.assign(window, {
  DATA, GROUP_COLORS, token, groupForCategory, Tag, Mono, CardHeading, TabExplainer,
  MATURITY, MATURITY_ORDER, FREQ_NUM, freqToNum,
  useState, useEffect, useRef, useMemo,
});
