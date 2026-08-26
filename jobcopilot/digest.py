"""Entry point for the automated morning run: fetch postings, score the new ones,
email a ranked digest. Invoked by Windows Task Scheduler via scripts/run_digest.bat.

Usage: python -m jobcopilot.digest
"""
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from jobcopilot import email_sender, pipeline
from jobcopilot.claude_client import get_client

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "digest.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    load_dotenv()
    _setup_logging()
    log = logging.getLogger("digest")

    config = pipeline.load_config()
    conn = pipeline.get_connection(config)

    log.info("Fetching postings...")
    jobs, fetch_warnings = pipeline.fetch_all_jobs(config)
    log.info("Fetched %d posting(s) across all sources.", len(jobs))

    client = get_client()
    scored, score_warnings = pipeline.ingest_and_score_new(
        conn, client, config["profile"], jobs
    )
    log.info("Scored %d new posting(s).", len(scored))

    warnings = fetch_warnings + score_warnings
    for w in warnings:
        log.warning(w)

    threshold = config.get("score_threshold", 70)
    to_send = [sj for sj in scored if sj.score >= threshold]
    log.info("%d posting(s) meet the score threshold (%d).", len(to_send), threshold)

    try:
        email_sender.send_digest(to_send, warnings)
        log.info("Digest email sent (%d posting(s)).", len(to_send))
    except email_sender.EmailNotConfigured as e:
        log.error("Digest not sent: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
