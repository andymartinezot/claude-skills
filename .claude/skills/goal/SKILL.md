---
name: goal
description: Autonomous end-to-end execution mode for a self-contained shipping task — "ship X". Forces plan-first, self-verifying execution, and a single final report. Used sparingly — for most work, the conversational flow with checkpoints is preferred. Only trigger on explicit `/goal <task>` or when the user explicitly says "do this autonomously, no checkpoints".
---

# Goal — autonomous end-to-end task

The user named a shipping goal. Execute it without conversational back-and-forth until done OR genuinely blocked. Use this mode ONLY when explicitly invoked.

## Required phases — do all of them, in order

### Phase 1 — Plan (BEFORE any code change)

Write a numbered plan as a single message. Each step has:

- **What** you'll do (one line).
- **Which files** you'll touch.
- **How** you'll verify the step worked (specific command or check).

After the steps, state:

- **Risks** — irreversible operations, shared state, anything that could leak past staging.
- **Out of scope** — what you noticed but won't touch (gets listed in the final report as "next actions").
- **Definition of done** — measurable criteria the final report will be checked against.

Then **wait for user OK**, unless the user said "no checkpoints" or "just ship it" in the original `/goal` invocation. If they did, skip the wait and start executing immediately.

### Phase 2 — Execute

Walk the plan top-to-bottom. After each step:

- **Verify the step worked.** Run the test, check the output, re-read the diff. Don't trust completion based on "no error in tool call".
- **Self-correct without prompting.** If verification fails, root-cause and fix it. Don't ask the user unless you've hit something truly outside your authority (e.g., needs AWS console access, deploys to prod).
- **One-line status updates only.** No mid-task summaries. Save synthesis for the final report.

If you discover related work outside the plan: write it under "next actions" in your eventual final report and **leave it**. Don't expand scope mid-execution.

### Phase 3 — Verify the whole

Before declaring done:

- Run the test/build/lint suite if one exists. If you can't run it (e.g., no env), say so explicitly.
- Read final diffs cold (`git diff origin/main` or equivalent) and compare to the Phase 1 definition of done.
- If this is a UI/runtime change, exercise it end-to-end where possible. For infra changes, run `terraform plan` against the target env and confirm zero unintended drift.

### Phase 4 — Final report

Single message. Sections in this exact order:

```
**What was done.** <2-4 sentences synthesizing the plan as it actually executed. Call out any deviations from Phase 1.>

**Verification.** <bullet list of commands run + result. Be specific: "make plan ENV=staging → Plan: 1 to add, 0 to change, 0 to destroy. Matches expectation." Not "tests pass".>

**Not done / deferred.** <bullet list of anything left out: blocked items (with the blocker), out-of-scope items spotted during execution, intentional follow-ups. Or "nothing — all in scope is shipped".>

**Next actions.** <2-4 bullets the user might want to do next: review the PR, merge, file follow-up tickets, run a smoke test, etc.>
```

## Don'ts

- **Don't ask clarifying questions mid-execution** unless the user opted out of checkpoints AND you're genuinely blocked. If checkpoints are allowed, batch your questions into one `AskUserQuestion` at a logical break — never one-off mid-task questions.
- **Don't claim "complete" without Phase 3.** "I made the edits" is not "shipped".
- **Don't expand scope.** Note new work in "next actions", don't action it.
- **Don't summarize step-by-step.** The final report is the summary. Mid-execution chatter dilutes signal.
- **Don't push or merge** unless the user's `/goal` invocation explicitly included it. Default ending state is "branch ready for PR" or "applied to staging" — match the natural stopping point.
