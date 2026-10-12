# claude-skills

A centralized, reusable collection of [Claude Code](https://claude.com/claude-code) skills.
Each skill lives in `.claude/skills/<name>/SKILL.md` and is designed to be **repo-agnostic** — drop it
into any project (or install it user-wide) and it works without editing.

## Skills

| Skill | What it does |
|-------|--------------|
| `commit-and-report` | Branch → commit → push → PR → rebase → merge lifecycle. Detects the repo's own branch/commit/ticket conventions; never merges without explicit confirmation. |
| `adr` | Append an Architecture Decision Record to `DECISIONS.md`. |
| `handoff` | Write an end-of-session log to `docs/sessions/` for the next `/resume-handoff`. |
| `resume-handoff` | Start-of-session orientation, the counterpart of `handoff`: reads STATUS.md, the latest session log, the decisions index and git state. |
| `goal` | Autonomous, plan-first, self-verifying execution mode for a single shipping task. |
| `drawio` | Create/edit draw.io diagrams and export to PNG/SVG/PDF. |
| `ascii-visualizer` | Terminal-rendered ASCII diagrams, box-drawing layouts, swimlanes. |
| `terraform-module-builder` | Generate production-ready reusable Terraform modules. |

## Install

Skills are discovered by Claude Code in two places:

- **User-wide** — `~/.claude/skills/` — available in every project.
- **Per-project** — `<repo>/.claude/skills/` — available only in that repo, and shareable with the team via git.

The `install.sh` helper **symlinks** skills from this repo into the target directory, so a later
`git pull` here updates every install automatically.

```bash
git clone <this-repo> ~/src/claude-skills
cd ~/src/claude-skills

./install.sh                       # all skills, user-wide (~/.claude/skills)
./install.sh adr handoff resume-handoff    # only these
./install.sh --project ~/code/app  # into that repo's .claude/skills instead
./install.sh --list                # show available + install status
./install.sh --uninstall           # remove symlinks pointing back into this repo
```

Restart Claude Code afterward and run `/help` to confirm the skills appear.

### Manual install

Copy or symlink any skill directory into a `.claude/skills/` folder:

```bash
ln -s "$PWD/.claude/skills/adr" ~/.claude/skills/adr
```

## Configuring `commit-and-report`

It auto-detects the default branch, commit-message shape, branch-naming style, and ticket key from the
repo's git history — no setup needed. To pin conventions explicitly, drop a
`.claude/commit-and-report.json` in the target repo:

```json
{
  "defaultBranch": "main",
  "ticketRegex": "[A-Z][A-Z0-9]+-[0-9]+",
  "requireTicket": true,
  "branchTemplate": "{ticket}_{slug}",
  "commitTemplate": "[{ticket}] - {message}",
  "prTitleTemplate": "[{ticket}] {title}",
  "mergeStrategy": "squash",
  "tracker": "jira"
}
```

Every key is optional; anything omitted is inferred.

## Writing an agnostic skill

Guidelines used across this repo — follow them for anything you add:

1. **No hardcoded specifics.** No company names, ticket prefixes (`ABCD-`, `JIRA-`), absolute paths,
   cloud accounts, or team names in the skill body. Detect from the repo or take it as a parameter.
2. **Discover, don't assume.** Read `git`, existing files, and config before acting. The default
   branch comes from `origin/HEAD`, not a literal `main`.
3. **Degrade gracefully.** If an optional integration (Jira/Atlassian MCP, `gh`) isn't present, skip
   that step silently rather than failing.
4. **Config file for overrides.** When behavior legitimately varies per repo, read an optional
   `.claude/<skill>.json` — never bake one project's choice into the skill.
5. **A precise `description`.** The frontmatter `description` is the *only* thing Claude sees when
   deciding whether to trigger the skill. State when to use it and the trigger phrase.
6. **Guardrails are explicit.** List the things the skill must never do (auto-merge, force-push a
   default branch, `git add -A`). These are load-bearing.
7. **Don't hardcode a model name** in commit trailers or output — it goes stale.

## Suggested next improvements

- Add a `CONTRIBUTING.md` with the skill-authoring checklist above.
- Add a lightweight CI check (`grep`) that fails if a skill body reintroduces a hardcoded
  ticket prefix or absolute home path.
- Version the collection (git tags) so teams can pin a known-good set.

## Repository layout

```
.claude/skills/<name>/SKILL.md   # one skill per directory
install.sh                       # symlink installer
.gitignore                       # ignores settings.local.json (machine-local)
```

> `.claude/settings.local.json` is intentionally git-ignored — it holds per-machine tool permissions
> and absolute paths that should not be shared.
