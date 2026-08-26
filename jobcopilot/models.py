from dataclasses import dataclass, field


@dataclass
class Job:
    source: str  # "greenhouse" | "lever" | "usajobs" | "manual"
    external_id: str  # id within that source, stable across fetches
    title: str
    company: str
    location: str
    url: str
    description: str
    posted_at: str = ""  # ISO date string if the source provides one, else ""

    @property
    def key(self) -> str:
        return f"{self.source}:{self.external_id}"


@dataclass
class ScoredJob:
    job: Job
    score: int
    rationale: str
    matched_skills: list[str] = field(default_factory=list)


@dataclass
class Application:
    job_key: str
    company: str
    title: str
    status: str = "Not Applied"  # Not Applied | Applied | Interview | Offer | Rejected
    applied_date: str = ""
    follow_up_date: str = ""
    notes: str = ""
    resume_bullets: str = ""
    cover_letter: str = ""
