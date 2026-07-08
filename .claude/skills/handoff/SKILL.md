---
name: handoff
description: Use at the end of a session to write a session log that the next `/resume` will read. Writes `docs/sessions/YYYY-MM-DD-<slug>.md` with goal, what changed (files, ADRs, external infra), outcome, open threads, and context for the next resume. Trigger on `/handoff` or when user says "wrap up the session" / "write a handoff".
---

# Handoff — session log

When invoked, write a single markdown file under `docs/sessions/` summarizing this session. Do not make any other changes.

## Steps

1. **Compute today's date** in `YYYY-MM-DD` format.
2. **Pick a slug** — 2-4 kebab-case words describing the session's primary focus (e.g., `argocd-internal-rollback`, `staging-eks-bootstrap`, `route53-greenfield-fix`). Derive from session context, not by asking.
3. **Check existing naming convention**: `ls docs/sessions/ 2>/dev/null | tail -5`. Mirror whatever convention is in place (separator, capitalization, etc.). If the directory doesn't exist, create it via the Write tool (writing the new file creates parents).
4. **Write `docs/sessions/<date>-<slug>.md`** with the template below. Pull all content from this session's actual context — file edits, terminal output, decisions, ticket comments. Do not invent.
5. **Tell the user** the file path you wrote and nothing else. If the session created ADRs or tracker tickets, list those keys too as a one-line confirmation.

## Template

```markdown
# YYYY-MM-DD — <Title Case Session Topic>

## Goal
One paragraph: what we set out to accomplish this session. State it as the user framed it, not as you executed it.

## What changed
- **Files:** `path/to/file.tf` — one-line why. (One bullet per file.)
- **ADRs:** `ADR-NNN — Title` — one-line summary. Or "none".
- **External systems:** changes made outside the repo — cloud console / CLI actions, secrets or DNS records created out-of-band, tracker tickets created (KEY-NNN — Title), wiki pages updated. Or "none".
- **Version control:** PRs opened/merged (link), branch pushed, etc. Or "none".

## Outcome
One paragraph: is the change live, partially live, broken, rolled back, on a feature branch awaiting review? Describe the actual state of the repo and any deployed envs.

## Open threads
- One bullet per unresolved item. Each line should give enough context that the next session can pick it up without re-asking. Include ticket IDs and file paths.

## Context for next /resume
2-4 lines of the most important "if you only read one section, read this" info. What's blocked on what, where to look first, any non-obvious gotchas surfaced this session that aren't in the code yet.
```

## Guardrails

- **Do not run tests, lint, commit, or push as part of /handoff.** It is a documentation step, not an integration step.
- **Do not summarize internally inside this skill** — the file IS the summary. Don't repeat its contents back to the user.
- **Be honest about broken state.** If something is half-done or broken, say so explicitly under Outcome — the next session needs to know.
- **Keep "What changed → External systems" focused on durable changes.** Skip ticket *comments* (too noisy), keep ticket *creations / transitions / decisions*.
