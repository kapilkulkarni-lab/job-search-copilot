# Job Search Copilot

Pulls job postings relevant to your background, scores/ranks them with Claude, drafts
tailored resume bullets + cover letters, and tracks your application pipeline. Nothing
here ever auto-applies anywhere; every generated artifact is for you to review.

There are two ways the daily digest runs:
- **Local Task Scheduler**: a script on your PC, run daily, writes a PDF to
  `data/digests/YYYY-MM-DD.pdf`. Only runs while your PC is on at that time.
- **Cloud routine**: a scheduled Claude Code cloud agent
  (`https://claude.ai/code/routines/trig_01FRXDysfJz2GRrfYQaBwzM8`) that runs daily
  regardless of PC state and reports its findings directly in the routine's session —
  check it on claude.ai each morning.

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

3. **Edit `config.json`** — already seeded with your profile (resume/portfolio bio, target roles, skills). Add company board slugs you want watched:
   - `greenhouse_slugs`: the token in `boards.greenhouse.io/<TOKEN>` (e.g. `andurilindustries`).
   - `lever_slugs`: the token in `jobs.lever.co/<TOKEN>` (e.g. `shieldai`).
   - `usajobs_keywords`: search terms for federal postings.
   - `score_threshold`: minimum score (0-100) for a posting to appear in the digest PDF.

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
Writes `data/digests/YYYY-MM-DD.pdf` and logs to `logs/digest.log`.

**Tests**:
```
pytest tests/
```

### Scheduling the local digest

After verifying `python -m jobcopilot.digest` works and the PDF looks right, register it
with Windows Task Scheduler (adjust the time as you like — this runs at 7:00 AM daily):

```
schtasks /create /tn "JobSearchCopilot Daily Digest" /tr "C:\Users\Kapil\Documents\Claude\job-search-copilot\scripts\run_digest.bat" /sc daily /st 07:00
```

Check it's registered: `schtasks /query /tn "JobSearchCopilot Daily Digest"`
Run it immediately to test: `schtasks /run /tn "JobSearchCopilot Daily Digest"`
Remove it: `schtasks /delete /tn "JobSearchCopilot Daily Digest" /f`

## The cloud routine path

The routine (`Job Search Copilot - Daily Digest`, daily 11:00 UTC / 7:00 AM ET) clones
`kapilkulkarni-lab/job-search-copilot` into an Anthropic-hosted sandbox, runs
`jobcopilot.cloud_fetch` (plain fetch + keyword prefilter, no Claude API call, no
persistent database — it filters to postings from the last ~30 hours instead), then the
agent itself scores each posting against `config.json`'s profile as part of its own
reasoning. It does not send anything anywhere — its final message in the session *is*
the digest, so check `https://claude.ai/code/routines/trig_01FRXDysfJz2GRrfYQaBwzM8`
each morning to read it. (We tried emailing from the cloud sandbox first — SMTP was
blocked by its network policy and the available MCP-style connectors weren't attachable
to routines — so this local-PDF + cloud-report split turned out simplest.)

Required one-time setup, outside this repo:
- **GitHub connection**: claude.ai needs its own GitHub connection (separate from local
  `gh` CLI), and the Claude GitHub App needs explicit access to this repo —
  github.com/settings/installations → the Claude app → repository access.
- **Network access**: the sandbox environment needed an outbound allowlist covering
  `boards-api.greenhouse.io`, `api.lever.co`, and `data.usajobs.gov` — configured on the
  routine's environment settings at claude.ai/code.

### Managing the routine

- View/edit: `https://claude.ai/code/routines/trig_01FRXDysfJz2GRrfYQaBwzM8`
- Run it manually any time from that page, or ask Claude Code to run it via the
  `schedule` skill / `RemoteTrigger` tool.

## How it fits together

- `jobcopilot/sources/` — Greenhouse, Lever, USAJobs API clients + manual job entry, all normalized into a `Job`.
- `jobcopilot/db.py` — SQLite cache of fetched/scored jobs + the applications tracker. Local path only (the cloud sandbox has no persistent disk between runs, so `cloud_fetch.py` filters to recently-posted jobs instead of deduping against a database).
- `jobcopilot/scoring.py` / `tailor.py` — Claude API calls (relevance scoring, resume/cover-letter drafting) against your cached profile. Local path only.
- `jobcopilot/pipeline.py` — shared fetch → dedupe → score orchestration used by `digest.py` and `streamlit_app.py`.
- `jobcopilot/digest.py` / `pdf_writer.py` — the local automated morning run and its PDF output.
- `jobcopilot/cloud_fetch.py` — the stateless cloud-routine fetch+prefilter step (no `anthropic` package dependency — the routine's own reasoning does the scoring and reports it directly, no separate send step).
