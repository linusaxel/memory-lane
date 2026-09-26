"""--burst waits out scheduled retries instead of leaving them to bill later."""

import os

# Importing pipeline.worker on macOS re-execs into a real worker unless this is set.
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

from pipeline import worker  # noqa: E402


def test_burst_runs_until_no_retry_is_scheduled(monkeypatch):
    scheduled = [2, 1, 0]
    passes = []

    class FakeWorker:
        def __init__(self, queues, connection):
            pass

        def work(self, **kwargs):
            passes.append(kwargs)

    class FakeRegistry:
        def __init__(self, name, connection):
            self.count = scheduled[0] if name == "extract" else 0

    def fake_sleep(_):
        scheduled.pop(0)

    monkeypatch.setattr(worker, "get_redis", lambda: None)
    monkeypatch.setattr(worker, "Worker", FakeWorker)
    monkeypatch.setattr(worker, "ScheduledJobRegistry", FakeRegistry)
    monkeypatch.setattr(worker.time, "sleep", fake_sleep)

    worker.run_worker(["classify", "extract"], burst=True)

    assert passes == [{"burst": True, "with_scheduler": True}] * 3
