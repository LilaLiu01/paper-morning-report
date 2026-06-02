# Morning Paper Report

Scheduled GitHub Actions pipeline that saves a Tuesday/Friday 8:00 AM Pacific PDF report of recent papers related to visual working memory, modeling working memory, visual search, and current project themes.

The report selects at most 5 papers from the last 5 years, writes the PDF into `paper_found/`, and stores selected paper IDs in `data/seen_papers.json` so future reports do not repeat the same papers.

## Sources

- PubMed through NCBI E-utilities
- Europe PMC
- arXiv
- OSF preprints
- Crossref
- Semantic Scholar
- Optional Google Scholar through SerpAPI, if `SERPAPI_API_KEY` is configured
- UCR Memory and Cognition Lab publications page for keyword expansion
- Public CSV export of the journal club Google Sheet for keyword expansion

## GitHub Secrets

No email secrets are needed. The only optional secret is:

| Secret | Example |
| --- | --- |
| `SERPAPI_API_KEY` | optional |

## Schedule

The workflow runs on Tuesdays and Fridays. Because GitHub cron uses UTC, the workflow has UTC schedules that cover the 8:00 AM Pacific hour. `src/main.py` exits unless the current Los Angeles time is Tuesday or Friday at 8 AM, and it will create at most one report per local date.

You can also run it manually from the GitHub Actions tab with **Run workflow**.

## Local Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --force --dry-run
```
