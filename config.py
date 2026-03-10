"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Anthropic ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = "claude-opus-4-6"


# ── User Profile — embedded into every Claude prompt ───────────────────────
# This is the profile that shapes how Claude evaluates and executes.
# The more accurate this is, the better the agent performs for you.
USER_PROFILE = """
ABOUT ME (the person running this agent):

PROFESSIONAL BACKGROUND:
- Sales Engineer at Inbenta — AI-powered search, chatbots, knowledge management for enterprise clients.
  I know how to demo complex AI products, map technical capabilities to business problems, and close deals.
- Sales Engineer at Homegrown Solutions — management consulting firm. Understand enterprise sales cycles,
  stakeholder management, and how to position solutions for C-suite buyers.
- Business Development Intern at Farmers Insurance — pipeline building, prospecting, enterprise BD.

BUILDING / TECH:
- Built CliqeStudents — taught myself to code from scratch to ship it. Proved I can go from zero to product.
- Building uPath.ai — a multi-agent AI platform. Deep experience with LLM orchestration, AI tooling,
  agentic workflows, prompt engineering, and AI product strategy. I understand this space better than
  most because I'm actually building in it, not just reading about it.
- Built Weave — personal information aggregation tool (Lovable). Good at rapid prototyping.
- Built Projo — another project where I deepened coding skills in more detail.

CONTENT / BRAND:
- Active on X/Twitter positioning as a "polymath" — someone who connects dots across domains.
- Obsessed with understanding WHY things work, not just WHAT they do.
- Started as a procrastination coach (no revenue) — content instincts are there, monetisation model wasn't.
- Voice: thoughtful, systems-thinker, builder, genuine. Not hype. Not generic.

TRADING / FINANCE:
- Made meaningful returns in stocks — sold the position. Understand technical analysis, market psychology,
  risk management. Not a paper trader.

SERVICE / HUSTLE ROOTS:
- Bartended at Hotel Santa Barbara — high-pressure, fast-paced, customer-facing. Understand service,
  reading people, staying calm under pressure.

SKILLS INVENTORY (what I can actually deliver):
1. AI product consulting — scope, architect, and ship AI/LLM solutions for SMBs and startups
2. Sales engineering / solution architecture — technical demos, POC builds, enterprise deals
3. Business development — outbound, partnerships, pipeline, BD strategy
4. No-code / low-code SaaS building — Lovable, rapid prototyping
5. Multi-agent AI development — actual code, not just prompts
6. Content strategy and writing — particularly around AI, productivity, building, "how things work"
7. Stock/market analysis — technical + macro lens
8. Management consulting — process improvement, operational scale

WHAT EXCITES ME MOST:
- Work that compounds my AI expertise and builds toward uPath.ai's mission
- Gigs that give me access to new industries or problems I can later productize
- Content opportunities that grow the polymath/builder brand
- Consulting deals where I can charge premium because I'm rare (AI + sales + builder combo)
- Market plays with asymmetric risk/reward and a clear thesis

WHAT TO DEPRIORITISE:
- Generic freelance tasks with no skill growth (e.g., basic data entry, commodity coding)
- High-effort, low-pay work that doesn't compound
- Anything requiring significant upfront capital I don't have
- Projects that distract from uPath.ai without clear ROI

MY HOURLY RATE FLOOR: $100/hr for technical work, $150/hr for AI consulting
MY TARGET MONTHLY INCOME FROM THIS AGENT: $5,000–$15,000 (then scale from there)
"""

# ── Reddit (optional — scanner degrades gracefully without these) ──────────
REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT: str = os.getenv("REDDIT_USER_AGENT", "MoneyAgent/1.0")

# Subreddits to scan for opportunities — tuned for AI builder / sales engineer profile
REDDIT_OPPORTUNITY_SUBS = [
    "forhire",           # People looking to hire freelancers
    "AIAssistants",      # AI product gigs
    "MachineLearning",   # ML consulting requests
    "artificial",        # AI opportunities
    "startups",          # Startup needs (often need sales engineers + AI help)
    "consulting",        # Consulting opportunities
]

REDDIT_PROBLEM_SUBS = [
    "entrepreneur",
    "smallbusiness",
    "startups",
    "SideProject",
    "ChatGPTPromptEngineering",  # AI tool ideas
    "AIAssistants",
    "nocode",
    "SaaS",
    "sales",             # Sales problems → product ideas for uPath.ai
]

# ── Scanner settings ────────────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))
MAX_OPPORTUNITIES_PER_SCAN: int = int(os.getenv("MAX_OPPORTUNITIES_PER_SCAN", "20"))
MIN_SCORE_THRESHOLD: float = float(os.getenv("MIN_SCORE_THRESHOLD", "6.0"))

# ── Output ──────────────────────────────────────────────────────────────────
OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./output")

# ── Market scanner settings ─────────────────────────────────────────────────
MARKET_WATCHLIST = [
    # AI / tech sector — aligned with uPath.ai expertise
    "NVDA", "MSFT", "META", "GOOGL", "AMZN", "AAPL",
    # Broad market
    "SPY", "QQQ",
    # AI-adjacent plays
    "PLTR", "AI", "SOUN", "BBAI", "IONQ",
    # High-beta for asymmetric opportunities
    "TSLA", "COIN",
]
MARKET_MOMENTUM_THRESHOLD: float = 0.03   # 3% gain in past day = interesting
MARKET_VOLUME_SPIKE_FACTOR: float = 2.0   # 2x average volume = notable
