# Job Search Copilot

Pulls job postings relevant to your background, scores/ranks them with Claude, drafts
tailored resume bullets + cover letters, and tracks your application pipeline. A daily
scheduled task fetches and scores new postings each morning and emails you a digest —
nothing here ever auto-applies anywhere; every generated artifact is for you to review.

## Setup

1. **Install dependencies** (Python 3.11+):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

2. **Configure secrets** — copy `.env.example` to `.env` and fill in:
   - `ANTHROPIC_API_KEY` — or run `ant auth login` and leave it unset.
   - `USAJOBS_API_KEY` / `USAJOBS_EMAIL` — free key from https://developer.usajobs.gov/apirequest/. Optional; that source is skipped (with a warning) if unset.
   - `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` — generate an app password at https://myaccount.google.com/apppasswords (requires 2FA already enabled on the account). **Do not use your real Gmail password.**
   - `DIGEST_RECIPIENT_EMAIL` — who gets the morning digest (usually the same as `GMAIL_ADDRESS`).

3. **Edit `config.json`** — already seeded with your profile (resume/portfolio bio, target roles, skills). Add company board slugs you want watched:
   - `greenhouse_slugs`: the token in `boards.greenhouse.io/<TOKEN>` (e.g. `andurilindustries`).
   - `lever_slugs`: the token in `jobs.lever.co/<TOKEN>` (e.g. `shieldai`).
   - `usajobs_keywords`: search terms for federal postings.
   - `score_threshold`: minimum score (0-100) for a posting to appear in the morning digest.

   Note: large primes (Boeing, Lockheed, Northrop, RTX, General Dynamics) run on Workday,
   which has no public search API. Use the "Add a job manually" box in the Streamlit app
   to paste those in instead.

## Running it

**Interactive app** (search, tailor materials, track applications):
```
streamlit run streamlit_app.py
```

**Morning digest, run by hand** (what the scheduled task runs automatically):
```
python -m jobcopilot.digest
```
Logs to `logs/digest.log`.

**Tests**:
```
pytest tests/
```

## Scheduling the daily digest

After verifying `python -m jobcopilot.digest` works and the email arrives, register it
with Windows Task Scheduler (adjust the time as you like — this runs at 7:00 AM daily):

```
schtasks /create /tn "JobSearchCopilot Daily Digest" /tr "C:\Users\Kapil\Documents\Claude\job-search-copilot\scripts\run_digest.bat" /sc daily /st 07:00
```

Check it's registered: `schtasks /query /tn "JobSearchCopilot Daily Digest"`
Run it immediately to test: `schtasks /run /tn "JobSearchCopilot Daily Digest"`
Remove it: `schtasks /delete /tn "JobSearchCopilot Daily Digest" /f`

## How it fits together

- `jobcopilot/sources/` — Greenhouse, Lever, USAJobs API clients + manual job entry, all normalized into a `Job`.
- `jobcopilot/db.py` — SQLite cache of fetched/scored jobs + the applications tracker. Shared by the digest script and the Streamlit app.
- `jobcopilot/scoring.py` / `tailor.py` — Claude API calls (relevance scoring, resume/cover-letter drafting) against your cached profile.
- `jobcopilot/pipeline.py` — shared fetch → dedupe → score orchestration used by both `digest.py` and `streamlit_app.py`.
- `jobcopilot/digest.py` / `email_sender.py` — the automated morning run and its email formatting/sending.
