---
name: resume-handoff
description: Fast session orientation, the counterpart of /handoff. Reads CLAUDE.md (if not already loaded), STATUS.md, this role's latest session log, the DECISIONS.md index and git state, then prints six bullets and asks what we're working on. Use at the start of a session, on `/resume-handoff`, or when the user says "resume", "where were we" or "catch me up".
---

# Resume-handoff — session orientation

Do **only** these reads. Pull more context only if the user's answer needs it.

## Reads (in parallel)

1. **`CLAUDE.md`** at the workspace root. Usually already in context as project instructions; if so, skip the read.
2. **`STATUS.md`**, if it exists. It is the "right now" page and outranks the session log for current state.
3. **The latest session log for this role.** The role is `main`, or the named agent's area (see `/handoff`). Take the newest `docs/sessions/*-<role>-*.md`. If there is none, fall back to the newest `docs/sessions/*.md` and **mark it "(untagged log — may be from another console)"** — logs predating the role segment, or written by a different console, describe work this role did not do. If the directory is missing or empty, say "no prior session log".
4. **`DECISIONS.md` index table only** — enough lines to capture the table. Never ADR bodies.
5. **Git state.** `git status -sb` and `git log --oneline -5`. If the workspace root is not a repo, run them in each repo that `STATUS.md` or the log names as active, not in all of them.

Memory: `MEMORY.md` is injected automatically, so never read it. Treat its entries as leads to verify, not as current truth.

## Output — exactly this shape

Six bullets, then one question. No headers, no preamble, no closing.

```
- **Project:** <one line from CLAUDE.md>
- **Last session:** <date + one-line goal, or "no prior session log">
- **Now:** <critical path / blockers from STATUS.md, or the log's Outcome if there is no STATUS.md — note the "Last updated" date if it is over 7 days old>
- **What changed:** <one line synthesizing the log's "What changed", or the recent commits if there is no log>
- **Open threads:** <one line each, from the log's Open threads; flag uncommitted or unpushed work found in git>
- **Recent decisions:** <last 2–3 rows of the DECISIONS.md index, or "none yet">

What are we working on today?
```

## Guardrails

- **Don't load full docs, runbooks or ADR bodies.** This is orientation, not research.
- **Don't act on the open threads.** Surface them and wait.
- **Ask only "What are we working on today?"**
- **If the answer names a runbook, ADR, spec or file, read it then** — not before.
