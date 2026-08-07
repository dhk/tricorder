#!/usr/bin/env node
/**
 * tricorder is a Python package. This script runs automatically after
 * `npm install dhk/tricorder` and installs it via pip.
 */

const { execSync, spawnSync } = require("child_process");
const path = require("path");

const pkg = path.resolve(__dirname);

console.log("\ntricorder — Python package installer");
console.log("─────────────────────────────────────");
console.log("  NOTICE: npm postinstall will invoke pip install -e.");
console.log("  This modifies the Python environment selected by pip3/pip.");
console.log("  For isolation, cancel and follow HOWTO.md's virtualenv install.\n");

// Detect pip
function findPip() {
  for (const cmd of ["pip3", "pip"]) {
    try {
      const r = spawnSync(cmd, ["--version"], { encoding: "utf8" });
      if (r.status === 0) return cmd;
    } catch {}
  }
  return null;
}

const pip = findPip();

if (!pip) {
  console.error(`
  ✗  pip not found.

  tricorder requires Python 3.9+ and pip. Install Python from:
    https://python.org/downloads/

  Then install tricorder directly:
    pip install git+https://github.com/dhk/tricorder.git
`);
  process.exit(0); // soft-fail — don't break npm install
}

console.log(`  pip: ${pip}`);
console.log(`  Installing from: ${pkg}\n`);

const result = spawnSync(pip, ["install", "-e", pkg], {
  stdio: "inherit",
  encoding: "utf8",
});

if (result.status === 0) {
  console.log(`
  ✓ tricorder installed.

  Usage:
    tricorder make-it-so           # run the full pipeline
    tricorder discover             # scan this repo (no credentials needed)
    tricorder --help               # all commands
`);
} else {
  console.error(`
  ✗  pip install failed (exit ${result.status}).

  Try manually:
    pip install git+https://github.com/dhk/tricorder.git
`);
  process.exit(0); // still soft-fail
}
