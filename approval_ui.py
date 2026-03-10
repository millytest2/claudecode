"""
Rich terminal UI for the human approval gate.

Displays each opportunity with full context, then prompts the user to
approve (execute), skip (never surface again), or defer (review later).
"""

import sys
from typing import List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich import box

from models import Opportunity, OpportunityStatus, OpportunityType

console = Console()

# Color mapping per opportunity type
TYPE_COLORS = {
    OpportunityType.FREELANCE: "bright_cyan",
    OpportunityType.REDDIT_PROBLEM: "bright_yellow",
    OpportunityType.MARKET: "bright_green",
    OpportunityType.CONTENT: "bright_magenta",
}

TYPE_LABELS = {
    OpportunityType.FREELANCE: "💼 FREELANCE GIG",
    OpportunityType.REDDIT_PROBLEM: "💡 PROBLEM → PRODUCT",
    OpportunityType.MARKET: "📈 MARKET SETUP",
    OpportunityType.CONTENT: "✍️  CONTENT",
}

SCORE_COLORS = {
    (0, 5): "red",
    (5, 7): "yellow",
    (7, 9): "green",
    (9, 11): "bright_green",
}


def _score_color(score: float) -> str:
    for (lo, hi), color in SCORE_COLORS.items():
        if lo <= score < hi:
            return color
    return "white"


def _score_bar(score: float, width: int = 20) -> str:
    filled = int((score / 10) * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar


def print_header(scan_num: int, total_found: int, showing: int):
    console.rule(f"[bold]🤖 Money Agent — Scan #{scan_num}[/bold]")
    console.print(
        f"  Found [bold]{total_found}[/bold] opportunities  →  "
        f"[bold green]{showing}[/bold green] worth reviewing\n"
    )


def display_opportunity(opp: Opportunity, index: int, total: int) -> None:
    """Print a rich panel for one opportunity."""
    opp_color = TYPE_COLORS.get(opp.opp_type, "white")
    opp_label = TYPE_LABELS.get(opp.opp_type, opp.opp_type.value.upper())
    score_clr = _score_color(opp.score)

    # Score bar
    score_bar = _score_bar(opp.score)
    score_line = (
        f"[{score_clr}]{score_bar}[/{score_clr}]  "
        f"[bold {score_clr}]{opp.score:.1f}/10[/bold {score_clr}]"
    )

    # Build details table
    details = Table(box=None, show_header=False, padding=(0, 1))
    details.add_column("key", style="dim", width=18)
    details.add_column("value")

    details.add_row("Earnings", f"[bold green]{opp.estimated_earnings}[/bold green]")
    details.add_row("Effort", opp.effort_level.capitalize() if opp.effort_level else "—")
    details.add_row("Time to $", opp.time_to_money or "—")
    details.add_row("Source", opp.source)
    if opp.tags:
        details.add_row("Tags", "  ".join(f"[dim]#{t}[/dim]" for t in opp.tags))

    # Build panel content
    content = Text()
    content.append(f"{opp_label}\n\n", style=f"bold {opp_color}")
    content.append(f"{opp.title}\n\n", style="bold white")
    content.append("Description:\n", style="dim")
    content.append(opp.description[:400] + ("…" if len(opp.description) > 400 else ""), style="white")
    content.append(f"\n\nURL: {opp.source_url}\n\n", style="dim blue")
    content.append("Claude's take:\n", style="dim")
    content.append(opp.reasoning or "(no evaluation)", style="italic")
    content.append(f"\n\nScore: {score_line}\n")

    console.print(
        Panel(
            content,
            title=f"[dim]Opportunity {index}/{total}[/dim]",
            border_style=opp_color,
            padding=(1, 2),
        )
    )
    console.print(details)
    console.print()


def prompt_approval(opp: Opportunity, index: int, total: int) -> str:
    """
    Display the opportunity and prompt the user.
    Returns: 'approve' | 'skip' | 'defer' | 'quit'
    """
    display_opportunity(opp, index, total)

    console.print(
        "  [bold green]\\[A]pprove[/bold green] — execute this now   "
        "[bold red]\\[S]kip[/bold red] — not interested   "
        "[bold yellow]\\[D]efer[/bold yellow] — remind me later   "
        "[bold dim]\\[Q]uit[/bold dim]"
    )

    while True:
        choice = Prompt.ask("  Your choice", choices=["a", "s", "d", "q", "A", "S", "D", "Q"], default="s")
        choice = choice.lower()
        if choice == "a":
            return "approve"
        if choice == "s":
            return "skip"
        if choice == "d":
            return "defer"
        if choice == "q":
            return "quit"


def display_execution_start(opp: Opportunity) -> None:
    opp_label = TYPE_LABELS.get(opp.opp_type, opp.opp_type.value)
    console.rule(f"[bold green]⚡ Executing: {opp_label}[/bold green]")
    console.print(f"[dim]{opp.title}[/dim]\n")
    console.print("[bold]Claude is generating your deliverable...[/bold]\n")
    console.print("─" * 60)


def display_execution_complete(opp) -> None:
    action = opp.proposed_action
    if not action:
        return
    console.print("\n" + "─" * 60)
    console.rule("[bold green]✅ Done![/bold green]")
    console.print(Panel(
        f"[bold]Saved to:[/bold] [blue]{action.output_file}[/blue]\n\n"
        f"[bold]Next steps:[/bold]\n{action.instructions}",
        title="📁 Output",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def display_summary(approved: int, skipped: int, deferred: int) -> None:
    console.rule("[bold]Session Summary[/bold]")
    table = Table(box=box.SIMPLE)
    table.add_column("Action", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("[green]Approved & Executed[/green]", str(approved))
    table.add_row("[yellow]Deferred[/yellow]", str(deferred))
    table.add_row("[dim]Skipped[/dim]", str(skipped))
    console.print(table)


def display_scan_start(sources: List[str]) -> None:
    console.rule("[bold cyan]🔍 Scanning for opportunities[/bold cyan]")
    for s in sources:
        console.print(f"  • {s}")
    console.print()


def display_no_opportunities() -> None:
    console.print(
        Panel(
            "[dim]No opportunities met the score threshold this scan.\n"
            "The agent will scan again soon.[/dim]",
            border_style="dim",
        )
    )


def display_error(msg: str) -> None:
    console.print(f"[bold red]Error:[/bold red] {msg}")


def run_approval_loop(opportunities: List[Opportunity]) -> Tuple[List[Opportunity], List[Opportunity]]:
    """
    Walk the user through all opportunities.
    Returns (approved_list, deferred_list).
    """
    approved: List[Opportunity] = []
    deferred: List[Opportunity] = []
    skipped = 0

    for i, opp in enumerate(opportunities, 1):
        choice = prompt_approval(opp, i, len(opportunities))

        if choice == "approve":
            opp.status = OpportunityStatus.APPROVED
            approved.append(opp)
        elif choice == "defer":
            opp.status = OpportunityStatus.PENDING
            deferred.append(opp)
            console.print("  [yellow]→ Saved for later[/yellow]\n")
        elif choice == "skip":
            opp.status = OpportunityStatus.REJECTED
            skipped += 1
            console.print("  [dim]→ Skipped[/dim]\n")
        elif choice == "quit":
            console.print("  [dim]→ Exiting approval loop[/dim]\n")
            break

    display_summary(len(approved), skipped, len(deferred))
    return approved, deferred
