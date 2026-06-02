# Morning Paper Report

Scheduled GitHub Actions pipeline that emails Lila a Tuesday/Friday 8:00 AM Pacific report of recent papers related to visual working memory, modeling working memory, visual search, and current project themes.

The report selects at most 5 papers from the last 5 years and stores selected paper IDs in `data/seen_papers.json` so future reports do not repeat the same papers.

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

Create these repository secrets in GitHub:

| Secret | Example |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | your Gmail address |
| `SMTP_PASSWORD` | Gmail app password, not your normal account password |
| `EMAIL_FROM` | your Gmail address |
| `EMAIL_TO` | `sliu485@ucr.edu` |
| `SERPAPI_API_KEY` | optional |

For Gmail, create an app password in your Google account security settings. Do not commit passwords to this repository.

## Schedule

The workflow runs on Tuesdays and Fridays. Because GitHub cron uses UTC, the workflow has two UTC schedules and `src/main.py` exits unless the current Los Angeles time is Tuesday or Friday at 8:00 AM.

You can also run it manually from the GitHub Actions tab with **Run workflow**.

## Local Test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m src.main --force --dry-run
```

Remove `--dry-run` only when email secrets are configured.
