---
name: commit-and-report
description: Run a feature-branch lifecycle in any repo — branch from the default branch, commit using the repo's own message convention, push, open a PR, and (in a second invocation) rebase + propose the approve/merge commands. Detects branch/commit/ticket conventions from the repo itself, or reads them from `.claude/commit-and-report.json`. NEVER auto-approves or merges PRs — that step always requires explicit human confirmation. Optionally posts a status comment to a GitHub issue or a linked issue tracker. Trigger on `/commit-and-report` or when the user says "commit, push and open a PR".
---

> **Language:** Respond in the user's language. If unclear, default to the language of the user's message.

# Commit & Report — feature branch lifecycle

Walks a repo's standard branch → commit → push → PR → rebase → merge flow. It auto-detects which
phase to run by inspecting `git status`, the current branch, and the open PR via `gh`. It does what's
needed and stops.

Nothing about this skill is repo-specific. **Conventions are discovered, never assumed.**

## Phase 0 — Discover the repo's conventions (always run first)

Run these in parallel; they're all cheap:

```sh
git rev-parse --abbrev-ref origin/HEAD 2>/dev/null   # default branch, e.g. "origin/main"
git branch --show-current
git status --short
git log --oneline -20                                # commit subject convention
git for-each-ref --format='%(refname:short)' --sort=-committerdate --count=20 refs/remotes/origin
gh pr list --head "$(git branch --show-current)" --json url,state,title 2>/dev/null
```

Then resolve, in this order of precedence:

1. **`.claude/commit-and-report.json`** in the repo root, if present. Highest authority. Schema:

   ```json
   {
     "defaultBranch": "main",
     "ticketRegex": "[A-Z][A-Z0-9]+-[0-9]+",
     "requireTicket": false,
     "branchTemplate": "{ticket}_{slug}",
     "commitTemplate": "[{ticket}] - {message}",
     "prTitleTemplate": "[{ticket}] {title}",
     "mergeStrategy": "squash",
     "deleteBranchOnMerge": true,
     "tracker": "auto"
   }
   ```

   Every key is optional. `tracker` is `auto` | `none` | `github` | `jira`.

2. **`CLAUDE.md` / `CONTRIBUTING.md`** — if either states a commit or branch convention, follow it.

3. **Inference from git history** — this is the normal path, since most repos have no config file:
   - **Default branch:** from `origin/HEAD`. Fall back to `main`, then `master`. Never assume.
   - **Ticket key:** match `ticketRegex` (default `[A-Z][A-Z0-9]+-[0-9]+`, e.g. `ABC-123`, `PROJ-4712`)
     against the current branch name, then against recent commit subjects. If ≥ 60% of the last 20
     commits carry a ticket key, treat tickets as **required** for this repo.
   - **Commit template:** take the shape of the majority of recent subjects. Common ones:
     `[ABC-123] - message` · `ABC-123: message` · `feat(scope): message` (Conventional Commits) ·
     bare `message`. Reproduce the majority shape exactly — separator, spacing, casing.
   - **Branch template:** same, from recent remote branch names. Common ones:
     `ABC-123_snake_case_slug` · `ABC-123-kebab-slug` · `feature/kebab-slug` · `user/topic`.
   - **Tracker:** `jira` only if a ticket key is in use **and** Atlassian MCP tools are available in
     this session; otherwise `github` if `gh` is authenticated; otherwise `none`.

4. **Ask the user** for anything still ambiguous. Do not guess on commit format, ticket key, or
   which files to stage.

State the detected conventions in one line before acting, e.g.
`Detected: default=main · commit=\`[ABC-123] - msg\` · branch=\`ABC-123_slug\` · tracker=jira`.
This lets the user correct a bad inference before anything is written.

## The full flow (for reference)

```sh
git checkout <default> && git pull --ff-only        # Phase A
git checkout -b <branchTemplate>                    # Phase A

# (user edits files, runs tests locally)

git add <files>                                     # Phase B
git commit -m "<commitTemplate>"                    # Phase B
git push -u origin <branch>                         # Phase B
gh pr create                                        # Phase B (only if no PR yet)

git fetch && git rebase origin/<default> \
  && git push --force-with-lease                    # Phase C

# ─── HARD STOP — human confirmation required ───
gh pr merge --squash --delete-branch                # Phase D
git checkout <default> && git pull --ff-only        # Phase D
```

**Never** chain Phase C straight into the merge step — always pause for explicit human confirmation.

## Invocation

```
/commit-and-report "<commit message>"                            # Phases A and B
/commit-and-report --merge                                       # Phases C and D (with the hard stop)
/commit-and-report "<commit message>" --issue <number>           # also comment on the tracker issue
/commit-and-report "<commit message>" --ticket ABC-123           # override the detected ticket key
```

If no arguments are given, run Phase 0, inspect git state, and ask which phase to run.

## Phase A — Start a new feature branch

Trigger: current branch is the default branch (or any non-feature branch) and the user wants to start
new work.

1. Confirm the working tree is clean: `git status`. If dirty, **stop** and ask how to handle the
   existing changes (stash, commit, discard). Don't auto-stash.
