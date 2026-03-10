"""
Hacker News scanner — scrapes "Who is Hiring?" threads and "Ask HN" posts
for freelance opportunities and product ideas.

Uses the official HN Firebase API (no auth needed).
"""

import hashlib
import logging
import re
import time
from typing import List, Optional

import requests

from models import Opportunity, OpportunityType

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"
HN_BASE = "https://news.ycombinator.com"

# Keywords that indicate remote freelance / contract work
REMOTE_FREELANCE_KEYWORDS = [
    "remote", "freelance", "contract", "part-time", "part time",
    "hourly", "project-based", "consultant", "consulting",
]

# Keywords that signal interesting ask HN problems
ASK_PROBLEM_KEYWORDS = [
    "how do you", "looking for a tool", "is there a service",
    "any recommendations", "what do you use for", "struggling with",
    "pain point", "wish there was",
]


def _get_item(item_id: int) -> Optional[dict]:
    try:
        resp = requests.get(f"{HN_API}/item/{item_id}.json", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("HN item %d fetch failed: %s", item_id, exc)
        return None


def _get_top_stories(n: int = 30) -> List[int]:
    try:
        resp = requests.get(f"{HN_API}/topstories.json", timeout=8)
        resp.raise_for_status()
        return resp.json()[:n]
    except Exception:
        return []


def _get_new_stories(n: int = 50) -> List[int]:
    try:
        resp = requests.get(f"{HN_API}/newstories.json", timeout=8)
        resp.raise_for_status()
        return resp.json()[:n]
    except Exception:
        return []


def _make_id(item_id: int) -> str:
    return f"hn_{item_id}"


def _find_wih_thread() -> Optional[dict]:
    """Find the current 'Who is Hiring?' thread."""
    top_ids = _get_top_stories(100)
    for sid in top_ids:
        item = _get_item(sid)
        if item and "who is hiring" in (item.get("title") or "").lower():
            return item
        time.sleep(0.05)
    return None


def scan_who_is_hiring() -> List[Opportunity]:
    """Parse the monthly 'Who is Hiring?' thread for remote/freelance posts."""
    opportunities: List[Opportunity] = []

    thread = _find_wih_thread()
    if not thread:
        logger.info("HN: 'Who is Hiring?' thread not found in top stories")
        return opportunities

    thread_url = f"{HN_BASE}/item?id={thread['id']}"
    kid_ids = (thread.get("kids") or [])[:60]

    for kid_id in kid_ids:
        comment = _get_item(kid_id)
        if not comment or comment.get("dead") or comment.get("deleted"):
            continue

        text = comment.get("text", "") or ""
        text_lower = text.lower()

        is_remote = any(kw in text_lower for kw in REMOTE_FREELANCE_KEYWORDS)
        if not is_remote:
            continue

        # Strip HTML tags for a cleaner description
        clean_text = re.sub(r"<[^>]+>", " ", text).strip()
        clean_text = re.sub(r"\s+", " ", clean_text)[:600]

        # Try to extract a title from the first line
        first_line = clean_text.split("|")[0].strip()[:120]

        opp = Opportunity(
            id=_make_id(kid_id),
            opp_type=OpportunityType.FREELANCE,
            title=first_line or f"HN Hiring: comment #{kid_id}",
            description=clean_text,
            source_url=f"{HN_BASE}/item?id={kid_id}",
            source="hackernews",
            raw_data={
                "thread_url": thread_url,
                "thread_title": thread.get("title", ""),
                "comment_id": kid_id,
                "author": comment.get("by", ""),
            },
        )
        opportunities.append(opp)
        time.sleep(0.1)

    logger.info("HN hiring scan found %d remote/freelance comments", len(opportunities))
    return opportunities


def scan_ask_hn() -> List[Opportunity]:
    """Look for 'Ask HN' posts describing unsolved problems = product ideas."""
    opportunities: List[Opportunity] = []
    new_ids = _get_new_stories(80)

    for sid in new_ids:
        item = _get_item(sid)
        if not item:
            continue
        title = (item.get("title") or "").lower()
        if not title.startswith("ask hn"):
            continue

        combined = title + " " + (item.get("text") or "").lower()
        if not any(kw in combined for kw in ASK_PROBLEM_KEYWORDS):
            continue

        # Filter by engagement
        if item.get("score", 0) < 10:
            continue

        clean_text = re.sub(r"<[^>]+>", " ", item.get("text", "") or "")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()[:600]

        opp = Opportunity(
            id=_make_id(item["id"]),
            opp_type=OpportunityType.REDDIT_PROBLEM,
            title=item.get("title", "")[:140],
            description=clean_text,
            source_url=f"{HN_BASE}/item?id={item['id']}",
            source="hackernews",
            raw_data={
                "score": item.get("score", 0),
                "num_comments": len(item.get("kids", [])),
                "author": item.get("by", ""),
            },
        )
        opportunities.append(opp)
        time.sleep(0.1)

    logger.info("HN Ask scan found %d problem posts", len(opportunities))
    return opportunities


def scan_all() -> List[Opportunity]:
    """Run all HN scanners."""
    results = []
    results.extend(scan_who_is_hiring())
    results.extend(scan_ask_hn())
    return results
