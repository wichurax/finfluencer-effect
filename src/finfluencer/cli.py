"""Command line: finfluencer videos | classify | prices | analyze, or load-labels | prices | analyze."""

import argparse
import json
from datetime import datetime, time, timedelta
from time import sleep


def wait_until(hhmm: str) -> None:
    now = datetime.now()
    target = datetime.combine(now.date(), time.fromisoformat(hhmm))
    if target <= now:
        target += timedelta(days=1)
    print(f"waiting until {target:%Y-%m-%d %H:%M}", flush=True)
    sleep((target - now).total_seconds())


def main() -> None:
    parser = argparse.ArgumentParser(prog="finfluencer")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("videos", help="fetch video metadata and transcripts")
    p.add_argument("--channel", nargs="*", help="channel keys from config.py (default: all)")

    p = sub.add_parser("classify", help="extract per-stock stance from transcripts with Claude")
    p.add_argument("--backend", choices=["api", "cli", "codex"], default="api",
                   help="api: Anthropic API key; cli: the local `claude` CLI and its login; "
                        "codex: GPT through the local Codex CLI")
    p.add_argument("--model", default="claude-opus-5-5",
                   help="for --backend codex a GPT model name; a claude-* value means Codex's default")
    p.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, help="classify at most N videos (for a trial run)")
    p.add_argument("--channel", nargs="*")
    p.add_argument("--shard", help='"i/n": only videos whose id hashes to i mod n, e.g. 0/2 for one '
                                   "of two labellers running side by side")
    p.add_argument("--start-at", help="HH:MM local time to wait for first, e.g. when a usage limit resets")

    p = sub.add_parser("agreement", help="label a sample again with the other model and compare")
    p.add_argument("--sample", type=int, default=40, help="videos per direction (Claude->GPT, GPT->Claude)")
    p.add_argument("--claude-model", default="claude-opus-5-5")
    p.add_argument("--claude-effort", default="low")
    p.add_argument("--directions", nargs="+", default=["claude", "gpt"],
                   help="whose labels get a second opinion: claude (from GPT), gpt (from Claude)")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--compare-only", action="store_true")
    p.add_argument("--start-at", help="HH:MM local time to wait for first")

    p = sub.add_parser("effort-test", help="a cheaper model at several efforts, against Opus labels")
    p.add_argument("--model", default="claude-haiku-5-5")
    p.add_argument("--efforts", nargs="+", default=["low", "medium"])
    p.add_argument("--sample", type=int, default=30)
    p.add_argument("--workers", type=int, default=4)

    sub.add_parser("prices", help="download daily prices for every classified ticker")
    sub.add_parser("earnings", help="download earnings announcement dates (for the news-day control)")

    sub.add_parser("report", help="redraw the charts, report.md and index.html from results/")
    sub.add_parser("robustness", help="key tests on Claude vs GPT labels of the same videos")
    sub.add_parser("video-data", help="write the numbers for the Remotion clip to video/src/data.json")
    sub.add_parser("export-labels", help="write the public labels (labels/*.csv) from data/")
    sub.add_parser("load-labels", help="rebuild data/ from the public labels, to run the analysis without transcripts")

    p = sub.add_parser("analyze", help="build events, run the tests, write results/")
    p.add_argument("--placebo-draws", type=int, default=2000)
    p.add_argument("--seed", type=int, default=7)

    args = parser.parse_args()
    if args.command == "videos":
        from .videos import fetch_all
        fetch_all(args.channel)
    elif args.command == "classify":
        from .classify import classify_all
        if args.start_at:
            wait_until(args.start_at)
        classify_all(args.backend, args.model, args.effort, args.workers, args.limit, args.channel, args.shard)
    elif args.command == "agreement":
        from .agreement import compare, relabel
        if args.start_at:
            wait_until(args.start_at)
        if not args.compare_only:
            relabel(args.sample, args.claude_model, args.claude_effort, args.workers, seed=11,
                    directions=tuple(args.directions))
        print(json.dumps(compare(), indent=1))
    elif args.command == "effort-test":
        from .agreement import effort_test
        print(json.dumps(effort_test(args.sample, args.model, args.efforts, args.workers, seed=5), indent=1))
    elif args.command == "prices":
        from .prices import download_all
        download_all()
    elif args.command == "earnings":
        from .prices import download_earnings
        download_earnings()
    elif args.command == "video-data":
        from .video_data import export
        export()
    elif args.command == "export-labels":
        from .labels import export
        export()
    elif args.command == "load-labels":
        from .labels import load
        load()
    elif args.command == "robustness":
        from .robustness import run as robustness
        robustness()
    elif args.command == "report":
        from .report import write_report
        write_report()
    elif args.command == "analyze":
        from .analyze import run
        run(args.placebo_draws, args.seed)


if __name__ == "__main__":
    main()
