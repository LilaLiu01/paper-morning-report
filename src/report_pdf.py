from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .config import PACIFIC
from .models import Paper


REPORT_DIR = Path("paper_found")


def write_pdf_report(papers: list[Paper], dry_run: bool = False) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(PACIFIC)
    suffix = "_dry_run" if dry_run else ""
    path = REPORT_DIR / f"paper_report_{now.strftime('%Y-%m-%d_%H%M%S')}{suffix}.pdf"

    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Morning Paper Report",
    )
    styles = _styles()
    story = [
        Paragraph(f"Morning Paper Report - {now.strftime('%A, %B %d, %Y')}", styles["Title"]),
        Paragraph(
            "Recent, non-repeated papers matched to visual working memory, visual search, modeling, "
            "SEM/intelligence/creativity, and egocentric predictive-coding memory themes.",
            styles["Body"],
        ),
        Spacer(1, 0.18 * inch),
    ]

    if dry_run:
        story.append(Paragraph("Dry run: this PDF was generated locally for preview.", styles["Note"]))
        story.append(Spacer(1, 0.12 * inch))

    if not papers:
        story.append(Paragraph("No non-repeated recent papers matched strongly enough today.", styles["Body"]))
    else:
        for index, paper in enumerate(papers, 1):
            story.extend(_paper_flowables(paper, index, styles))

    doc.build(story)
    return path


def _paper_flowables(paper: Paper, index: int, styles: dict[str, ParagraphStyle]) -> list:
    authors = ", ".join(paper.authors[:6]) if paper.authors else "Authors unavailable"
    if len(paper.authors) > 6:
        authors += ", et al."
    summary = summary_from_abstract(paper)
    link = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
    terms = ", ".join(paper.matched_terms[:6]) if paper.matched_terms else "topic match"
    venue = f"{paper.venue}, " if paper.venue else ""
    year = paper.year or "year unavailable"

    flowables = [
        Paragraph(f"{index}. {_xml(paper.title)}", styles["Heading"]),
        Paragraph(f"<b>{_xml(authors)}</b><br/>{_xml(venue)}{_xml(str(year))}", styles["Meta"]),
        Paragraph(f"Source: {_xml(paper.source)}; matched terms: {_xml(terms)}", styles["Meta"]),
    ]
    if link:
        flowables.append(Paragraph(f"Link: <link href=\"{_xml(link)}\">{_xml(link)}</link>", styles["Link"]))
    flowables.extend(
        [
            Paragraph(f"<b>Goal:</b> {_xml(summary['goal'])}", styles["Body"]),
            Paragraph(f"<b>Method:</b> {_xml(summary['method'])}", styles["Body"]),
            Paragraph(f"<b>Results:</b> {_xml(summary['results'])}", styles["Body"]),
            Paragraph(f"<b>Conclusion:</b> {_xml(summary['conclusion'])}", styles["Body"]),
            Spacer(1, 0.18 * inch),
        ]
    )
    return flowables


def summary_from_abstract(paper: Paper) -> dict[str, str]:
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


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            spaceAfter=12,
        ),
        "Heading": ParagraphStyle(
            "PaperHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=5,
            textColor=colors.HexColor("#1f2933"),
        ),
        "Body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            spaceAfter=5,
        ),
        "Meta": ParagraphStyle(
            "ReportMeta",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#52606d"),
            spaceAfter=4,
        ),
        "Link": ParagraphStyle(
            "ReportLink",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1d4ed8"),
            spaceAfter=5,
        ),
        "Note": ParagraphStyle(
            "ReportNote",
            parent=base["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#7c2d12"),
        ),
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


def _xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
