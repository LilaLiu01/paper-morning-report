from __future__ import annotations

import html
import os
import re
from datetime import datetime
from typing import Iterable
from urllib.parse import quote_plus
from xml.etree import ElementTree

import feedparser
import requests
from dateutil.parser import parse as parse_date

from .config import RuntimeConfig
from .models import Paper


def search_all_sources(keywords: list[str], config: RuntimeConfig) -> list[Paper]:
    queries = _make_queries(keywords)
    papers: list[Paper] = []
    for query in queries:
        papers.extend(search_arxiv(query, config))
        papers.extend(search_pubmed(query, config))
        papers.extend(search_europe_pmc(query, config))
        papers.extend(search_crossref(query, config))
        papers.extend(search_semantic_scholar(query, config))
        papers.extend(search_osf(query, config))
        papers.extend(search_google_scholar_serpapi(query, config))
    return _dedupe_papers(papers)


def search_arxiv(query: str, config: RuntimeConfig) -> list[Paper]:
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query=all:{quote_plus(query)}&start=0&max_results=20"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    feed = _get_feed(url, config)
    papers = []
    for entry in feed.entries:
        published = getattr(entry, "published", "")
        year = _year_from_date(published)
        papers.append(Paper(
            title=_clean(getattr(entry, "title", "")),
            source="arXiv",
            year=year,
            authors=[a.name for a in getattr(entry, "authors", []) if getattr(a, "name", "")],
            abstract=_clean(getattr(entry, "summary", "")),
            url=getattr(entry, "link", ""),
            published=published,
            paper_id=getattr(entry, "id", ""),
        ))
    return papers


def search_pubmed(query: str, config: RuntimeConfig) -> list[Paper]:
    term = f'({query}) AND ("{config.earliest_year}"[Date - Publication] : "3000"[Date - Publication])'
    ids_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    try:
        ids_response = requests.get(
            ids_url,
            params={"db": "pubmed", "term": term, "retmode": "json", "retmax": 20, "sort": "relevance"},
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        ids_response.raise_for_status()
        ids = ids_response.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []
        summary_response = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        summary_response.raise_for_status()
    except requests.RequestException:
        return []

    data = summary_response.json().get("result", {})
    papers = []
    for pmid in ids:
        item = data.get(pmid, {})
        pubdate = item.get("pubdate", "")
        papers.append(Paper(
            title=_clean(item.get("title", "")),
            source="PubMed",
            year=_year_from_date(pubdate),
            authors=[author.get("name", "") for author in item.get("authors", [])[:8] if author.get("name")],
            abstract="",
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            venue=item.get("fulljournalname", ""),
            published=pubdate,
            paper_id=pmid,
        ))
    return papers


def search_europe_pmc(query: str, config: RuntimeConfig) -> list[Paper]:
    try:
        response = requests.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": f'({query}) FIRST_PDATE:[{config.earliest_year}-01-01 TO 3000-12-31]',
                "format": "json",
                "pageSize": 20,
            },
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in response.json().get("resultList", {}).get("result", []):
        papers.append(Paper(
            title=_clean(item.get("title", "")),
            source="Europe PMC",
            year=_safe_int(item.get("pubYear")),
            authors=_split_authors(item.get("authorString", "")),
            abstract=_clean(item.get("abstractText", "")),
            url=item.get("doi") and f"https://doi.org/{item['doi']}" or item.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url", ""),
            doi=item.get("doi", ""),
            venue=item.get("journalTitle", ""),
            published=item.get("firstPublicationDate", ""),
            paper_id=item.get("id", ""),
        ))
    return papers


def search_crossref(query: str, config: RuntimeConfig) -> list[Paper]:
    try:
        response = requests.get(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": query,
                "filter": f"from-pub-date:{config.earliest_year}-01-01",
                "rows": 20,
            },
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in response.json().get("message", {}).get("items", []):
        date_parts = item.get("published-print", item.get("published-online", item.get("created", {}))).get("date-parts", [[]])
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        papers.append(Paper(
            title=_clean(" ".join(item.get("title", [])[:1])),
            source="Crossref",
            year=_safe_int(year),
            authors=[_format_crossref_author(a) for a in item.get("author", [])[:8]],
            abstract=_clean(re.sub("<[^>]+>", " ", item.get("abstract", ""))),
            url=item.get("URL", ""),
            doi=item.get("DOI", ""),
            venue="; ".join(item.get("container-title", [])[:1]),
            published=str(year or ""),
            paper_id=item.get("DOI", ""),
        ))
    return papers


