"""
Claude-powered executor.

For each approved opportunity, Claude generates a concrete, ready-to-use
deliverable — a proposal, a content draft, a trade plan — and saves it to disk.

The executor streams output so you can watch it being written in real time.
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

import anthropic

import config
from models import Action, Opportunity, OpportunityType

logger = logging.getLogger(__name__)

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _safe_filename(title: str) -> str:
    """Convert a title to a safe filename."""
    clean = re.sub(r"[^\w\s-]", "", title).strip()
    clean = re.sub(r"\s+", "_", clean)[:60]
    return clean


def _save_output(opp: Opportunity, content: str, suffix: str) -> str:
    """Save generated content to a file, return the path."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{timestamp}_{opp.opp_type.value}_{_safe_filename(opp.title)}_{suffix}.md"
    fpath = os.path.join(config.OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    return fpath


# ── System prompts per opportunity type ────────────────────────────────────

FREELANCE_SYSTEM = """You are an expert freelance business developer.
Write compelling, personalized proposals that WIN contracts.
Your proposals are concise (under 300 words), specific, and focus on the client's problem.
Always include: a hook, your relevant experience, a specific plan, and a CTA.
Format as clean Markdown."""

PROBLEM_SYSTEM = """You are a serial entrepreneur and product strategist.
When shown a Reddit/HN problem post, you create a concrete business plan for a solution.
Be specific: name the product, describe the MVP, estimate the market, outline a launch plan.
Format as clean Markdown."""

CONTENT_SYSTEM = """You are a professional content strategist and writer.
Create high-quality, publication-ready content that generates income.
Format as clean Markdown with proper headings."""

MARKET_SYSTEM = """You are a professional trader and analyst.
When given a market setup, write a detailed trade plan with:
  - Setup analysis (why this is interesting)
  - Entry criteria (exact price or condition)
  - Stop loss level
  - Take profit targets (multiple levels)
  - Position sizing guidance (% of portfolio)
  - Risk/reward ratio
  - Key risks and invalidation scenario
Format as clean Markdown. Always remind the user this is not financial advice."""

# ── User prompt templates ───────────────────────────────────────────────────

FREELANCE_PROMPT = """OPPORTUNITY:
Title: {title}
Description:
{description}

URL: {source_url}

Write a winning freelance proposal for this job. Tailor it specifically to their requirements.
After the proposal, add a section "## Next Steps" with 3 bullet points on how to submit this."""

PROBLEM_PROMPT = """PROBLEM/OPPORTUNITY:
Title: {title}
Description:
{description}

Source: {source_url}
Evaluation: {reasoning}
Estimated earnings: {estimated_earnings}

Create a detailed business plan to build a product/service that solves this problem.
Structure:
## Product Concept
## Target Customer
## MVP Features (max 5)
## Revenue Model
## Go-to-Market (first 30 days)
## Next Steps (actionable, this week)"""

MARKET_PROMPT = """MARKET SETUP:
{description}

Source: {source_url}
Analysis notes: {reasoning}

Write a complete trade plan for this setup. Include all sections listed in your instructions.

After the plan, add:
## Execution Checklist
- [ ] step 1
- [ ] step 2
(etc.)

⚠️ *This is not financial advice. Always do your own research.*"""


def _get_system_and_prompt(opp: Opportunity) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given opportunity type."""
    if opp.opp_type == OpportunityType.FREELANCE:
        return FREELANCE_SYSTEM, FREELANCE_PROMPT.format(
            title=opp.title,
            description=opp.description[:1500],
            source_url=opp.source_url,
        )
    elif opp.opp_type == OpportunityType.REDDIT_PROBLEM:
        return PROBLEM_SYSTEM, PROBLEM_PROMPT.format(
            title=opp.title,
            description=opp.description[:1500],
            source_url=opp.source_url,
            reasoning=opp.reasoning,
            estimated_earnings=opp.estimated_earnings,
        )
    elif opp.opp_type == OpportunityType.MARKET:
        return MARKET_SYSTEM, MARKET_PROMPT.format(
            description=opp.description,
            source_url=opp.source_url,
            reasoning=opp.reasoning,
        )
    else:
        return CONTENT_SYSTEM, f"Create monetisable content for:\n\n{opp.title}\n\n{opp.description[:1000]}"


def _action_type_for(opp: Opportunity) -> str:
    return {
        OpportunityType.FREELANCE: "draft_proposal",
        OpportunityType.REDDIT_PROBLEM: "build_product_plan",
        OpportunityType.MARKET: "trade_plan",
        OpportunityType.CONTENT: "write_content",
    }.get(opp.opp_type, "draft_content")


def execute(opp: Opportunity, stream_callback=None) -> Action:
    """
    Generate the deliverable for an approved opportunity.

    stream_callback: optional callable(text_chunk) called during streaming.
    Returns an Action with the generated content and file path.
    """
    client = _get_client()
    system, user_prompt = _get_system_and_prompt(opp)

    print_fn = stream_callback or (lambda t: print(t, end="", flush=True))

    content_parts: list[str] = []

    with client.messages.stream(
        model=config.CLAUDE_MODEL,
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for event in stream:
            if (
                event.type == "content_block_delta"
                and event.delta.type == "text_delta"
            ):
                chunk = event.delta.text
                content_parts.append(chunk)
                print_fn(chunk)

        final = stream.get_final_message()

    full_content = "".join(content_parts)

    # Save to disk
    action_type = _action_type_for(opp)
    fpath = _save_output(opp, full_content, action_type)

    # Build instructions for the user
    instructions_map = {
        "draft_proposal": (
            f"1. Open the saved proposal: {fpath}\n"
            f"2. Review and personalise any [PLACEHOLDER] sections\n"
            f"3. Submit via the job URL: {opp.source_url}\n"
            "4. Follow up within 48 hours if no response"
        ),
        "build_product_plan": (
            f"1. Read the product plan: {fpath}\n"
            "2. Validate the problem by commenting on the original post\n"
            "3. Build the MVP (estimate: 1–2 weekends)\n"
            "4. Post in r/SideProject and relevant communities when ready"
        ),
        "trade_plan": (
            f"1. Review the trade plan: {fpath}\n"
            f"2. Check current price at: {opp.source_url}\n"
            "3. PAPER TRADE first to validate the setup\n"
            "4. Only risk money you can afford to lose\n"
            "⚠️ Not financial advice."
        ),
        "write_content": (
            f"1. Review the content: {fpath}\n"
            "2. Post on Medium, Substack, or your blog\n"
            "3. Share in relevant subreddits / communities\n"
            "4. Add affiliate links or CTA for monetisation"
        ),
    }

    instructions = instructions_map.get(
        action_type,
        f"Review the output at: {fpath}\nThen follow the steps outlined inside.",
    )

    action = Action(
        action_type=action_type,
        title=f"[{action_type.replace('_', ' ').title()}] {opp.title[:80]}",
        content=full_content,
        instructions=instructions,
        output_file=fpath,
        estimated_time=opp.time_to_money,
    )

    opp.proposed_action = action
    return action
