"""Core data models for the autonomous money agent."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class OpportunityType(Enum):
    FREELANCE = "freelance"
    REDDIT_PROBLEM = "reddit_problem"
    MARKET = "market"
    CONTENT = "content"


class OpportunityStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class Action:
    """A specific action the agent proposes to take on an opportunity."""
    action_type: str  # draft_proposal | write_content | trade_alert | build_tool
    title: str
    content: str          # Full generated content (proposal text, article, etc.)
    instructions: str     # Step-by-step instructions for the user to follow
    output_file: str = "" # Where the content will be saved
    estimated_time: str = ""
    tools_needed: List[str] = field(default_factory=list)


@dataclass
class Opportunity:
    """A money-making opportunity discovered by the agent."""
    id: str
    opp_type: OpportunityType
    title: str
    description: str
    source_url: str
    source: str           # reddit | hackernews | market | manual
    raw_data: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.now)
    status: OpportunityStatus = OpportunityStatus.PENDING

    # Set by evaluator
    score: float = 0.0                   # 0-10 overall score
    estimated_earnings: str = ""         # e.g. "$200-$500"
    effort_level: str = ""               # low | medium | high
    time_to_money: str = ""              # e.g. "1-3 days"
    reasoning: str = ""                  # Why this is a good opportunity
    tags: List[str] = field(default_factory=list)

    # Set after approval + execution
    proposed_action: Optional[Action] = None
    execution_result: str = ""

    def summary_line(self) -> str:
        """One-line summary for display."""
        score_str = f"[{self.score:.1f}/10]" if self.score > 0 else ""
        earnings = f" | {self.estimated_earnings}" if self.estimated_earnings else ""
        return f"{score_str} {self.title}{earnings}"
