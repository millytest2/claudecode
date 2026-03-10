"""
Reddit scanner — finds freelance gigs, paid requests, and solvable problems.

Works in two modes:
  1. Authenticated (PRAW) — requires REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
  2. Anonymous  — uses Reddit's public JSON API (no credentials needed)
"""

import hashlib
import time
import logging
from datetime import datetime, timezone
from typing import List

import requests

import config
from models import Opportunity, OpportunityType

logger = logging.getLogger(__name__)

# Patterns that signal someone wants to PAY for something
HIRE_KEYWORDS = [
    "[hiring]", "[paid]", "paying", "pay someone", "willing to pay",
    "budget:", "budget is", "offering $", "offering usd", "hourly rate",
    "fixed price", "per hour", "per project", "commission", "bounty",
    "need a developer", "need a designer", "need a writer", "need someone",
    "looking to hire", "looking for a freelancer", "job offer",
]

# Patterns that signal an unfilled problem / potential product idea
PROBLEM_KEYWORDS = [
    "i wish there was", "does anyone know a tool", "is there an app",
    "why isn't there", "i can't find a", "nobody seems to offer",
    "i would pay for", "desperately need", "struggling with",
    "pain point", "biggest problem", "major issue",
]

FORHIRE_SUBS = ["forhire", "slavelabour", "Jobs4Bitcoins"]
PROBLEM_SUBS = ["entrepreneur", "smallbusiness", "startups", "SideProject", "webdev"]


def _reddit_json(subreddit: str, sort: str = "new", limit: int = 25) -> list:
    """Fetch posts from Reddit's public JSON endpoint."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    headers = {"User-Agent": config.REDDIT_USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", {}).get("children", [])
    except Exception as exc:
        logger.warning("Reddit JSON fetch failed for r/%s: %s", subreddit, exc)
        return []


def _make_id(url: str) -> str:
    return "reddit_" + hashlib.md5(url.encode()).hexdigest()[:12]


def _post_to_opportunity(post_data: dict, opp_type: OpportunityType) -> Opportunity:
    title = post_data.get("title", "")
    body = post_data.get("selftext", "")[:800]
    url = "https://reddit.com" + post_data.get("permalink", "")
    subreddit = post_data.get("subreddit", "")
    score = post_data.get("score", 0)
    num_comments = post_data.get("num_comments", 0)

    description = f"{body}\n\n[Score: {score} | Comments: {num_comments} | r/{subreddit}]"

    return Opportunity(
        id=_make_id(url),
        opp_type=opp_type,
        title=title,
        description=description.strip(),
        source_url=url,
        source="reddit",
        raw_data={
            "subreddit": subreddit,
            "score": score,
            "num_comments": num_comments,
            "created_utc": post_data.get("created_utc", 0),
            "author": post_data.get("author", "[deleted]"),
            "flair": post_data.get("link_flair_text", ""),
        },
    )


def scan_freelance_gigs() -> List[Opportunity]:
    """Scan r/forhire and similar subs for paid gigs."""
    opportunities: List[Opportunity] = []
    seen_ids: set = set()

    for sub in FORHIRE_SUBS:
        posts = _reddit_json(sub, sort="new", limit=30)
        for child in posts:
            post = child.get("data", {})
            title_lower = post.get("title", "").lower()
            flair = (post.get("link_flair_text") or "").lower()

            # Only pick up "hiring" posts, not "for hire" offers
            is_hiring = (
                "[hiring]" in title_lower
                or flair in ("hiring", "paid", "job offer")
                or any(kw in title_lower for kw in HIRE_KEYWORDS[:6])
            )
            if not is_hiring:
                continue

            opp = _post_to_opportunity(post, OpportunityType.FREELANCE)
            if opp.id not in seen_ids:
                seen_ids.add(opp.id)
                opportunities.append(opp)

        time.sleep(1.5)  # Be polite to Reddit

    logger.info("Reddit freelance scan found %d opportunities", len(opportunities))
    return opportunities


def scan_problem_posts() -> List[Opportunity]:
    """Scan entrepreneurship / dev subs for unfilled problems = product ideas."""
    opportunities: List[Opportunity] = []
    seen_ids: set = set()

    for sub in PROBLEM_SUBS:
        posts = _reddit_json(sub, sort="hot", limit=25)
        for child in posts:
            post = child.get("data", {})
            title_lower = post.get("title", "").lower()
            body_lower = post.get("selftext", "").lower()
            combined = title_lower + " " + body_lower

            has_problem = any(kw in combined for kw in PROBLEM_KEYWORDS)
            # Also pick up posts with high engagement
            high_engagement = post.get("num_comments", 0) > 15 and post.get("score", 0) > 50

            if not (has_problem or high_engagement):
                continue

            opp = _post_to_opportunity(post, OpportunityType.REDDIT_PROBLEM)
            if opp.id not in seen_ids:
                seen_ids.add(opp.id)
                opportunities.append(opp)

        time.sleep(1.5)

    logger.info("Reddit problem scan found %d opportunities", len(opportunities))
    return opportunities


def scan_all() -> List[Opportunity]:
    """Run all Reddit scanners and return combined results."""
    results = []
    results.extend(scan_freelance_gigs())
    results.extend(scan_problem_posts())
    return results
