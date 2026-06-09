"""
tricorder config — show or initialize configuration.
"""

from __future__ import annotations

import sys
from pathlib import Path


def run(args: list[str]) -> int:
    import argparse
    from tricorder.config import load_config, write_default_config, repo_dir

    parser = argparse.ArgumentParser(
        prog="tricorder config",
        description="Show or initialize tricorder configuration.",
    )
    parser.add_argument("--init", action="store_true",
                        help="Write a starter config.yml to .tricorder/config.yml")
    parser.add_argument("--global", dest="global_", action="store_true",
                        help="Target ~/.tricorder/config.yml instead of ./.tricorder/config.yml")
    parser.add_argument("--tricorder-dir", default=None, metavar="DIR")

    parsed = parser.parse_args(args)

    if parsed.global_:
        config_path = Path.home() / ".tricorder" / "config.yml"
        tri_dir = config_path.parent
    else:
        tri_dir = Path(parsed.tricorder_dir).expanduser().resolve() if parsed.tricorder_dir \
            else Path.cwd() / ".tricorder"
        config_path = tri_dir / "config.yml"

    if parsed.init:
        if config_path.exists():
            print(f"Config already exists: {config_path}")
            print("Edit it directly, or delete it and re-run --init.")
            return 1
        write_default_config(config_path)
        print(f"✓ Created {config_path}")
        return 0

    # Show current config
    cfg = load_config(tri_dir)

    print(f"\ntricorder config")
    print(f"  Config file:  {config_path}{'  (not found)' if not config_path.exists() else ''}")
    print(f"  Global:       {Path.home() / '.tricorder' / 'config.yml'}")
    print()

    if not cfg:
        print("  No config found. Run: tricorder config --init")
        print()
        return 0

    _print_section("LLM", {
        "provider": cfg.get("llm", {}).get("provider", "(default: anthropic)"),
        "model":    cfg.get("llm", {}).get("model", "(default: provider default)"),
    })

    _print_section("Output", {
        "dir": cfg.get("output", {}).get("dir", "(default: --out flag)"),
    })

    deny = cfg.get("reviewer_deny") or []
    allow = cfg.get("reviewer_allow") or []
    _print_section("Reviewer filters", {
        "deny":  ", ".join(deny) if deny else "(none)",
        "allow": ", ".join(allow) if allow else "(none — all humans included)",
    })

    # Show per-repo subdirs that exist
    repos = [d for d in tri_dir.iterdir() if d.is_dir() and "__" in d.name] if tri_dir.exists() else []
    if repos:
        print("  Per-repo data:")
        for r in sorted(repos):
            slug = r.name.replace("__", "/", 1)
            pr_count = len(list((r / ".raw" / "prs").glob("*.json"))) if (r / ".raw" / "prs").exists() else 0
            print(f"    {slug:<35}  {pr_count} PRs cached  ({r})")
        print()

    return 0


def _print_section(title: str, fields: dict) -> None:
    print(f"  {title}:")
    for k, v in fields.items():
        print(f"    {k:<12}  {v}")
    print()
