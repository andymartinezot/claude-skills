# Reference card

The standard line — what every install of this skill renders, left to right:

```
Opus 5.5 high │ ctx 13% │ $3.62 │ ⏱ 78h09m │ +180 −0 │ cache cold │ aws 1h37m │ no-git │ ticket-validator-session
└─ model ───┘   context   cost    duration   lines     cache        aws         git      session
```

Default order: `model, context, cost, duration, lines, cache, aws, git, session`. `scripts/test.sh` checks this exact format (golden test). A segment whose payload field is absent hides itself; nothing renders as a fake `0`.

## Segments

| # | Segment | Example | States and colours | Reads | Hidden when |
|---|---|---|---|---|---|
| 1 | `model` | `Opus 5.5 high` | name in sky blue; `fast` and the effort level (`low`, `medium`, `high`, …) in gray | `model.display_name`, `fast_mode`, `effort.level` | never (`?` if absent) |
| 2 | `context` | `ctx 13%` | green < 50 %, yellow < 80 %, red ≥ 80 %; red `!` past 200k on a ≤ 200k window; `ctx --` before the first response | `context_window.used_percentage`, `.context_window_size`, `exceeds_200k_tokens` | never |
| 3 | `cost` | `$3.62` | gray; with `"cost_quota": true` also `· 5h 41%` (gray < 60, yellow < 85, red) | `cost.total_cost_usd`, `rate_limits.five_hour.used_percentage` | field absent |
| 4 | `duration` | `⏱ 78h09m` | gray; `45s`, `21m`, `1h02m` | `cost.total_duration_ms` | field absent |
| 5 | `lines` | `+180 −0` | added green, removed red; zeros shown | `cost.total_lines_added`, `.total_lines_removed` | both fields absent |
| 6 | `cache` | `cache warm 58m` / `cache cold` | warm green, yellow under 2 m; `cache cold` yellow | `prompt_cache.warm`, `.expires_at`, `.caching_observed` | before the first response, or the provider doesn't report caching |
| 7 | `aws` | `aws 1h37m` / `aws EXPIRED` / `no-aws` | green > 1 h, yellow > 10 m, red ≤ 10 m; `aws EXPIRED` red; `no-aws` gray | `AWS_CREDENTIAL_EXPIRATION`, else the active profile's `*expir*` key in `~/.aws/credentials`, else the newest `expiresAt` in `~/.aws/sso/cache/*.json` — expiry fields only | `aws.mode` `off` (or `auto` with no `AWS_PROFILE` / `CLAUDE_CODE_USE_BEDROCK`) |
| 8 | `git` | `repo ⎇ main* ↑2 ↓1` / `no-git` | repo blue, branch yellow, `*` red when dirty, `↑?` never pushed; `no-git` gray | `workspace.current_dir`, git | never |
| 9 | `session` | `ticket-validator-session` | gray, cut to 24 chars | `session_name` | no `/rename`, `--name` or AI title yet |
| – | `agents` | `⚙ 2 agents` | magenta; best-effort (see spec) | mtime of `<transcript>/subagents/agent-*.jsonl` | **off by default**; none running |
| – | `newline` | — | starts a second row | — | — |

Separator: ` │ ` in gray.

## Troubleshooting a segment

| You see | Why | Fix |
|---|---|---|
| `ctx --` | No API response yet in this session | Send a message |
| No `cache …` | No response yet, or the provider doesn't report caching | Send a message |
| `cache cold` | The prompt cache TTL passed since the last response | Nothing; the next message rebuilds it |
| `aws EXPIRED` | The credentials found have expired | Log in again (`aws sso login`, your credential helper, …) |
| `no-aws` | No expiry found: no AWS login, or static keys | Expected without AWS; set `"aws": {"mode": "off"}` to hide it |
| `no-git` | The working directory isn't in a git repo | Expected |
| No session name | The session has no name yet | `/rename <name>` |
| Whole line missing | Bad interpreter path or the script errored | Run the `statusLine` command by hand on `/tmp/statusline-last-input.json`; `claude --debug` shows stderr |

## Width

When `COLUMNS` (set by Claude Code) is smaller than the row, segments are dropped in `drop_order`: `session, lines, duration, agents, cost, cache, aws`. `model`, `context` and `git` are never dropped. Each row is fitted on its own.

## Config keys (`~/.claude/statusline.json`, all optional)

The standard install writes no config. Write only the keys the user asked to change; delete the file to go back to the standard line.

```json
{
  "segments": ["model", "context", "cost", "duration", "lines", "cache", "aws", "git", "session"],
  "drop_order": ["session", "lines", "duration", "agents", "cost", "cache", "aws"],
  "cost_quota": false,
  "branch_max": 28,
  "session_max": 24,
  "agent_fresh_secs": 45,
  "cache_warn_secs": 120,
  "aws": {"mode": "always", "warn_secs": 3600, "crit_secs": 600}
}
```

## Subagent rows (`statusline-subagent.py`)

One row per running subagent: `⚙ <name> · <status> · <progress label> · <ctx %> · <short model> · <elapsed>`. Name falls back `name` → `agentType` → `description`. Completed tasks are hidden (empty `content`); failed and killed stay visible in red. Rows are cut to the payload's `columns`.
