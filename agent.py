"""
Autonomous Money Agent — main entry point.

Run with:
    python agent.py              # single scan + approval loop
    python agent.py --loop       # continuous scanning (every N minutes)
    python agent.py --demo       # inject fake opportunities for UI demo

Flow per scan:
  1. Scan all sources (Reddit, HN, Markets)
  2. Evaluate each opportunity with Claude
  3. Filter by score threshold
  4. Present to user for approval
  5. Execute approved opportunities (Claude generates deliverable)
  6. Save output to ./output/
  7. (If --loop) wait and repeat
"""

import argparse
import logging
import os
import time
from datetime import datetime
from typing import List

from rich.console import Console

import config
import evaluator
import executor
import approval_ui
from models import Opportunity, OpportunityType, OpportunityStatus
from scanners import reddit_scanner, hn_scanner, market_scanner

console = Console()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("agent")

# Track seen opportunity IDs across scans to avoid repeats
_seen_ids: set = set()
_deferred: List[Opportunity] = []
_scan_count = 0


def check_config() -> bool:
    """Validate required configuration and warn about optional items."""
    ok = True

    if not config.ANTHROPIC_API_KEY:
        console.print("[bold red]ERROR:[/bold red] ANTHROPIC_API_KEY is not set.")
        console.print("  Add it to your .env file and restart.\n")
        ok = False

    if not (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET):
        console.print(
            "[yellow]INFO:[/yellow] Reddit credentials not set — Reddit scanner "
            "will use the anonymous JSON API (lower rate limits)."
        )

    return ok


def run_scan() -> List[Opportunity]:
    """Run all scanners and return de-duplicated results."""
    global _seen_ids

    approval_ui.display_scan_start([
        "Reddit (r/forhire, r/entrepreneur, r/SideProject…)",
        "Hacker News (Who is Hiring?, Ask HN…)",
        "Market momentum (Yahoo Finance)",
    ])

    raw: List[Opportunity] = []

    try:
        raw.extend(reddit_scanner.scan_all())
    except Exception as exc:
        logger.error("Reddit scanner failed: %s", exc)

    try:
        raw.extend(hn_scanner.scan_all())
    except Exception as exc:
        logger.error("HN scanner failed: %s", exc)

    try:
        raw.extend(market_scanner.scan_all())
    except Exception as exc:
        logger.error("Market scanner failed: %s", exc)

    # De-duplicate against previously seen
    new_opps = [o for o in raw if o.id not in _seen_ids]
    _seen_ids.update(o.id for o in new_opps)

    console.print(
        f"  Scanned: [bold]{len(raw)}[/bold] total  →  "
        f"[bold green]{len(new_opps)}[/bold green] new\n"
    )
    return new_opps


def run_demo_scan() -> List[Opportunity]:
    """Return a set of fake opportunities for demo / testing purposes."""
    from datetime import datetime

    demo_opps = [
        Opportunity(
            id="demo_freelance_1",
            opp_type=OpportunityType.FREELANCE,
            title="[Hiring] Python developer needed for data pipeline — $80/hr",
            description=(
                "We need an experienced Python developer to build an ETL pipeline "
                "that pulls data from 3 REST APIs, transforms it, and loads it into "
                "Postgres. Budget: $80/hr, ~20 hours of work. Must have experience "
                "with SQLAlchemy, requests, and pandas."
            ),
            source_url="https://reddit.com/r/forhire/comments/demo1",
            source="reddit",
            raw_data={"subreddit": "forhire", "score": 12, "num_comments": 4},
        ),
        Opportunity(
            id="demo_problem_1",
            opp_type=OpportunityType.REDDIT_PROBLEM,
            title="Ask HN: Is there a tool that auto-summarises Slack threads for standups?",
            description=(
                "Every morning I spend 20 minutes reading Slack threads to write my standup. "
                "I'd pay $30/month for a bot that reads the threads I was tagged in and gives "
                "me a bullet-point summary. Does this exist? Comments show 15+ people agreeing."
            ),
            source_url="https://news.ycombinator.com/item?id=demo1",
            source="hackernews",
            raw_data={"score": 87, "num_comments": 43},
        ),
        Opportunity(
            id="demo_market_1",
            opp_type=OpportunityType.MARKET,
            title="NVDA: UP 4.2% today | Volume 2.8x average | RSI 58",
            description=(
                "Ticker: NVDA\nCompany: NVIDIA Corporation\nSector: Technology\n"
                "Market Cap: $2.1T\nPrice: $875.40\n1-Day Change: +4.20%\n"
                "Volume Factor: 2.8x avg\nRSI (14): 58.3\n"
                "Signals: UP 4.2% today | Volume 2.8x average"
            ),
            source_url="https://finance.yahoo.com/quote/NVDA",
            source="market",
            raw_data={
                "ticker": "NVDA", "price": 875.40,
                "pct_change": 0.042, "vol_factor": 2.8, "rsi": 58.3,
            },
        ),
    ]
    return demo_opps


