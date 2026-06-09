from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import PACIFIC, RuntimeConfig
from .keyword_sources import build_keywords
from .rank_papers import select_papers
from .report_pdf import write_pdf_report
from .search_sources import search_all_sources


SEEN_PATH = Path("data/seen_papers.json")


def main() -> None:
    args = parse_args()
    now = parse_report_date(args.report_date) or datetime.now(PACIFIC)
    force_run = args.force or os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
    scheduled_run = is_scheduled_report_run(now)
    if not force_run and not scheduled_run and not _is_report_time(now):
        print(f"Not report time in America/Los_Angeles: {now.isoformat()}")
        return
    if not force_run and report_exists_for_date(now):
        print(f"Report already exists for {now.date()} in paper_found/.")
        return

    config = RuntimeConfig()
    seen_ids = load_seen_ids()
    keywords = build_keywords(config)
    candidates = search_all_sources(keywords, config)
    selected = select_papers(candidates, keywords, seen_ids, config)
    pdf_path = write_pdf_report(selected, dry_run=args.dry_run, report_time=now)
    print(f"Selected {len(selected)} papers. Wrote {pdf_path}")

    if selected and not args.no_update_seen:
        save_seen_ids(seen_ids | {paper.stable_id() for paper in selected})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Run even when it is not Tuesday/Friday 8 AM Pacific.")
    parser.add_argument("--dry-run", action="store_true", help="Write a preview PDF with a dry-run suffix.")
    parser.add_argument("--no-update-seen", action="store_true", help="Do not update data/seen_papers.json.")
    parser.add_argument("--report-date", help="Override the report date as YYYY-MM-DD for make-up reports.")
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


def parse_report_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").replace(hour=8, minute=0, second=0, tzinfo=PACIFIC)


def report_exists_for_date(now: datetime) -> bool:
    report_dir = Path("paper_found")
    return any(report_dir.glob(f"paper_report_{now.strftime('%Y-%m-%d')}_*.pdf"))


def is_scheduled_report_run(now: datetime) -> bool:
    if os.getenv("GITHUB_EVENT_NAME") != "schedule":
        return False
    if now.weekday() not in {1, 4}:
        return False
    if now.hour < 8 or now.hour > 12:
        return False

    event_schedule = os.getenv("GITHUB_EVENT_SCHEDULE", "")
    scheduled_hours = _cron_hours(event_schedule)
    if not scheduled_hours:
        return _is_report_time(now)

    candidate_utc_hours = {
        datetime(now.year, now.month, now.day, 8, tzinfo=PACIFIC)
        .astimezone(timezone.utc)
        .hour,
        15,
        16,
    }
    return bool(candidate_utc_hours & scheduled_hours)


def _cron_hours(cron: str) -> set[int]:
    fields = cron.split()
    if len(fields) < 2:
        return set()
    hours: set[int] = set()
    for part in fields[1].split(","):
        try:
            hours.add(int(part))
        except ValueError:
            continue
    return hours


def _is_report_time(now: datetime) -> bool:
    return now.weekday() in {1, 4} and now.hour == 8


if __name__ == "__main__":
    main()
