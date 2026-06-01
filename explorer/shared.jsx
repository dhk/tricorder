// shared.jsx — design-system primitives shared across tabs
const { useState, useEffect, useRef, useMemo } = React;

const DATA = window.TRICORDER_DATA;

// --- color families per content-type group -------------------------------
// patterns -> green, tools/reviewers -> purple, data/analysis -> blue, team/gaps -> orange
const GROUP_COLORS = {
  pattern: { fg: "#16a34a", bg: "rgba(22,163,74,0.10)",  bd: "rgba(22,163,74,0.30)"  },
  tool:    { fg: "#7c5ce0", bg: "rgba(124,92,224,0.10)", bd: "rgba(124,92,224,0.30)" },
  data:    { fg: "#2970d6", bg: "rgba(41,112,214,0.10)", bd: "rgba(41,112,214,0.30)" },
  team:    { fg: "#d94f2a", bg: "rgba(217,79,42,0.10)",  bd: "rgba(217,79,42,0.28)"  },
};

function groupForCategory(cat) {
  return DATA.CATEGORY_GROUP[cat] || "pattern";
}

// A tag/label chip. DM Mono, uppercase, rectangular (no pills).
function Tag({ children, group = "pattern", size = "sm", style }) {
  const c = GROUP_COLORS[group] || GROUP_COLORS.pattern;
  const sizes = {
    sm: { fontSize: 10.5, padding: "2px 7px", letterSpacing: "0.06em" },
    md: { fontSize: 12,   padding: "3px 9px", letterSpacing: "0.05em" },
  };
  return (
    <span style={{
      fontFamily: "var(--font-mono)",
      textTransform: "uppercase",
      color: c.fg,
      background: c.bg,
      border: `1px solid ${c.bd}`,
      borderRadius: "var(--border-radius)",
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

// Section heading inside a card (Barlow Condensed).
function CardHeading({ children, style }) {
  return (
    <div style={{
      fontFamily: "var(--font-cond)",
      fontWeight: 600,
      textTransform: "uppercase",
      letterSpacing: "0.04em",
      fontSize: 13,
      color: "var(--text-dim)",
      ...style,
    }}>{children}</div>
  );
}

Object.assign(window, {
  DATA, GROUP_COLORS, groupForCategory, Tag, Mono, CardHeading,
  MATURITY, MATURITY_ORDER, FREQ_NUM, freqToNum,
  useState, useEffect, useRef, useMemo,
});
