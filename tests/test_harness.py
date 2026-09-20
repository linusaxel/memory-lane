"""Smoke checks for the loop's own machinery."""

import os
import pathlib

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


def test_ruff_formats_for_the_python_we_actually_run():
    """`ruff format` emits syntax for its target version, and with no
    `[project].requires-python` to infer from it defaults to the newest Python it
    knows about - 3.14 at the time of writing.

    That is not cosmetic. PEP 758 made `except A, B:` legal in 3.14, so a
    3.14-targeted `ruff format` strips parentheses that 3.12 requires and leaves
    a file python cannot parse. `ruff check` does not catch it: the gate runs
    check before format, so check sees the still-valid file.
    """
    import sys
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    target = config["tool"]["ruff"]["target-version"]
    running = f"py{sys.version_info.major}{sys.version_info.minor}"
    assert target == running, (
        f"ruff targets {target} but the venv is {running}; "
        "ruff will format for a Python this project does not run"
    )
