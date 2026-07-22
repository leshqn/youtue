"""CLI entrypoint: ``python -m viralworks``.

Runs full end-to-end cycles on stubs (no API keys required), prints a real reel
spec + Growth Report, and writes an HTML dashboard. Default is 2 cycles so the
self-growth (cycle 1 -> cycle 2) is visible in a single command.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .dashboard import render_cli, write_html
from .orchestrator import Orchestrator


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="viralworks", description="Self-growing AI content company")
    parser.add_argument("--cycles", type=int, default=4, help="number of weekly cycles to run")
    parser.add_argument("--config", type=str, default=None, help="path to config.yaml")
    parser.add_argument("--niche", type=str, default=None, help="override the niche")
    parser.add_argument("--fresh", action="store_true", help="wipe the learning store first (clean demo)")
    parser.add_argument("--no-html", action="store_true", help="skip writing the HTML dashboard")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.niche:
        config.niche = args.niche

    if args.fresh:
        # Wipe generated state so the demo starts from a clean cold-start.
        import shutil

        for d in (config.data_dir, config.playbooks_dir, config.reports_dir):
            shutil.rmtree(d, ignore_errors=True)
    config.ensure_dirs()

    orch = Orchestrator(config)
    results = orch.run_cycles(max(1, args.cycles))

    print(render_cli(results))

    if not args.no_html:
        out = write_html(results, config.reports_dir / "dashboard.html")
        print(f"\nHTML dashboard written to: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
