# Contract for the status line scripts

What `statusline.py` and `statusline-subagent.py` must keep doing. Read this before changing either; `scripts/test.sh` checks every item marked ✓.

Field names come from the official schema: https://code.claude.com/docs/en/statusline. Re-read it when adding a segment, and don't guess names.

## Hard requirements

- ✓ **Deterministic default.** With no `~/.claude/statusline.json`, the output is the standard line in `segments.md`, segment for segment. The golden test in `test.sh` pins it; change it there, in `SKILL.md` and in `segments.md` together.
- ✓ **Never blank.** A non-zero exit or empty stdout blanks the status line. Catch every exception, always print something, always exit 0. The subagent script is the exception that proves the rule: printing nothing there means "default rows", which is the right fallback.
- ✓ **Any field can be missing or null**, especially before the first API response. Absent data hides its segment. Never show a fake `0`.
- **Fast.** It runs on every assistant message, and every `refreshInterval` tick. Git calls get short timeouts and use `git status --porcelain -uno`. No network calls.
- **Absolute paths** for the interpreter and git; the status line shell doesn't get the interactive PATH.
- **Python 3.9 compatible** — the macOS system interpreter.
- **No credentials on screen or in dumps.** Read expiry fields only.
- **Agnostic.** No org, host, profile or path values in the scripts; anything per-machine goes in `~/.claude/statusline.json`.
- Each script writes its last stdin to `/tmp` (`statusline-last-input.json`, `statusline-subagent-last-input.json`) so field names can be checked against real payloads.

## Known traps

- **The main `statusLine` payload has no subagent data.** Only `subagentStatusLine` gets a `tasks` array. The main line's count uses how recently the subagent logs were written: `<transcript_path without .jsonl>/subagents/agent-*.jsonl` modified in the last ~45 s. Finished logs have no end marker, so the count is best-effort.
- **`subagentStatusLine` output is JSON, not text.** One line per row: `{"id": "<task id>", "content": "<row body>"}`. Plain text is ignored. Omit a task to keep its default row; `"content": ""` hides it.
- ✓ **`exceeds_200k_tokens` is a fixed 200k threshold**, not the model's window. On a 1M-context model it fires at 20% used. Only warn on it when `context_window_size` ≤ 200,000.
- ✓ **`rate_limits` is absent with some providers** (AWS Bedrock, for example). Leave it out quietly.
- **`prompt_cache` is absent until the first response**, and `expires_at` is `null` when the last response had no cache tokens. Claude Code re-renders when a warm cache reaches `expires_at`, but a countdown only ticks with `refreshInterval`.
- **`session_name` is absent** until there's a custom name (`/rename`, `--name`) or an AI-generated title.
- **`COLUMNS`**, not `tput cols`: Claude Code captures stdout, so the script can't query the terminal. `COLUMNS` may be `0` or unset; then don't trim.
- **In `tasks` entries:** `name` and `model` may be missing; `label` equals `description` when there's no progress summary, so don't print both; `model` may be a long provider ID such as `global.anthropic.claude-haiku-4-5-20251001-v1:0` — shorten it to `haiku-4-5`.
- **AWS expiry sources differ.** Credential helpers write an `*expir*` key into the profile (epoch seconds, millis or ISO-8601); SSO logins keep `expiresAt` in `~/.aws/sso/cache/*.json`, alongside client-registration files that carry a different expiry. Static keys have no expiry: hide the segment.

## Test cases (`scripts/test.sh`)

1. ✓ A realistic full payload — every default segment renders, and the plain-text line equals the golden line exactly.
2. ✓ `{}`
3. ✓ Malformed JSON.
4. ✓ Empty stdin.
5. ✓ `used_percentage: null` → `ctx --`.
6. ✓ Inside a git repo (ahead of upstream → `↑2`), a repo never pushed (`↑?`), and outside git (`no-git`).
7. ✓ A `tasks` payload with one running, one completed and one id-less task: the running row renders, the completed one is hidden, the id-less one is left to the default.

Plus: cache cold, the ≤200k warning, AWS expired, `no-aws` when nothing is found, AWS from `AWS_CREDENTIAL_EXPIRATION`, `+180 −0` (zero removed still shown), no `lines` fields, a narrow terminal (fits, keeps git), a two-row config, usage hidden without `rate_limits`, usage with no reset time, weekly usage only, `aws.mode: auto` + `"usage_week": false` config, a broken config file, and hostile subagent input.
