"""--burst waits out scheduled retries instead of leaving them to bill later,
a dead model ID stops the worker before its first job, and a queue left over
is shown, and asked about, before any of it runs."""

import os

import anthropic
import httpx
import pytest

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

    monkeypatch.setattr(worker, "check_models", lambda: None)
    monkeypatch.setattr(worker, "get_redis", lambda: None)
    monkeypatch.setattr(worker, "Worker", FakeWorker)
    monkeypatch.setattr(worker, "ScheduledJobRegistry", FakeRegistry)
    monkeypatch.setattr(worker.time, "sleep", fake_sleep)

    worker.run_worker(["classify", "extract"], burst=True)

    assert passes == [{"burst": True, "with_scheduler": True}] * 3


def test_a_retired_model_id_stops_the_worker_naming_its_variable(monkeypatch):
    """2026-09-27: EXTRACTION_MODEL=claude-sonnet-4-20250514 held a burst for 12 minutes."""

    class Models:
        def retrieve(self, model):
            if model == "claude-sonnet-4-20250514":
                response = httpx.Response(404, request=httpx.Request("GET", "https://x"))
                raise anthropic.NotFoundError("not found", response=response, body=None)

    class Client:
        models = Models()

    monkeypatch.setattr(worker.anthropic, "Anthropic", lambda **_: Client())
    monkeypatch.setattr(worker, "EXTRACTION_MODEL", "claude-sonnet-4-20250514")
    with pytest.raises(SystemExit, match="EXTRACTION_MODEL='claude-sonnet-4-20250514'"):
        worker._check()


@pytest.fixture
def queued(monkeypatch):
    class Job:
        def __init__(self, content_id):
            self.kwargs = {"content_id": content_id}

    held = {"classify": [Job(1), Job(1), Job(2)], "extract": []}

    class FakeQueue:
        def __init__(self, name, connection):
            self.jobs = held[name]

    monkeypatch.setattr(worker, "get_redis", lambda: None)
    monkeypatch.setattr(worker, "Queue", FakeQueue)
    monkeypatch.setattr(
        worker, "_source_names", lambda ids: {1: "Historisk Atlas", 2: "Carl Møller"}
    )
    monkeypatch.setattr(worker.sys.stdin, "isatty", lambda: False)
    return held


def test_queued_jobs_are_shown_by_source_and_refused_without_a_terminal(queued, capsys):
    with pytest.raises(SystemExit, match="--yes"):
        worker.confirm_queues(["classify", "extract"])
    assert capsys.readouterr().out == "classify: 3 jobs: Historisk Atlas 2, Carl Møller 1\n"


def test_yes_runs_what_is_queued(queued):
    worker.confirm_queues(["classify", "extract"], yes=True)


def test_empty_queues_run_without_asking(queued):
    queued["classify"].clear()
    worker.confirm_queues(["classify", "extract"])
