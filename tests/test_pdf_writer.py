from pathlib import Path

from jobcopilot.models import Job, ScoredJob
from jobcopilot.pdf_writer import write_digest_pdf


def make_scored_job(score, key_suffix="1"):
    job = Job(
        source="greenhouse", external_id=key_suffix, title=f"Title {key_suffix}",
        company="Co", location="Remote", url=f"https://example.com/{key_suffix}",
        description="desc",
    )
    return ScoredJob(job=job, score=score, rationale="Good fit", matched_skills=["Python"])


def test_write_digest_pdf_creates_valid_pdf(tmp_path):
    scored = [make_scored_job(90, "1"), make_scored_job(75, "2")]
    path = write_digest_pdf(scored, [], out_dir=str(tmp_path))

    data = Path(path).read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 0


def test_write_digest_pdf_handles_no_matches(tmp_path):
    path = write_digest_pdf([], ["USAJobs skipped: no key"], out_dir=str(tmp_path))
    assert Path(path).read_bytes().startswith(b"%PDF")


def test_write_digest_pdf_uses_out_dir(tmp_path):
    out_dir = tmp_path / "digests"
    path = write_digest_pdf([], [], out_dir=str(out_dir))
    assert Path(path).parent == out_dir
    assert out_dir.exists()
