"""Launch activity job store (UI progress)."""

from __future__ import annotations

from uvdrop.ui.launch_activity import JobStore, LAUNCH_STEPS


def test_job_store_progress_label() -> None:
    store = JobStore()
    job = store.start("Demo", detail="go")
    assert job.progress_label == f"1/{LAUNCH_STEPS}"
    store.update(job.id, step=3, detail="sync", state="running")
    assert store.jobs[job.id].progress_label == f"3/{LAUNCH_STEPS}"
    assert len(store.active()) == 1
    store.finish(job.id, state="done", detail="ok")
    assert store.active() == []
    store.remove(job.id)
    assert job.id not in store.jobs
