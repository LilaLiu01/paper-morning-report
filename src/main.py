from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .config import PACIFIC, RuntimeConfig
from .email_report import render_report, send_email
from .keyword_sources import build_keywords
from .rank_papers import select_papers
from .search_sources import search_all_sources


SEEN_PATH = Path("data/seen_papers.json")


def main() -> None:
    args = parse_args()
    now = datetime.now(PACIFIC)
    if not args.force and not _is_report_time(now):
        print(f"Not report time in America/Los_Angeles: {now.isoformat()}")
        return

    config = RuntimeConfig()
    seen_ids = load_seen_ids()
    keywords = build_keywords(config)
    candidates = search_all_sources(keywords, config)
    selected = select_papers(candidates, keywords, seen_ids, config)
    html_body = render_report(selected, dry_run=args.dry_run)

    if args.dry_run:
        Path("report_preview.html").write_text(html_body, encoding="utf-8")
        print(f"Dry run selected {len(selected)} papers. Wrote report_preview.html")
    else:
        send_email(html_body, len(selected))
        print(f"Sent report with {len(selected)} papers.")

    if selected and not args.no_update_seen:
        save_seen_ids(seen_ids | {paper.stable_id() for paper in selected})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Run even when it is not Tuesday/Friday 8 AM Pacific.")
    parser.add_argument("--dry-run", action="store_true", help="Write report_preview.html instead of sending email.")
    parser.add_argument("--no-update-seen", action="store_true", help="Do not update data/seen_papers.json.")
    return parser.parse_args()


def load_seen_ids() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return set(data.get("seen", []))


def save_seen_ids(seen_ids: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seen": sorted(seen_ids)}
    SEEN_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _is_report_time(now: datetime) -> bool:
    return now.weekday() in {1, 4} and now.hour == 8


if __name__ == "__main__":
    main()
