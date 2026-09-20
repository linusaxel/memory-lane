"""The loop grades itself. This test grades the loop.

Everything here exists to make ONE failure mode expensive: an agent marking a
task done that does not actually work. A `done` task must point at a test that
still collects, and at a commit that really exists. The classic cheats -
deleting the failing test, renaming it, or inventing a SHA - turn the gate RED
instead of green.

This file is part of the contract. The loop may not weaken it.
"""

import pathlib
import re
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = yaml.safe_load((ROOT / "loop" / "TASKS.yaml").read_text())
TASKS = CONTRACT["tasks"]
VALID_GATES = set(CONTRACT["meta"]["gates"])
VALID_STATES = set(CONTRACT["meta"]["states"])

DONE = [t for t in TASKS if t["state"] == "done"]
BLOCKED = [t for t in TASKS if t["state"] == "blocked"]


def _verify_targets(verify: str):
    """Paths / node ids a verify command points at."""
    for token in verify.split():
        token = token.strip("\"'")
        if token.startswith("tests/") or "::" in token:
            yield token


def _target_exists(token: str) -> bool:
    """Does this still exist?

    Deliberately does NOT shell out to pytest: this module would be re-imported
    by the child process and spawn another, forever. Reading the file proves the
    same thing - that the test was not quietly deleted or renamed to reach green.
    """
    path, _, node = token.partition("::")
    f = ROOT / path
    if not f.exists():
        return False
    if not node:
        return True
    return re.search(rf"^\s*(async )?def {re.escape(node)}\b", f.read_text(), re.M) is not None


# -- structural invariants ---------------------------------------------------

def test_ids_are_unique():
    ids = [t["id"] for t in TASKS]
    assert len(ids) == len(set(ids)), "duplicate task ids"


def test_states_are_legal():
    for t in TASKS:
        assert t["state"] in VALID_STATES, f"{t['id']} has bogus state {t['state']!r}"


def test_every_task_has_a_goal_and_a_verify():
    for t in TASKS:
        assert t.get("goal"), f"{t['id']} has no goal"
        assert t.get("verify"), f"{t['id']} has no verify"


def test_dependencies_exist():
    ids = {t["id"] for t in TASKS}
    for t in TASKS:
        for dep in t.get("depends_on") or []:
            assert dep in ids, f"{t['id']} depends on unknown task {dep}"


def test_no_task_is_done_before_its_dependencies():
    by_id = {t["id"]: t for t in TASKS}
    for t in DONE:
        for dep in t.get("depends_on") or []:
            assert by_id[dep]["state"] == "done", \
                f"{t['id']} is done but its dependency {dep} is {by_id[dep]['state']}"


# -- the part that actually stops false progress -----------------------------

@pytest.mark.parametrize("t", DONE, ids=lambda t: t["id"])
def test_done_task_is_actually_proven(t):
    tid = t["id"]

    # 1. done means machine-checked, never "I looked at it"
    assert t["verify"] != "MANUAL", f"{tid} claims done but its proof is MANUAL"

    # 2. anything it points at must STILL EXIST. Deleting or renaming the test
    #    to get to green fails right here.
    for token in _verify_targets(t["verify"]):
        assert _target_exists(token), \
            f"{tid} is done but points at {token!r}, which no longer exists"

    # 3. a real commit, not a story about one
    sha = t.get("commit")
    assert sha, f"{tid} is done with no commit recorded"
    found = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                           cwd=ROOT, capture_output=True)
    assert found.returncode == 0, f"{tid} records commit {sha} which does not exist"


@pytest.mark.parametrize("t", BLOCKED, ids=lambda t: t["id"])
def test_blocked_task_tells_the_human_what_to_do(t):
    tid = t["id"]
    assert t.get("blocked_on") == "human", f"{tid} is blocked but not on a human"
    assert t.get("gate") in VALID_GATES, f"{tid} has an unrecognised gate {t.get('gate')!r}"
    note = (t.get("note") or "").strip()
    assert len(note) > 40, f"{tid} is blocked without explaining what a human must do"


# -- scope fence -------------------------------------------------------------

def test_inbox_is_not_executable():
    """Ideas live in inbox as plain strings. If one grows a `verify`, someone is
    trying to smuggle unreviewed scope into the contract."""
    for item in CONTRACT.get("inbox") or []:
        assert isinstance(item, str), f"inbox entry is not a plain string: {item!r}"


def test_at_most_one_task_in_flight():
    doing = [t["id"] for t in TASKS if t["state"] == "doing"]
    assert len(doing) <= 1, f"more than one task in flight: {doing}"
