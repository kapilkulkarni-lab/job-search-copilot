# GNC Job Search -- Supplemental Update, 2026-09-03 (afternoon)

## Headline: GitHub persistence restored, tracker baseline committed

Every daily report since 2026-08-28 flagged the same blocker: this session's
GitHub access returned a 403 ("Resource not accessible by integration") on
every attempted push, so each morning's run reconstructed "previously found"
postings from the prior day's email instead of a saved database. As of this
session, write access works. This run:

1. Fixed a real bug in `jobcopilot/prefilter.py` (flagged in this morning's
   9/3 report): `passes_prefilter()` did an exact-substring match against
   `config.json`'s `target_roles`/`skills` phrases. The phrase
   "guidance navigation and control" doesn't appear verbatim in real postings
   ("Guidance, Navigation & Control (GNC) Engineer"), so the automated
   `python -m jobcopilot.cloud_fetch` path was silently dropping nearly all
   real GNC-titled roles even on the three tracked boards. Fix: normalize
   punctuation (`&` -> `and`, strip commas/parens) before comparing, and add
   `gnc`, `guidance and control(s)`, `flight control` as explicit tokens to
   `config.json`. Verified against real titles pulled live from Anduril's and
   Shield AI's boards -- confirmed the fixed filter now surfaces all of them.
2. Committed `data/tracker.json` as the persisted baseline: 33 currently-open
   GNC/flight-controls/state-estimation/system-safety roles pulled live from
   the three tracked boards (Anduril, Shield AI, Vannevar Labs) in target
   regions, plus a watchlist of 5 companies sourced from manual web sweeps
   over the past 7 days, ranked skill gaps, and region activity notes.
   Future runs should read this file, diff fresh fetches against it, and
   update in place instead of starting over.

## Application status

Checked Gmail again (application/interview/offer/rejection language, plus
greenhouse/lever/myworkday/icims/smartrecruiters senders) and for any reply
to the daily report threads asking for status updates: no hits. Zero
applications on record, unchanged from every prior day.

## New since this morning's 9/3 report

No new postings surfaced in the few hours since the 09:06 UTC report --
expected, given the short gap. This update's value is the persistence fix
above, not new listings.

## Regions with the least activity

Unchanged from the last several days: **DC Metro** remains thinnest, with
activity there skewing toward large primes/contractors (SAIC, Kratos, Ventus
Executive Solutions) rather than startups building air vehicles.
