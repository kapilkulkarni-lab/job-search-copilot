# Job Search Copilot

Pulls job postings relevant to your background, scores/ranks them with Claude, drafts
tailored resume bullets + cover letters, and tracks your application pipeline. Nothing
here ever auto-applies anywhere; every generated artifact is for you to review.

There are two ways the daily digest runs — pick one (or both):
- **Local Task Scheduler**: a script on your PC, run daily, using your Claude API key
  and Gmail SMTP. Only runs while your PC is on at that time.
- **Cloud routine**: a scheduled Claude Code cloud agent (`https://claude.ai/code/routines/trig_01FRXDysfJz2GRrfYQaBwzM8`)
  that runs regardless of PC state, using your Claude subscription and the Gmail API.

## Setup — local path

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

### Running the local path

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

### Scheduling the local digest

After verifying `python -m jobcopilot.digest` works and the email arrives, register it
with Windows Task Scheduler (adjust the time as you like — this runs at 7:00 AM daily):

```
schtasks /create /tn "JobSearchCopilot Daily Digest" /tr "C:\Users\Kapil\Documents\Claude\job-search-copilot\scripts\run_digest.bat" /sc daily /st 07:00
```

Check it's registered: `schtasks /query /tn "JobSearchCopilot Daily Digest"`
Run it immediately to test: `schtasks /run /tn "JobSearchCopilot Daily Digest"`
Remove it: `schtasks /delete /tn "JobSearchCopilot Daily Digest" /f`

## Setup — cloud routine path

The routine (`Job Search Copilot - Daily Digest`, daily 11:00 UTC / 7:00 AM ET) clones
`kapilkulkarni-lab/job-search-copilot` into an Anthropic-hosted sandbox, runs
`jobcopilot.cloud_fetch` (plain fetch + keyword prefilter, no Claude API call), then the
agent itself scores each posting against `config.json`'s profile as part of its own
reasoning, and sends the digest via the Gmail API (`jobcopilot.cloud_send` /
`gmail_api_sender.py`) — SMTP is used for the local path but appears to be blocked by
the sandbox's network policy, so the cloud path uses HTTPS instead.

Things that had to be configured once, outside this repo, for the routine to work:
- **GitHub connection**: claude.ai needs its own GitHub connection (separate from local
  `gh` CLI), and the Claude GitHub App needs explicit access to this repo —
  github.com/settings/installations → the Claude app → repository access.
- **Network access**: the sandbox environment needed an outbound allowlist covering
  `boards-api.greenhouse.io`, `api.lever.co`, `data.usajobs.gov`, and the Gmail API/OAuth
  hosts (`oauth2.googleapis.com`, `gmail.googleapis.com`) — configured on the routine's
  environment settings at claude.ai/code.
- **Gmail API OAuth** (one-time, local):
  1. In Google Cloud Console, create/select a project and enable the **Gmail API**.
  2. Configure the OAuth consent screen: External, Testing mode (fine for personal use —
     add your own Gmail as a test user; no Google verification needed).
  3. Create an OAuth client ID of type **Desktop app**; note its client ID + secret.
  4. Run locally: `pip install google-auth-oauthlib` then
     `python scripts/gmail_oauth_setup.py --client-id ... --client-secret ...`
     — this opens a browser for one-time consent and prints `GMAIL_CLIENT_ID`,
     `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`.
  5. Set those three plus `GMAIL_ADDRESS` and `DIGEST_RECIPIENT_EMAIL` as **secrets on
     the routine's cloud environment** (claude.ai/code environment settings) — the
     sandbox doesn't read your local `.env`.

### Managing the routine

- View/edit: `https://claude.ai/code/routines/trig_01FRXDysfJz2GRrfYQaBwzM8`
- Run it manually any time from that page, or ask Claude Code to run it via the
  `schedule` skill / `RemoteTrigger` tool.

## How it fits together

- `jobcopilot/sources/` — Greenhouse, Lever, USAJobs API clients + manual job entry, all normalized into a `Job`.
- `jobcopilot/db.py` — SQLite cache of fetched/scored jobs + the applications tracker. Local path only (the cloud sandbox has no persistent disk between runs, so `cloud_fetch.py` filters to recently-posted jobs instead of deduping against a database).
- `jobcopilot/scoring.py` / `tailor.py` — Claude API calls (relevance scoring, resume/cover-letter drafting) against your cached profile. Local path only.
- `jobcopilot/pipeline.py` — shared fetch → dedupe → score orchestration used by `digest.py` and `streamlit_app.py`.
- `jobcopilot/digest.py` / `email_sender.py` — local automated morning run (SMTP).
- `jobcopilot/cloud_fetch.py` / `cloud_send.py` / `gmail_api_sender.py` — the stateless cloud-routine variant (no `anthropic` package dependency — the routine's own reasoning does the scoring; sends via the Gmail API over HTTPS).
