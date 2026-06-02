from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Paper:
    title: str
    source: str
    year: int | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    url: str = ""
    doi: str = ""
    venue: str = ""
    published: str = ""
    paper_id: str = ""
    score: float = 0.0
    matched_terms: list[str] = field(default_factory=list)

    def stable_id(self) -> str:
        if self.doi:
            return "doi:" + self.doi.lower().strip()
        if self.paper_id:
            return self.source.lower() + ":" + self.paper_id.lower().strip()
        normalized_title = " ".join(self.title.lower().split())
        return "title:" + normalized_title
