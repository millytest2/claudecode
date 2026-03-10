"""
Claude-powered opportunity evaluator.

Takes raw opportunities and enriches them with:
  - A score (0–10)
  - Estimated earnings range
  - Effort level
  - Time to first dollar
  - Strategic reasoning
  - Tags

Uses claude-opus-4-6 with adaptive thinking + streaming.
"""

import json
import logging
from typing import List

import anthropic

import config
from models import Opportunity, OpportunityType

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


EVAL_SYSTEM = f"""You are an elite opportunity evaluator for an autonomous money-making agent.
You are evaluating opportunities specifically for ONE person. Their profile is below.
Your job: decide if this opportunity is worth their time given WHO THEY ARE.

{config.USER_PROFILE}

EVALUATION RULES:
• Score HIGH (8-10) when: matches their AI/sales/builder skills, pays $100+/hr equivalent,
  builds toward uPath.ai or their polymath brand, low competition given their unique combo.
• Score MEDIUM (6-7) when: good fit but requires learning or is somewhat competitive.
• Score LOW (<6) when: generic work, below their rate floor, no skill compounding, or
  distracts from their core trajectory.
• Be SPECIFIC with dollar estimates — use their rate floor ($100/hr tech, $150/hr AI).
• Prioritize opportunities that are RARE FITS — where their AI + sales + builder combo
  gives them an unfair advantage over regular freelancers.
• For market plays: score based on their existing trading experience and AI sector knowledge.

Always respond with valid JSON only. No markdown, no commentary outside the JSON."""

EVAL_USER_TEMPLATE = """Evaluate this opportunity FOR THIS SPECIFIC PERSON (see profile above):

TYPE: {opp_type}
SOURCE: {source}
TITLE: {title}
DESCRIPTION:
{description}

Return a JSON object with these exact fields:
{{
  "score": <float 0-10, where 7+ = act on this>,
  "estimated_earnings": "<specific dollar range given their skills, e.g. '$150/hr × 10hrs = $1,500'>",
  "effort_level": "<low|medium|high>",
  "time_to_money": "<e.g. '2–3 days' or 'this week'>",
  "reasoning": "<2-3 sentences explaining fit to THEIR specific background — mention which of their skills apply>",
  "tags": ["<tag1>", "<tag2>"],
  "skill_match": "<which of their specific skills make them the right fit, or why it's a miss>",
  "skip_reason": "<if score < 6, one-line reason this doesn't fit their profile, else empty string>"
}}"""


def evaluate_opportunity(opp: Opportunity) -> Opportunity:
    """Evaluate a single opportunity using Claude. Mutates and returns the opp."""
    client = _get_client()

    prompt = EVAL_USER_TEMPLATE.format(
        opp_type=opp.opp_type.value,
        source=opp.source,
        title=opp.title,
        description=opp.description[:1200],
    )

    try:
        with client.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=512,
            thinking={"type": "adaptive"},
            system=EVAL_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            final = stream.get_final_message()

        # Extract text content (skip thinking blocks)
        text = ""
        for block in final.content:
            if block.type == "text":
                text += block.text

        # Strip any accidental markdown fences
        text = text.strip().strip("```json").strip("```").strip()
        data = json.loads(text)

        opp.score = float(data.get("score", 0))
        opp.estimated_earnings = data.get("estimated_earnings", "")
        opp.effort_level = data.get("effort_level", "")
        opp.time_to_money = data.get("time_to_money", "")
        opp.reasoning = data.get("reasoning", "")
        opp.tags = data.get("tags", [])

    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error evaluating '%s': %s | raw: %s", opp.title[:50], exc, text[:200])
    except Exception as exc:
        logger.error("Evaluation failed for '%s': %s", opp.title[:50], exc)

    return opp


def evaluate_batch(opps: List[Opportunity], min_score: float = 0.0) -> List[Opportunity]:
    """
    Evaluate a list of opportunities and return only those meeting min_score.
    Results are sorted by score descending.
    """
    evaluated = []
    for i, opp in enumerate(opps):
        logger.info("Evaluating %d/%d: %s", i + 1, len(opps), opp.title[:60])
        evaluated.append(evaluate_opportunity(opp))

    # Filter and sort
    passing = [o for o in evaluated if o.score >= min_score]
    passing.sort(key=lambda o: o.score, reverse=True)
    return passing
