---
name: resume
description: Use at the start of a session to get oriented. Reads CLAUDE.md + the latest docs/sessions/*.md + the index table at the top of DECISIONS.md, then prints a 5-bullet summary (project, last session, what changed, open threads, recent decisions) and asks what we're working on today. Does NOT load full ADR bodies, runbooks, or architecture.md — only what's needed for orientation. Trigger on `/resume` or whenever the user asks "where did we leave off" / "what's the state" at session start.
---

# Resume — session orientation

When invoked, do **only** these reads. Do not pull additional context unless the user's answer requires it.

## Reads (in order, all in parallel)

1. **`CLAUDE.md`** at repo root — the project-level rules / overview. You may already have this in context from project rules; if so, skip the file read and rely on what's there.
2. **The most recent session log**: `ls -1t docs/sessions/*.md 2>/dev/null | head -1`. Read the whole file if found. If `docs/sessions/` doesn't exist or is empty, say so (it's a fresh project or no handoff was logged) and skip this step.
3. **`DECISIONS.md` index table only** — read only enough to capture the table at the top (typically the first 30-60 lines). Do NOT read ADR bodies. If `DECISIONS.md` doesn't exist, say so and skip.
4. Optional but recommended: `git status` and `git log --oneline -10` — fast, surfaces uncommitted work or commits that landed after the last handoff.

## Output — exactly this shape

After the reads, print **five bullets** and then **one question**. No headers, no preamble, no closing fluff.

```
- **Project:** <one line from CLAUDE.md "What this repo does">
- **Last session:** <date + one-line goal from the latest session log, or "no prior session log">
- **What changed:** <one line synthesizing the latest session's "What changed" section, or recent git commits if no log>
- **Open threads:** <bullet list from the latest session's "Open threads" — keep each thread to one line; use sub-bullets if helpful>
- **Recent decisions:** <last 2-3 ADRs from DECISIONS.md index table: ADR-NNN — Title (Status), or "no ADRs yet">

What are we working on today?
```

## Guardrails

- **Do not load full docs.** No `docs/architecture.md`, no `docs/runbooks/`, no ADR bodies. The point of this skill is fast orientation, not full context.
- **Do not act on the open threads.** Just surface them. Wait for the user to pick what to do.
- **Do not ask follow-up questions other than "what are we working on today?"** — let the user direct.
- **If the user's answer references a specific runbook / ADR / file, pull it then** — not preemptively.
