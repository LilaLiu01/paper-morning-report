from __future__ import annotations

import csv
import io
import re
from collections import Counter

import requests
from bs4 import BeautifulSoup

from .config import BASE_TOPICS, JOURNAL_CLUB_CSV_URL, LAB_PUBLICATIONS_URL, PROJECT_CONTEXT, RuntimeConfig


STOPWORDS = {
    "about", "after", "also", "among", "based", "being", "between", "during",
    "from", "have", "into", "more", "other", "paper", "papers", "than", "that",
    "their", "these", "this", "through", "using", "with", "within", "without",
    "memory", "working", "visual",
}


def build_keywords(config: RuntimeConfig) -> list[str]:
    phrases = list(BASE_TOPICS) + list(PROJECT_CONTEXT)
    phrases.extend(_keywords_from_lab_publications(config))
    phrases.extend(_keywords_from_journal_club(config))
    return _dedupe_ranked(phrases)


def _keywords_from_lab_publications(config: RuntimeConfig) -> list[str]:
    try:
        response = requests.get(
            LAB_PUBLICATIONS_URL,
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    return _extract_phrases(text)


def _keywords_from_journal_club(config: RuntimeConfig) -> list[str]:
    try:
        response = requests.get(
            JOURNAL_CLUB_CSV_URL,
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    rows = list(csv.reader(io.StringIO(response.text)))
    all_text = " ".join(" ".join(row) for row in rows)
    lila_rows = " ".join(" ".join(row) for row in rows if any("lila" in cell.lower() for cell in row))
    phrases = _extract_phrases(all_text)
    phrases.extend(_extract_phrases(lila_rows))
    return phrases


def _extract_phrases(text: str) -> list[str]:
    lowered = re.sub(r"[^a-zA-Z0-9\s-]", " ", text.lower())
    words = [w for w in lowered.split() if len(w) > 3 and w not in STOPWORDS]
    counts = Counter()
    for n in (2, 3, 4):
        for i in range(0, max(0, len(words) - n + 1)):
            phrase = " ".join(words[i : i + n])
            if any(anchor in phrase for anchor in ("attention", "search", "precision", "fidelity", "model", "egocentric", "prediction", "intelligence", "creativity")):
                counts[phrase] += 1
    return [phrase for phrase, _ in counts.most_common(30)]


def _dedupe_ranked(phrases: list[str]) -> list[str]:
    seen: set[str] = set()
    ranked: list[str] = []
    for phrase in phrases:
        clean = " ".join(phrase.lower().split())
        if len(clean) < 4 or clean in seen:
            continue
        seen.add(clean)
        ranked.append(clean)
    return ranked[:80]
