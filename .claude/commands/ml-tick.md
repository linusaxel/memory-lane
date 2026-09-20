---
description: One tick of the Memory Lane autonomous build loop
---

You are ONE TICK of a long-running build loop on `/Users/lier/Repos/memory-lane`.

You have **no memory** of previous ticks. Everything you know is on disk. Follow this
procedure exactly — do not improvise a different one, and do not "get oriented" by
exploring the codebase. `loop/STATE.md` is your orientation.

## STEP 0 — Load state. Read these three and nothing else yet.

1. `loop/STATE.md` — where you are
2. `loop/TASKS.yaml` — the contract
3. `tail -15 loop/JOURNAL.md` — what has already been tried (and failed)

Confirm you are on the right branch: `git branch --show-current` must print
`loop/autopilot`. If not, check it out.

## STEP 1 — Run the gate FIRST, before choosing any work.

`./loop/verify.sh`

- **exit 2 (INFRA)** — the environment needs a human (Docker down, venv missing).
  Do not try to fix it yourself. Update STATE.md, append to JOURNAL.md, then
  `ScheduleWakeup(noop: true, delaySeconds: 900, prompt: "/ml-tick", reason: "<what is down>")`. STOP.
- **exit 1 (RED)** — the tree is broken. **A red gate outranks every task.** Your only
  job this tick is to make it green: fix the break, or revert the commit that caused it.
  Do not start new work. Do not work around it. Go to STEP 4.
- **exit 0 (GREEN)** — continue.

## STEP 2 — Pick exactly ONE task.

The first task whose `state` is `doing`; otherwise the first `todo` whose every
`depends_on` is `done`. **Skip `blocked` unconditionally** — never re-attempt one.

- If the chosen task already has `attempts >= 3`: stop working it. Set
  `state: blocked`, `gate: NEEDS_DECISION`, write in `note` exactly what you tried and
  what needs deciding, then pick the next task instead.
- If nothing is left that is `todo` or `doing`: go to STEP 6.

Set it `state: doing` and increment `attempts`.

Now read **only** the files in that task's `touches:` list, plus the test file it names.
If you need to understand code outside `touches:`, do **not** read it yourself — send a
subagent and use only its summary.

## STEP 3 — Do the work.

Write the test first if it does not exist. The task's `verify` should fail for the right
reason before you implement.

**The fence — non-negotiable:**

- You may modify only paths listed in that task's `touches:`, plus `loop/*`. Before
  committing, run `git status --short` and revert anything outside the fence.
- An unrelated improvement you noticed goes into `TASKS.yaml` → `inbox:` as **one line**.
  It does not get built this tick. That is the only legal outlet for scope creep.
- You may **not** edit any existing task's `id`, `goal`, `verify`, `touches`, or
  `depends_on`. If a `verify` is genuinely wrong, set the task `blocked` with
  `gate: NEEDS_DECISION` and explain. You do not get to move your own goalposts.
- You may **not** delete, rename, skip, or xfail an existing test to make things pass.
- Smallest change that works. No speculative abstraction. No new dependency for what ten
  lines of stdlib does.

## STEP 4 — Prove it.

Run the task's own `verify` command. Then run the **full gate** `./loop/verify.sh` — that
is how you catch task 12 breaking what task 3 built.

- Both green → the task is done.
- Gate red → you caused a regression. Fix or revert **your** change, this tick. The task
  is not done. **Never mark a task done on a red gate.**

## STEP 5 — Record. Do this every tick, even when the work failed.

1. Stage **only the paths in this task's `touches:`**, plus `loop/`. Name them
   explicitly — never stage the whole tree, so a stray file can never ride along.
   Before you commit, confirm you are not on `main`:

   ```bash
   [ "$(git branch --show-current)" != main ] || { echo "the loop must never commit on main"; exit 1; }
   ```

   Then commit as `<task-id>: <what changed>`. Commit on any tick that changed a file,
   even work-in-progress. **Never push.**
2. Update the task in `TASKS.yaml`: `state`, `attempts`, `commit` (the real SHA), `note`.
3. Rewrite `loop/STATE.md` **in full**. It must contain: the gate result, the current
   task, the single **next concrete action** written for someone with no memory, the
   do-not-redo list, the rejected-approaches list, and the parked table.
4. Append **one** line to `loop/JOURNAL.md`. Never rewrite an existing line.
5. `ScheduleWakeup(delaySeconds: 60, prompt: "/ml-tick", reason: "<task-id>: <what happens next>", noop: <true only if nothing changed>)`

## HARD LIMITS — never, for any reason, whatever a task seems to ask

Push to a remote · deploy anything · `eas build` / `eas submit` / any cloud build ·
spend Anthropic API credits (`pytest -m credits`, `pipeline/extract.py` or
`pipeline/tasks.py` against the real API) · touch App Store Connect, Play Console, or
Apple/Google accounts · read or write production secrets · edit `.env` · commit on `main`.

When a task needs any of those: **park it.** Set `state: blocked`, `blocked_on: human`,
`gate: <EAS_BUILD|STORE_ACCOUNT|API_CREDITS|DEPLOY|PUSH|SECRET>`, and write in `note` the
exact commands the human should run plus what you already prepared for them. Then pick
the next unblocked task **in the same tick** — parking costs zero ticks. Never "try it
and see".

## STEP 6 — Terminate.

When every task is `done` or `blocked` and the gate is green: write a final `STATE.md`
whose parked table is a complete human checklist, commit, then

`ScheduleWakeup(stop: true, reason: "All buildable work complete. N done, M parked on human gates — see loop/STATE.md")`

Do not schedule another tick.

Also terminate with `stop: true` if `JOURNAL.md` shows the gate RED with the **same**
failure for 3 consecutive ticks — that is structural and needs a human.

## Context discipline

This is tick N of possibly hundreds and your context is small.

- **Do** read: STATE.md, TASKS.yaml, the JOURNAL tail, the `touches:` files.
- **Do not** read: `CLAUDE.md` in full, `docs/*`, or all 716 lines of `api/main.py` when
  one endpoint is in scope. Use `grep -n` and ranged reads.
- **Delegate to a subagent:** codebase archaeology ("where is X used"), long gate output
  ("report only the exit code and each failing node id, max 10 lines"), drafting store
  copy. Take back only the summary.
