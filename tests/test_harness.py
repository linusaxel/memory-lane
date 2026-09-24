"""Smoke checks for the loop's own machinery."""

import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_gate_is_executable():
    gate = ROOT / "loop" / "verify.sh"
    assert gate.exists(), "loop/verify.sh is missing"
    assert os.access(gate, os.X_OK), "loop/verify.sh is not executable"


def test_e2e_runner_is_executable():
    """The simulator run is not part of the gate - no iOS simulator exists on
    the CI runner, and it takes minutes rather than the gate's seconds. What
    the gate can still say is that the entry point has not rotted."""
    runner = ROOT / "e2e" / "run.sh"
    assert runner.exists(), "e2e/run.sh is missing"
    assert os.access(runner, os.X_OK), "e2e/run.sh is not executable"
    assert sorted((ROOT / ".maestro").glob("*.yml")), "no flows in .maestro/"


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


def _slug(heading):
    """GitHub's anchor for a heading: lowercase, punctuation gone, spaces to hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def _anchors(md):
    text = re.sub(r"```.*?```", "", md.read_text(), flags=re.S)
    return {_slug(h) for h in re.findall(r"^#+ (.+)$", text, flags=re.M)}


def test_doc_links_resolve():
    """The new docs are pointers, so a pointer that dangles is the whole failure.
    Every relative link in the guidance must name a file that exists, and an
    anchor must name a heading in it. Code that cites a decision by anchor too."""
    docs = [ROOT / p for p in ("AGENTS.md", "README.md", "mobile/UI.md", "e2e/README.md")]
    docs += sorted((ROOT / "docs").rglob("*.md"))
    broken = []
    for doc in docs:
        text = re.sub(r"```.*?```", "", doc.read_text(), flags=re.S)
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"[a-z]+:", target):
                continue
            path, _, anchor = target.partition("#")
            dest = (doc.parent / path).resolve() if path else doc
            if not dest.exists():
                broken.append(f"{doc.relative_to(ROOT)}: {target}")
            elif anchor and dest.suffix == ".md" and anchor not in _anchors(dest):
                broken.append(f"{doc.relative_to(ROOT)}: {target}")
    decisions = _anchors(ROOT / "docs" / "10-decisions.md")
    for folder in ("api", "pipeline", "crawler", "mobile/src", "tests", "db", "e2e", ".maestro"):
        for f in (ROOT / folder).rglob("*"):
            if f.suffix not in {".py", ".ts", ".tsx", ".sql", ".sh", ".yml", ".md"}:
                continue
            for anchor in re.findall(r"10-decisions\.md#([\w-]+)", f.read_text()):
                if anchor not in decisions:
                    broken.append(f"{f.relative_to(ROOT)}: #{anchor}")
    assert not broken, "dangling links:\n" + "\n".join(broken)
