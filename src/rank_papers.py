from __future__ import annotations

import re
from collections import Counter

from .config import PROJECT_CONTEXT, RuntimeConfig
from .models import Paper


ANCHOR_TERMS = [
    "visual working memory",
    "working memory",
    "visual search",
    "fidelity",
    "precision",
    "flexibility",
    "computational model",
    "modeling",
    "predictive coding",
    "egocentric",
    "natural video",
    "intelligence",
    "creativity",
    "structural equation",
]


def select_papers(papers: list[Paper], keywords: list[str], seen_ids: set[str], config: RuntimeConfig) -> list[Paper]:
    ranked: list[Paper] = []
    for paper in papers:
        if paper.stable_id() in seen_ids:
            continue
        if paper.year is not None and paper.year < config.earliest_year:
            continue
        score, terms = score_paper(paper, keywords)
        if score < config.min_score:
            continue
        paper.score = score
        paper.matched_terms = terms
        ranked.append(paper)

    ranked.sort(key=lambda p: (p.score, p.year or 0, len(p.abstract)), reverse=True)
    return ranked[: config.max_papers]


def score_paper(paper: Paper, keywords: list[str]) -> tuple[float, list[str]]:
    text = " ".join([paper.title, paper.abstract, paper.venue]).lower()
    score = 0.0
    matches: Counter[str] = Counter()

    for term in ANCHOR_TERMS:
        if term in text:
            matches[term] += 1
            score += 2.0 if term in paper.title.lower() else 1.0

    for keyword in keywords[:60]:
        if keyword in text:
            matches[keyword] += 1
            score += 0.8

    for project in PROJECT_CONTEXT:
        overlap = _token_overlap(project, text)
        score += min(overlap * 0.35, 2.5)

    if paper.abstract:
        score += 0.5
    if paper.doi:
        score += 0.2
    if paper.year:
        score += max(0, paper.year - 2020) * 0.05

    return score, [term for term, _ in matches.most_common(8)]


def _token_overlap(seed: str, text: str) -> int:
    seed_tokens = set(re.findall(r"[a-z]{5,}", seed.lower()))
    text_tokens = set(re.findall(r"[a-z]{5,}", text.lower()))
    return len(seed_tokens & text_tokens)
