"""Smoke checks for the loop's own machinery."""

import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_gate_is_executable():
    gate = ROOT / "loop" / "verify.sh"
    assert gate.exists(), "loop/verify.sh is missing"
    assert os.access(gate, os.X_OK), "loop/verify.sh is not executable"


def test_state_files_exist():
    for name in ("TASKS.yaml", "STATE.md", "JOURNAL.md", "verify.sh"):
        assert (ROOT / "loop" / name).exists(), f"loop/{name} is missing"


def test_tick_prompt_exists():
    assert (ROOT / ".claude" / "commands" / "ml-tick.md").exists()


def test_fake_anthropic_never_touches_the_network():
    """The loop may not spend credits, so the fake must be a real stand-in."""
    from tests.fakes import FakeAnthropic

    fake = FakeAnthropic()
    resp = fake.messages.create(model="whatever", max_tokens=10, messages=[])
    assert resp.content[0].type == "text"
    assert "Katz" in resp.content[0].text
    assert len(fake.messages.calls) == 1


def test_loop_is_not_on_main():
    """The loop commits to its own branch so nothing reaches main unreviewed."""
    branch = subprocess.run(["git", "branch", "--show-current"],
                            cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert branch != "main", "the loop must never commit on main"
