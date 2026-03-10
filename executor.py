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
# All prompts are written FROM the user's perspective — Claude is ghostwriting for them.

def _freelance_system() -> str:
    return f"""You are ghostwriting a freelance proposal FOR this specific person.
Write in first person AS THEM. Their background:

{config.USER_PROFILE}

PROPOSAL RULES:
- Open with a hook that shows you immediately understand their problem (no "Hi, I'm X...")
- Reference specific relevant experience from their background (name the companies/projects)
- Show the AI + sales + builder combo as an unfair advantage — most freelancers can't do what they can
- Be concrete: suggest a specific approach, not vague "I can help with that"
- Close with a clear CTA and timeline
- Tone: confident, direct, human. Not corporate. Not salesy. Intelligent.
- Length: 250-350 words max. Tight.
- Format as clean Markdown."""


def _problem_system() -> str:
    return f"""You are a strategic advisor helping this person find a business inside a problem.
Their profile:

{config.USER_PROFILE}

BUSINESS PLAN RULES:
- Always look for how this connects to or validates uPath.ai's direction
- Consider how their AI + sales engineering background gives them an unfair distribution advantage
- The MVP must be something they can ship in 1-2 weekends using their existing stack
- Revenue model should match their rate floor ($100+/hr) or build to recurring SaaS
- Be direct about what's realistic vs. speculative
- Format as clean Markdown."""


def _market_system() -> str:
    return f"""You are writing a trade plan for an experienced stock trader.
Their trading profile:

{config.USER_PROFILE}

TRADE PLAN RULES:
- Write for someone who understands technical analysis — don't over-explain basics
- The AI sector watchlist is their edge — emphasize any AI/tech narrative driving the move
- Position sizing: assume they're working with a moderate account, max 5% per trade
- Always include invalidation scenario (when the thesis is wrong)
- Be clear about whether this is a momentum trade, swing, or longer-term thesis
- Format as clean Markdown.
- Always end with: ⚠️ *Not financial advice. Do your own research.*"""


def _content_system() -> str:
    return f"""You are a content strategist writing AS this person for their personal brand.
Their voice and positioning:

{config.USER_PROFILE}

CONTENT RULES:
- Write in their voice: systems-thinker, builder, polymath. Curious about WHY things work.
- Not preachy, not generic. Real observations from someone actually in the arena.
- Every piece should build their AI + builder + polymath brand on X/Twitter
- Include a monetisation angle: affiliate, consulting CTA, product waitlist, or paid newsletter
- Format as clean Markdown with suggested title, hook tweet, and the full piece."""


# ── User prompt templates ───────────────────────────────────────────────────

FREELANCE_PROMPT = """OPPORTUNITY:
Title: {title}
Description:
{description}

URL: {source_url}

Write a winning proposal for this job as if you ARE the person described in the profile above.
Pull specific experience from their background that directly maps to this client's need.
After the proposal, add:

## Why You're the Right Fit (for your own reference, not to send)
- Which skills from your background are the unfair advantage here

## Next Steps
1. Where/how to submit
2. What to include with the application
3. Follow-up timing"""

PROBLEM_PROMPT = """PROBLEM/OPPORTUNITY:
Title: {title}
Description:
{description}

Source: {source_url}
Agent evaluation: {reasoning}
Estimated earnings: {estimated_earnings}

Build a business plan for this person to solve this problem and make money from it.
Consider how this connects to uPath.ai or builds their AI + polymath brand.

## The Problem (restated clearly)
## Why They're Uniquely Positioned to Solve It
## Product / Service Concept
## Target Customer & Willingness to Pay
## MVP (what to build in 1-2 weekends)
## Revenue Model & Pricing
## Go-to-Market: First 30 Days
## Connection to uPath.ai / Long-term Vision
## This Week's Actions (max 5 bullet points)"""

MARKET_PROMPT = """MARKET SETUP:
{description}

Source: {source_url}
Agent notes: {reasoning}

Write a complete, executable trade plan.

## Setup Analysis
## Entry Criteria
## Stop Loss
## Take Profit Targets (T1, T2, T3)
## Position Size
## Risk / Reward
## AI / Tech Narrative (if applicable — how does this connect to the AI boom?)
## Invalidation Scenario

## Execution Checklist
- [ ] Confirm entry condition is met
- [ ] Set stop loss order
- [ ] Set T1 limit order
- [ ] Note the invalidation trigger
- [ ] Log trade in journal

⚠️ *Not financial advice. Do your own research.*"""

CONTENT_PROMPT = """CONTENT OPPORTUNITY:
{title}

Context: {description}

Write a complete piece of content for this person's polymath / AI builder brand.
Include:
1. **Suggested Title** (punchy, specific, curiosity-inducing)
2. **Hook Tweet** (the X/Twitter post to launch this)
3. **The Full Piece** (article, thread, or essay — whichever fits best)
4. **Monetisation CTA** embedded naturally (consulting, uPath.ai waitlist, or newsletter)"""


def _get_system_and_prompt(opp: Opportunity) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given opportunity type."""
    if opp.opp_type == OpportunityType.FREELANCE:
        return _freelance_system(), FREELANCE_PROMPT.format(
            title=opp.title,
            description=opp.description[:1500],
            source_url=opp.source_url,
        )
    elif opp.opp_type == OpportunityType.REDDIT_PROBLEM:
        return _problem_system(), PROBLEM_PROMPT.format(
            title=opp.title,
            description=opp.description[:1500],
            source_url=opp.source_url,
            reasoning=opp.reasoning,
            estimated_earnings=opp.estimated_earnings,
        )
    elif opp.opp_type == OpportunityType.MARKET:
        return _market_system(), MARKET_PROMPT.format(
            description=opp.description,
            source_url=opp.source_url,
            reasoning=opp.reasoning,
        )
    else:
        return _content_system(), CONTENT_PROMPT.format(
            title=opp.title,
            description=opp.description[:1000],
        )


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