def execute_approved(approved: List[Opportunity]) -> None:
    """For each approved opportunity, run the executor and show results."""
    for opp in approved:
        approval_ui.display_execution_start(opp)
        try:
            executor.execute(opp)
            opp.status = OpportunityStatus.EXECUTED
            approval_ui.display_execution_complete(opp)
        except Exception as exc:
            opp.status = OpportunityStatus.FAILED
            approval_ui.display_error(f"Execution failed: {exc}")
            logger.exception("Executor error for '%s'", opp.title)


def run_once(demo: bool = False) -> None:
    """Single scan → evaluate → approve → execute cycle."""
    global _scan_count, _deferred
    _scan_count += 1

    approval_ui.print_header(_scan_count, total_found=0, showing=0)

    # 1. Collect opportunities (real or demo)
    raw_opps = run_demo_scan() if demo else run_scan()

    # Include any previously deferred opportunities
    if _deferred:
        console.print(f"  [yellow]+ {len(_deferred)} deferred from previous scans[/yellow]\n")
        raw_opps = _deferred + raw_opps
        _deferred = []

    if not raw_opps:
        approval_ui.display_no_opportunities()
        return

    # 2. Evaluate with Claude
    console.rule("[bold]🧠 Evaluating with Claude[/bold]")
    console.print(f"  Scoring {len(raw_opps)} opportunities...\n")

    evaluated = evaluator.evaluate_batch(raw_opps, min_score=config.MIN_SCORE_THRESHOLD)
    # Cap to avoid overwhelming the user
    shortlist = evaluated[: config.MAX_OPPORTUNITIES_PER_SCAN]

    if not shortlist:
        approval_ui.display_no_opportunities()
        return

    console.print(
        f"\n  [bold green]{len(shortlist)}[/bold green] opportunities scored "
        f"≥ {config.MIN_SCORE_THRESHOLD}/10 — presenting for your review.\n"
    )

    # 3. Human approval
    console.rule("[bold]👤 Your Review[/bold]")
    approved, deferred_now = approval_ui.run_approval_loop(shortlist)
    _deferred.extend(deferred_now)

    # 4. Execute
    if approved:
        console.rule("[bold green]⚡ Executing Approved Opportunities[/bold green]")
        execute_approved(approved)

    console.print(f"\n[dim]Output saved to: {os.path.abspath(config.OUTPUT_DIR)}[/dim]\n")


def run_loop(interval_minutes: int, demo: bool = False) -> None:
    """Continuously scan on a schedule."""
    console.print(
        f"[bold cyan]🔄 Agent running continuously "
        f"(every {interval_minutes} min)[/bold cyan]\n"
        "Press Ctrl+C to stop.\n"
    )
    while True:
        try:
            run_once(demo=demo)
            next_run = datetime.now().strftime("%H:%M")
            console.print(
                f"[dim]Next scan in {interval_minutes} minutes "
                f"(started at {next_run})[/dim]\n"
            )
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            console.print("\n[bold]Agent stopped.[/bold]")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous money-making agent — find and execute opportunities."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help=f"Run continuously (every {config.SCAN_INTERVAL_MINUTES} minutes)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use synthetic demo opportunities (no real scanning)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=config.SCAN_INTERVAL_MINUTES,
        help="Scan interval in minutes (default: from config)",
    )
    args = parser.parse_args()

    console.print(
        "\n[bold cyan]💰 Autonomous Money Agent[/bold cyan]\n"
        "[dim]Finds opportunities, proposes actions, executes with your approval.[/dim]\n"
    )

    if not check_config():
        return

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    if args.loop:
        run_loop(args.interval, demo=args.demo)
    else:
        run_once(demo=args.demo)


if __name__ == "__main__":
    main()
