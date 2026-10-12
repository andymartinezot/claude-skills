# Segments

Default order: `model, context, cost, duration, lines, cache, aws, agents, git, session`. Set the order and selection in `~/.claude/statusline.json` → `segments`. A segment with no data hides itself; nothing renders as a fake `0`.

| Segment | Shows | Reads | Hidden when |
|---|---|---|---|
| `model` | `Opus·high` — name, `·fast` in fast mode, effort unless `medium` | `model.display_name`, `fast_mode`, `effort.level` | never (`?` if absent) |
| `context` | `ctx 63%`, green < 50, yellow < 80, red; red `!` past 200k on a ≤200k window | `context_window.used_percentage`, `.context_window_size`, `exceeds_200k_tokens` | never (`ctx --` before the first response) |
| `cost` | `$1.23 · 5h 41%` | `cost.total_cost_usd`, `rate_limits.five_hour.used_percentage` | each piece when absent (no `rate_limits` on some providers, e.g. Bedrock) |
| `duration` | `⏱ 21m` session wall-clock | `cost.total_duration_ms` | under a minute |
| `lines` | `+120 −8` | `cost.total_lines_added`, `.total_lines_removed` | both zero |
| `cache` | `cache 3m` until the prompt cache goes cold (yellow under 2m), or `cache cold` | `prompt_cache.warm`, `.expires_at`, `.caching_observed` | before the first response, or the provider doesn't report caching |
| `aws` | `aws 45m` until the active credentials expire (yellow < 1h, red < 10m), `aws EXPIRED` | the active profile's `*expir*` key in `~/.aws/credentials` (epoch or ISO-8601), else the newest `expiresAt` in `~/.aws/sso/cache/*.json` — expiry fields only | `aws.mode` `off`; in `auto`, when neither `CLAUDE_CODE_USE_BEDROCK` nor `AWS_PROFILE` is set; credentials with no expiry |
| `agents` | `⚙ 2 agents` live subagents | mtime of `<transcript>/subagents/agent-*.jsonl` | none running; best-effort (see spec) |
| `git` | `repo ⎇ branch*` + `↑2 ↓1` vs upstream, `↑?` for a branch never pushed | `workspace.current_dir`, git | `no-git` outside a repo |
| `session` | session name, truncated | `session_name` | no custom name or AI title yet |
| `newline` | starts a second row | — | — |

## Width

When `COLUMNS` (set by Claude Code) is smaller than the row, segments are dropped in `drop_order`: `session, lines, duration, agents, cost, cache, aws`. `model`, `context` and `git` are never dropped. Each row is fitted on its own.

## Config keys (all optional)

```json
{
  "segments": ["model", "context", "cost", "cache", "aws", "git", "newline", "duration", "lines", "agents", "session"],
  "drop_order": ["session", "lines", "duration", "agents", "cost", "cache", "aws"],
  "branch_max": 28,
  "session_max": 24,
  "agent_fresh_secs": 45,
  "cache_warn_secs": 120,
  "aws": {"mode": "auto", "warn_secs": 3600, "crit_secs": 600}
}
```

## Subagent rows (`statusline-subagent.py`)

One row per running subagent: `⚙ <name> · <status> · <progress label> · <ctx %> · <short model> · <elapsed>`. Name falls back `name` → `agentType` → `description`. Completed tasks are hidden (empty `content`); failed and killed stay visible in red. Rows are cut to the payload's `columns`.