2. `git checkout <default> && git pull --ff-only`.
3. Ask for a ticket key (only if the repo requires one and it wasn't supplied) and a short
   description for the slug. Build the branch name from `branchTemplate`.
4. `git checkout -b <branch>`.
5. Confirm the branch is created. **Stop.** The user makes the code changes; the skill picks up
   again at Phase B.

## Phase B — Commit, push, open PR

Trigger: current branch is not the default branch and there are staged or unstaged changes (or the
user explicitly invokes with a commit message).

1. Phase 0 discovery, plus `git diff --stat HEAD` to see the scale of the change.
2. Extract the ticket key from the branch name, or from `--ticket`, or ask if the repo requires one.
3. Stage **specific files by name**, based on what the user described. Never `git add .` or
   `git add -A`. If the user wants everything staged, they'll say so — ask if unclear.
4. **Format the subject** from `commitTemplate`. If the user's message already matches the template
   (e.g. already carries the ticket prefix), don't double-prefix it.
5. Commit using a heredoc so multi-line bodies format correctly:
   ```sh
   git commit -m "$(cat <<'EOF'
   <formatted subject>

   <optional body>
   EOF
   )"
   ```
   Add a `Co-Authored-By:` trailer only if the host environment's instructions ask for one — don't
   hardcode a model name here, it goes stale.
6. Push: `git push -u origin "$(git branch --show-current)"` on the first push of a branch,
   `git push` afterwards.
7. **PR step:**
   - No PR yet → `gh pr create --title "<prTitleTemplate>" --body "$(cat <<'EOF' … EOF
     )"` with a Summary + Test Plan body. If the repo has `.github/pull_request_template.md`, follow
     its structure instead.
   - PR exists → skip; just confirm the push landed.
8. **Optional reporting:**
   - `--issue <n>` and tracker is `github` → `gh issue comment <n> --body "<status update>"`.
   - Tracker is `jira` → **offer** to post a status comment to the ticket via the Atlassian MCP tool.
     Always ask first: tracker comments are visible to the whole team and awkward to clean up.
   - Tracker is `none` → skip silently.
9. Print the PR URL. **Stop.** Hand off to review.

## Phase C — Rebase against the default branch (just before merging)

Trigger: user invokes with `--merge`, or the PR is approved and green.

1. `git fetch origin`.
2. `git rebase origin/<default>`. On conflict, **stop** and report — never resolve silently.
3. After a clean rebase: `git push --force-with-lease` (never plain `--force`, so we abort if the
   remote moved unexpectedly).
4. `gh pr view --json url,statusCheckRollup,reviewDecision,mergeable` — confirm checks are green,
   review is approved, mergeable is true.
5. **HARD STOP. Do not merge.** Print the PR URL, the status, and the exact commands the user would
   run next:
   ```sh
   gh pr merge --squash --delete-branch
   git checkout <default> && git pull --ff-only
   ```
   Include `gh pr review --approve` in that list **only** if the user is not the PR author — GitHub
   rejects self-approval, and most branch protections require a *different* reviewer anyway.

   Then ask: **"Ready to merge and clean up? Reply 'yes' to proceed."**

Do not proceed without an explicit affirmative from the user **in the current conversation turn** —
not a memory of a past session, not an inferred preference.

## Phase D — Merge and clean up (only after explicit confirmation in Phase C)

1. `gh pr review --approve` — only if the user asked for it and is not the author.
2. `gh pr merge --<mergeStrategy> [--delete-branch]`, honoring the repo's configured strategy.
   Default `--squash`. If the repo's merge history is clearly all merge commits or all rebases,
   match it rather than forcing squash.
3. `git checkout <default> && git pull --ff-only`.
4. Verify: `git status` (clean), `git log --oneline -3` (the merged commit is on the default branch),
   `git branch --list <branch>` (the feature branch is gone locally).
5. Report and stop. Don't start another work cycle.

## Auto-detection logic (no-args invocation)

1. Current branch == default branch → suggest Phase A.
2. Current branch != default branch → check `git status`:
   - dirty → Phase B (ask for the commit message).
   - clean, PR exists → Phase C (rebase, then hard stop).
   - clean, no PR, branch has unpushed commits → Phase B step 6-7 (push + open PR).
   - clean, no PR, no commits ahead → nothing to do; say so.
3. Detached HEAD, mid-rebase, mid-merge → **stop** and report the state. Don't try to recover it.

## Guardrails

- **PR merge is never automatic.** The most important rule. Even with green checks and a "ship it"
  from a previous session, merging requires an explicit "yes" in the current turn.
- **Never force-push the default branch.** Never commit directly to it either — if the user asks,
  confirm first.
- **Never `git push --force`** — always `--force-with-lease`.
- **Never `--no-verify`.** Pre-commit hooks stay on unless the user explicitly asks to skip them.
- **Don't `git add .` or `git add -A`.** Stage files by name, based on intent.
- **Read git state before acting.** `git status`, `git diff`, `git log`, `gh pr view` are cheap.
- **Don't invent a ticket key.** If the repo requires one and it isn't in the branch name or the
  invocation, ask.
- **If anything is ambiguous: ask.** Conventions are easy to misread from a small sample.

## Examples

```
/commit-and-report "Add ALB controller install runbook"
   → Detects `[ABCD-41615] - <msg>` from history, stages the relevant files,
     commits, pushes, opens a PR. Ticket inferred from the branch name.

/commit-and-report "add retry to fetch client"
   → In a Conventional Commits repo with no ticket keys, commits as
     `feat: add retry to fetch client` on `feature/add-retry-to-fetch-client`.

/commit-and-report --merge
   → Rebases onto the default branch, force-with-lease pushes, shows PR status,
     STOPS, asks for explicit confirmation before merging.

/commit-and-report "Initial VPN module" --issue 42
   → Phase B, plus a status comment on GitHub issue #42.
```
