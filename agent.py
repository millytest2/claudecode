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
    """
    Demo opportunities — realistic examples tuned to this user's actual background:
    AI sales engineer + builder of uPath.ai + polymath creator + trader.
    """
    demo_opps = [
        # ── Freelance: AI consulting — perfect fit for their Inbenta + uPath background ──
        Opportunity(
            id="demo_freelance_ai_consult",
            opp_type=OpportunityType.FREELANCE,
            title="[Hiring] AI Solutions Consultant for Enterprise SaaS — $150-200/hr, remote",
            description=(
                "We're a Series B SaaS company (200 employees) looking for an AI consultant "
                "to help us integrate LLM-based features into our product. We need someone who "
                "understands both the technical side (prompt engineering, multi-agent systems, "
                "RAG pipelines) AND can communicate strategy to non-technical executives. "
                "This is a 3-month engagement, ~15hrs/week. Previous experience with enterprise "
                "AI products required. Bonus: experience in sales engineering or pre-sales."
            ),
            source_url="https://reddit.com/r/forhire/comments/ai_consult_demo",
            source="reddit",
            raw_data={"subreddit": "forhire", "score": 34, "num_comments": 8},
        ),
        # ── Freelance: Sales engineer contract — direct match ──
        Opportunity(
            id="demo_freelance_sales_eng",
            opp_type=OpportunityType.FREELANCE,
            title="[Hiring] Fractional Sales Engineer for AI startup — equity + $120/hr",
            description=(
                "Early-stage AI startup (just closed seed) needs a fractional sales engineer "
                "for 3-6 months to help close our first 10 enterprise customers. You'll own "
                "technical demos, POC builds, and RFP responses. Product is an AI knowledge "
                "management platform. We need someone who's done this before at an AI company "
                "and can hit the ground running. 20hrs/week, flexible schedule."
            ),
            source_url="https://news.ycombinator.com/item?id=sales_eng_demo",
            source="hackernews",
            raw_data={"score": 52, "num_comments": 19},
        ),
        # ── Problem → Product: AI tool gap that overlaps with uPath.ai ──
        Opportunity(
            id="demo_problem_ai_sales",
            opp_type=OpportunityType.REDDIT_PROBLEM,
            title="r/sales: Our AEs spend 3 hours/day on CRM updates and follow-up emails — there HAS to be a better way",
            description=(
                "Posted in r/sales with 340 upvotes and 180 comments. "
                "Sales teams are drowning in admin: updating Salesforce after every call, "
                "writing follow-up emails, summarising meeting notes. Multiple commenters saying "
                "they'd pay $50-100/month per seat for a tool that listens to calls and "
                "auto-populates CRM fields + drafts follow-ups. Existing tools like Gong are "
                "$1,200+/yr per seat — too expensive for SMBs. The thread has 3 different people "
                "saying 'someone should build this.' Gap in the market for an SMB-focused version."
            ),
            source_url="https://reddit.com/r/sales/comments/crm_pain_demo",
            source="reddit",
            raw_data={"subreddit": "sales", "score": 340, "num_comments": 180},
        ),
        # ── Problem → Product: Content / brand opportunity ──
        Opportunity(
            id="demo_content_polymath",
            opp_type=OpportunityType.CONTENT,
            title="Trending: 'The death of the specialist — why companies are hiring polymaths in the AI era'",
            description=(
                "Multiple viral threads on X this week around generalists vs specialists in the "
                "age of AI. The argument: AI commoditises specialist knowledge, so the new premium "
                "is people who can connect dots across domains — exactly the 'polymath' positioning "
                "this person has been building. This is a direct on-ramp to write the definitive "
                "piece on this topic from the POV of someone actually building AI tools as a "
                "multi-domain builder. High potential for viral distribution and consulting pipeline."
            ),
            source_url="https://twitter.com/search?q=polymath+AI+generalist",
            source="twitter_trend",
            raw_data={"engagement": "high", "trend_age": "48hrs"},
        ),
        # ── Market: AI sector momentum ──
        Opportunity(
            id="demo_market_ai_sector",
            opp_type=OpportunityType.MARKET,
            title="PLTR: UP 6.1% today | Volume 3.4x average | AI government contracts narrative",
            description=(
                "Ticker: PLTR\nCompany: Palantir Technologies\nSector: AI / Defense Tech\n"
                "Market Cap: $52B\nPrice: $23.80\n1-Day Change: +6.10%\n"
                "Volume Factor: 3.4x avg\nRSI (14): 62.4\n"
                "Catalyst: DoD contract renewal + AIP (AI Platform) enterprise expansion news.\n"
                "Signals: Strong momentum | Heavy volume | AI narrative tailwind | "
                "Institutional accumulation pattern on the daily chart."
            ),
            source_url="https://finance.yahoo.com/quote/PLTR",
            source="market",
            raw_data={
                "ticker": "PLTR", "price": 23.80,
                "pct_change": 0.061, "vol_factor": 3.4, "rsi": 62.4,
                "sector": "AI/Defense",
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
