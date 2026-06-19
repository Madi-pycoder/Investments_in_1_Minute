from dataclasses import dataclass
from typing import Optional

@dataclass
class InsightCard:
    id: str
    category: str
    priority: int
    severity: str
    emoji: str
    headline: str
    summary: str
    why_it_matters: str
    impact: Optional[str] = None
    action_label: Optional[str] = None
    callback: Optional[str] = None