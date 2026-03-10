"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Anthropic ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = "claude-opus-4-6"

# ── Reddit (optional — scanner degrades gracefully without these) ──────────
REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "MoneyAgent/1.0")

# Subreddits to scan for opportunities
REDDIT_OPPORTUNITY_SUBS = [
    "forhire",           # People looking to hire freelancers
    "slavelabour",       # Small paid tasks
    "Jobs4Bitcoins",     # Crypto-paid gigs
    "entrepreneur",      # Business problems / ideas
    "smallbusiness",     # Small biz pain points
    "SideProject",       # Ideas and problems
    "startups",          # Startup needs
    "unresolvedmysteries", # Just kidding — removed
]

REDDIT_PROBLEM_SUBS = [
    "entrepreneur",
    "smallbusiness",
    "startups",
    "SideProject",
    "webdev",
    "learnprogramming",
]

# ── Scanner settings ────────────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))
MAX_OPPORTUNITIES_PER_SCAN: int = int(os.getenv("MAX_OPPORTUNITIES_PER_SCAN", "20"))
MIN_SCORE_THRESHOLD: float = float(os.getenv("MIN_SCORE_THRESHOLD", "6.0"))

# ── Output ──────────────────────────────────────────────────────────────────
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")

# ── Market scanner settings ─────────────────────────────────────────────────
MARKET_WATCHLIST = [
    # A starter watchlist; agent will also find its own picks
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL",
]
MARKET_MOMENTUM_THRESHOLD: float = 0.03   # 3% gain in past day = interesting
MARKET_VOLUME_SPIKE_FACTOR: float = 2.0   # 2x average volume = notable
