---
name: adr
description: Record an architectural decision. Writes a numbered entry in `DECISIONS.md` with the 5 sections (Context, Decision, Status, Consequences, Revisit if) and updates the index table at the top. Writes autonomously from current session context — does NOT ask clarifying questions. User edits the file in place after if anything needs refinement. Trigger on `/adr` or when user says "log this decision" / "write an ADR for X".
---

# ADR — architectural decision record

Write one ADR entry in `DECISIONS.md` from current session context. No questions back to the user.

## Steps

1. **Read `DECISIONS.md`** to find:
   - The existing format (heading levels, separators, section order) — **mimic it exactly**.
   - The next ADR number (`ADR-NNN`). Use 3-digit padded (`ADR-001`, `ADR-042`).
   - The index table at the top.

2. **If `DECISIONS.md` doesn't exist yet**, create it with this minimal header before the first ADR:

   ```markdown
   # Decisions

   Architecture Decision Records for this repository. Append-only — once a decision is `Accepted`, edit only the `Status` line to retire it.

   | ADR | Date | Title | Status |
   |-----|------|-------|--------|
   ```

3. **Append the new ADR** to the bottom of the file using the template below. Pull all content from this session's context — what the user said, what we explored, what was decided. Don't invent and don't ask.

4. **Add a row to the index table** at the top — match the existing column order. New row at the bottom of the table.

5. **Tell the user**: ADR number, title, and the line range where you wrote it so they can edit in place. One sentence. No further commentary.

## Template

```markdown
## ADR-NNN — <Short Title (decision verb form, e.g., "Use Helm CLI for ArgoCD install instead of Terraform helm_release")>

**Date:** YYYY-MM-DD
**Status:** Accepted

### Context
2-4 sentences: what observation, constraint, or recurring issue led us to make a decision. Reference tickets (using whatever key format the repo uses), prior ADRs ([[ADR-NNN]]), or code paths if relevant. State what was painful or unclear before.

### Decision
1-3 sentences stating the decision as a directive — not a discussion. "We will X" / "We will not Y". Be specific enough that a future reader can tell whether code or process matches the decision.

### Consequences
- **Positive:** what becomes easier or cheaper.
- **Negative:** what we lose, what becomes harder, what manual steps we now own.
- **Neutral:** assumptions we're now relying on (e.g., "assumes the team has Tailscale clients installed").

### Revisit if
- Specific conditions that would make this decision wrong. Be concrete (numbers, tools, scale points). "If we scale past 50 engineers", "If AWS launches managed ArgoCD with our RBAC model", "If we adopt a multi-cloud strategy". Avoid "if things change".
```

## Guardrails

- **Append-only.** Do not modify existing ADR bodies — ADRs are immutable once accepted. The only existing-ADR field you may touch is `Status` if the user explicitly says to retire/supersede a prior ADR.
- **Do not ask the user to fill in sections.** Synthesize from session context. If a section is genuinely thin (e.g., consequences are just "we did this thing"), keep the section but make it one short sentence — don't pad.
- **Pick the decision verb carefully.** Title should start with the chosen action ("Use", "Adopt", "Defer", "Standardize on"), not "Decision about X".
- **Don't write multiple ADRs in one invocation.** One decision, one ADR. If the session touched on several decisions, ask the user which to record first.
