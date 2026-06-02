from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from html import escape

from .config import PACIFIC
from .models import Paper


def render_report(papers: list[Paper], dry_run: bool = False) -> str:
    today = datetime.now(PACIFIC).strftime("%A, %B %-d, %Y")
    if not papers:
        body = "<p>No non-repeated recent papers matched strongly enough today.</p>"
    else:
        body = "\n".join(_render_paper(paper, index + 1) for index, paper in enumerate(papers))

    dry_note = "<p><strong>Dry run:</strong> email was not sent.</p>" if dry_run else ""
    return f"""<!doctype html>
<html>
  <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; color: #1f2933;">
    <h2>Morning Paper Report - {escape(today)}</h2>
    <p>Recent, non-repeated papers matched to visual working memory, visual search, modeling, SEM/intelligence/creativity, and egocentric predictive-coding memory themes.</p>
    {dry_note}
    {body}
  </body>
</html>"""


def send_email(html_body: str, paper_count: int) -> None:
    host = _require_env("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = _require_env("SMTP_USERNAME")
    password = _require_env("SMTP_PASSWORD")
    email_from = _require_env("EMAIL_FROM")
    email_to = _require_env("EMAIL_TO")

    msg = EmailMessage()
    msg["Subject"] = f"Morning paper report: {paper_count} selected paper{'s' if paper_count != 1 else ''}"
    msg["From"] = email_from
    msg["To"] = email_to
    msg.set_content("Your email client does not support HTML. Please view this report in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(msg)


def _render_paper(paper: Paper, index: int) -> str:
    authors = ", ".join(paper.authors[:6]) if paper.authors else "Authors unavailable"
    if len(paper.authors) > 6:
        authors += ", et al."
    summary = _summary_from_abstract(paper)
    link = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
    link_html = f'<p><a href="{escape(link)}">{escape(link)}</a></p>' if link else ""
    terms = ", ".join(paper.matched_terms[:6]) if paper.matched_terms else "topic match"
    venue = f"{paper.venue}, " if paper.venue else ""
    year = paper.year or "year unavailable"

    return f"""
    <section style="margin: 0 0 28px 0; padding-top: 8px; border-top: 1px solid #d9e2ec;">
      <h3>{index}. {escape(paper.title)}</h3>
      <p><strong>{escape(authors)}</strong><br>{escape(venue)}{escape(str(year))}<br>Source: {escape(paper.source)}; matched terms: {escape(terms)}</p>
      {link_html}
      <p><strong>Goal:</strong> {escape(summary['goal'])}</p>
      <p><strong>Method:</strong> {escape(summary['method'])}</p>
      <p><strong>Results:</strong> {escape(summary['results'])}</p>
      <p><strong>Conclusion:</strong> {escape(summary['conclusion'])}</p>
    </section>
    """


def _summary_from_abstract(paper: Paper) -> dict[str, str]:
    abstract = paper.abstract.strip()
    if not abstract:
        return {
            "goal": "The title and metadata suggest relevance to Lila's working-memory and attention topics, but no abstract was available from the source API.",
            "method": "Method details were not available in the retrieved metadata.",
            "results": "Result details were not available in the retrieved metadata.",
            "conclusion": "Open the linked record to inspect the full abstract or paper before journal-club use.",
        }

    sentences = _split_sentences(abstract)
    first = sentences[0] if sentences else abstract
    middle = " ".join(sentences[1:3]) if len(sentences) > 2 else first
    late = " ".join(sentences[-2:]) if len(sentences) > 1 else first

    return {
        "goal": _trim(first, 420),
        "method": _trim(_find_sentence(sentences, ["participant", "experiment", "model", "dataset", "analysis", "measured"]) or middle, 420),
        "results": _trim(_find_sentence(sentences, ["found", "show", "result", "revealed", "improved", "predicted"]) or late, 420),
        "conclusion": _trim(_find_sentence(sentences, ["suggest", "conclude", "therefore", "indicate", "support"]) or late, 420),
    }


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in text.replace("\n", " ").split(". ") if part.strip()]


def _find_sentence(sentences: list[str], cues: list[str]) -> str:
    for sentence in sentences:
        lowered = sentence.lower()
        if any(cue in lowered for cue in cues):
            return sentence
    return ""


def _trim(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 3].rsplit(" ", 1)[0] + "..."


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
