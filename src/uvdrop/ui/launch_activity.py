"""In-progress launch jobs shown on the main window."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

JobState = Literal["running", "waiting", "done", "error"]

# Default phase count for a full prepare → confirm → sync → run flow.
LAUNCH_STEPS = 4


@dataclass
class LaunchJob:
    id: str
    title: str
    step: int = 1
    total: int = LAUNCH_STEPS
    detail: str = ""
    state: JobState = "running"

    @property
    def progress_label(self) -> str:
        return f"{self.step}/{self.total}"


def new_job_id() -> str:
    return uuid4().hex[:10]


@dataclass
class JobStore:
    """Thread-unsafe store; mutate only on the Tk main thread."""

    jobs: dict[str, LaunchJob] = field(default_factory=dict)

    def start(self, title: str, *, total: int = LAUNCH_STEPS, detail: str = "") -> LaunchJob:
        job = LaunchJob(id=new_job_id(), title=title, total=total, detail=detail, step=1)
        self.jobs[job.id] = job
        return job

    def update(
        self,
        job_id: str,
        *,
        step: int | None = None,
        detail: str | None = None,
        state: JobState | None = None,
    ) -> LaunchJob | None:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        if step is not None:
            job.step = max(1, min(step, job.total))
        if detail is not None:
            job.detail = detail
        if state is not None:
            job.state = state
        return job

    def finish(self, job_id: str, *, state: JobState = "done", detail: str = "") -> None:
        job = self.jobs.get(job_id)
        if job is None:
            return
        job.state = state
        if detail:
            job.detail = detail
        if state in {"done", "error"}:
            # Keep briefly visible via UI timer; caller removes.
            pass

    def remove(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)

    def active(self) -> list[LaunchJob]:
        return [j for j in self.jobs.values() if j.state in {"running", "waiting"}]
