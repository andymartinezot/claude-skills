---
name: statusline-builder
description: Install, customize, update or repair a Claude Code status line from the bundled, tested scripts — model, context %, cost and 5h quota, session time, lines changed, prompt-cache countdown, AWS credential expiry, live subagents, git branch with ahead/behind, session name — plus per-subagent rows. Asks which segments to show, writes ~/.claude/statusline.json and settings.json (with a backup), then proves it renders. Trigger on `/statusline-builder`, "set up my status line", "add X to the status bar", "my status line is blank", or when replicating the status line on a new machine.
---

# Status line builder

Installs two bundled scripts and one config file, then proves they work. The scripts are the product; don't rewrite them from scratch. Customization goes in `~/.claude/statusline.json`, never into the scripts, so updates stay a plain copy.

| File | Installed to |
|---|---|
| `scripts/statusline.py` | `~/.claude/statusline.py` |
| `scripts/statusline-subagent.py` | `~/.claude/statusline-subagent.py` |
| (written by step 3) | `~/.claude/statusline.json` |

`references/segments.md` is the segment menu (what each shows, which fields it reads, when it hides). `references/spec.md` is the contract the scripts must keep — read it before changing either script.

## 1. Pre-flight (read-only, in parallel)

- `claude --version`. Below 2.1.251 there is no `prompt_cache` (cache segment stays hidden); below 2.1.205 subagent rows have no model or context %.
- The interpreter: `/usr/bin/python3` on macOS, otherwise `command -v python3`. Use it by **absolute path** — the status line shell does not get the interactive PATH. Needs Python 3.9+.
- Current state: the `statusLine` and `subagentStatusLine` keys of `~/.claude/settings.json`, and whether `~/.claude/statusline.py`, `statusline-subagent.py` and `statusline.json` exist.
- If the installed scripts exist, `diff` them against the bundled ones. Same: this is a config-only change. Different and not from this skill (no `~/.claude/statusline.json` alongside, or a different structure): show the user what would be replaced and ask before going on.

## 2. Choose segments

One `AskUserQuestion` round (multiSelect). Propose the current `segments` from `statusline.json` when it exists, otherwise the defaults. Take the options from `references/segments.md`. `model`, `context` and `git` are always on; ask about the rest:

- **Usage:** cost / 5h quota, session duration, lines changed
- **Freshness:** prompt-cache countdown, AWS credential expiry
- **Activity:** live subagent count, session name

Then, only if relevant: one row or two (a `newline` entry starts the second row), and for AWS whether to show it only when AWS is in use (`auto`, default), always, or never. Don't ask about thresholds; mention they're in the config.

## 3. Install

1. **Back up** `~/.claude/settings.json` to `settings.json.bak-<YYYYMMDD-HHMMSS>`, and any script that will be replaced to `<name>.bak-<ts>`.
2. Copy both scripts to `~/.claude/` and `chmod +x` them.
3. Write `~/.claude/statusline.json` with only the keys the user changed from the defaults (`segments`, and `aws.mode` if not `auto`). An omitted key falls back to the defaults in `statusline.py`. A broken file falls back too; it never blanks the line.
4. Patch `~/.claude/settings.json` by **loading, modifying and dumping JSON** — never a text edit. Keep every existing key, and confirm afterwards that the key set is unchanged apart from these two:

   ```json
   "statusLine": {"type": "command", "command": "<python> ~/.claude/statusline.py", "padding": 1, "refreshInterval": 30},
   "subagentStatusLine": {"type": "command", "command": "<python> ~/.claude/statusline-subagent.py"}
   ```

   `refreshInterval` keeps the cache and AWS countdowns current while the session is idle; drop it if neither segment is on. Keep a `padding` the user already had.

## 4. Verify before saying it works

1. `bash scripts/test.sh` (from this skill's directory). It runs every case in `references/spec.md` against a throwaway HOME and throwaway repos — no real credentials or settings are read. Show its output. Any FAIL: fix the script, not the test, unless the test is wrong, and say which.
2. Render the installed script on the last real payload, if there is one: `<python> ~/.claude/statusline.py < /tmp/statusline-last-input.json`.
3. After your next reply renders the status line for real, read `/tmp/statusline-last-input.json` (and the subagent dump, if a subagent ran). Confirm each field the chosen segments use is present, using `references/segments.md`. Don't print paths or the transcript location back to the user — field names only.

Report: segments on, the backup paths, test result, and anything hidden for a known reason (e.g. no `rate_limits` on this provider).

## Changing or repairing it later

- **Add / remove / reorder a segment:** edit `segments` in `~/.claude/statusline.json`. No script change, no restart; it applies on the next render.
- **Blank status line:** run the `statusLine` command by hand on `/tmp/statusline-last-input.json`; check the interpreter path exists; `claude --debug` logs the script's stderr.
- **A new segment:** add it to `scripts/statusline.py` in this repo (a `seg_<name>` function plus its `SEGMENTS` entry), add a case to `scripts/test.sh` and a row to `references/segments.md`, run the tests, then re-install with this skill.

## Guardrails

- **Never print a credential.** The AWS segment reads expiry fields only; don't widen what it reads, and never `cat` or `grep` a credentials or token-cache file to debug it — read the parsed expiry instead.
- **It must never go blank:** every path prints something and exits 0. Keep that when editing.
- **No org-specific values in the scripts** — no profile names, hosts or paths. They go in `~/.claude/statusline.json` if they're ever needed.
- **Back up before every write** to `settings.json` or an installed script, and never touch other keys.
