from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


PACIFIC = ZoneInfo("America/Los_Angeles")

BASE_TOPICS = [
    "visual working memory",
    "working memory representation",
    "working memory modeling",
    "working memory modelling",
    "computational models of working memory",
    "neural networks in working memory",
    "artificial intelligence for human memory",
    "AI models of human memory",
    "visual search",
    "working memory fidelity flexibility visual search",
    "egocentric vision natural video statistics predictive coding memory precision",
]

PROJECT_CONTEXT = [
    "working memory fidelity and flexibility in visual search",
    "working memory representation precision fidelity capacity and resource allocation",
    "neural network models recurrent networks transformers and deep learning models of human working memory",
    "AI for human memory computational cognitive models biologically plausible memory systems",
    "human-aligned egocentric vision benchmark natural video statistics predictive coding memory behavior mnemonic precision strength",
]

LAB_PUBLICATIONS_URL = "https://memory.ucr.edu/publications/"
JOURNAL_CLUB_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1LFhmzMIwVTve9uJWdF-neyr1ECcX8UZdJe7TC7lS02c"
    "/export?format=csv"
)


@dataclass(frozen=True)
class RuntimeConfig:
    max_papers: int = 5
    recent_years: int = 5
    min_score: float = 1.0
    request_timeout: int = 20
    user_agent: str = "LilaLiu01/paper-morning-report (mailto:sliu485@ucr.edu)"

    @property
    def earliest_year(self) -> int:
        return datetime.now(PACIFIC).year - self.recent_years