def search_semantic_scholar(query: str, config: RuntimeConfig) -> list[Paper]:
    try:
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "limit": 20,
                "year": f"{config.earliest_year}-",
                "fields": "title,abstract,authors,year,venue,url,externalIds,publicationDate",
            },
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in response.json().get("data", []):
        external = item.get("externalIds") or {}
        papers.append(Paper(
            title=_clean(item.get("title", "")),
            source="Semantic Scholar",
            year=_safe_int(item.get("year")),
            authors=[a.get("name", "") for a in item.get("authors", [])[:8] if a.get("name")],
            abstract=_clean(item.get("abstract", "")),
            url=item.get("url", ""),
            doi=external.get("DOI", ""),
            venue=item.get("venue", ""),
            published=item.get("publicationDate", ""),
            paper_id=item.get("paperId", ""),
        ))
    return papers


def search_osf(query: str, config: RuntimeConfig) -> list[Paper]:
    try:
        response = requests.get(
            "https://api.osf.io/v2/preprints/",
            params={
                "filter[title]": query,
                "page[size]": 20,
            },
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in response.json().get("data", []):
        attrs = item.get("attributes", {})
        published = attrs.get("date_published") or attrs.get("date_created", "")
        papers.append(Paper(
            title=_clean(attrs.get("title", "")),
            source="OSF/PsyArXiv",
            year=_year_from_date(published),
            abstract=_clean(attrs.get("description", "")),
            url=item.get("links", {}).get("html", ""),
            published=published,
            paper_id=item.get("id", ""),
        ))
    return papers


def search_google_scholar_serpapi(query: str, config: RuntimeConfig) -> list[Paper]:
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_scholar",
                "q": query,
                "as_ylo": config.earliest_year,
                "api_key": api_key,
                "num": 20,
            },
            timeout=config.request_timeout,
            headers={"User-Agent": config.user_agent},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    papers = []
    for item in response.json().get("organic_results", []):
        publication_info = item.get("publication_info", {})
        summary = publication_info.get("summary", "")
        papers.append(Paper(
            title=_clean(item.get("title", "")),
            source="Google Scholar",
            year=_year_from_date(summary),
            authors=_split_authors(summary.split(" - ")[0]),
            abstract=_clean(item.get("snippet", "")),
            url=item.get("link", ""),
            venue=summary,
            paper_id=item.get("result_id", ""),
        ))
    return papers


def _make_queries(keywords: list[str]) -> list[str]:
    preferred = keywords[:12]
    focused = [
        "visual working memory visual search",
        "working memory fidelity precision",
        "working memory representation",
        "working memory computational model",
        "working memory modelling neural network",
        "neural networks human working memory",
        "artificial intelligence human memory",
        "AI models human memory",
        "predictive coding memory natural video egocentric vision",
    ]
    return list(dict.fromkeys(focused + preferred))[:18]


def _dedupe_papers(papers: Iterable[Paper]) -> list[Paper]:
    deduped: dict[str, Paper] = {}
    for paper in papers:
        if not paper.title:
            continue
        key = paper.stable_id()
        existing = deduped.get(key)
        if existing is None or (len(paper.abstract) > len(existing.abstract)):
            deduped[key] = paper
    return list(deduped.values())


def _get_feed(url: str, config: RuntimeConfig):
    try:
        response = requests.get(url, timeout=config.request_timeout, headers={"User-Agent": config.user_agent})
        response.raise_for_status()
        return feedparser.parse(response.text)
    except requests.RequestException:
        return feedparser.parse("")


def _clean(value: str) -> str:
    return html.unescape(" ".join(str(value or "").split()))


def _year_from_date(value: str) -> int | None:
    if not value:
        return None
    match = re.search(r"(20\d{2})", str(value))
    if match:
        return int(match.group(1))
    try:
        return parse_date(str(value), fuzzy=True).year
    except (ValueError, TypeError, OverflowError):
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _split_authors(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip(" .") for part in re.split(r",|;| and ", value) if part.strip()][:8]


def _format_crossref_author(author: dict) -> str:
    return " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part).strip()
