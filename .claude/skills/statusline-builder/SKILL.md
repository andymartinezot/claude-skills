---
name: statusline-builder
description: Install, update or repair the standard Claude Code status line from the bundled, tested scripts. Always produces the same single row — model + effort, context %, cost, plan usage for the current session (as /usage shows), session time, lines changed, prompt-cache countdown, AWS credential expiry, git branch, session name — plus per-subagent rows. No questions: installs the default, patches settings.json (with a backup), then proves it renders. Trigger on `/statusline-builder`, "set up my status line", "add X to the status bar", "my status line is blank", or when replicating the status line on a new machine.
---

# Status line builder

Installs two bundled scripts, then proves they work. The output is **deterministic**: every install renders the same line, in this order, with no questions asked:

```
Opus 5.5 high │ ctx 13% │ $3.62 │ usage 7% ↻3h05m │ ⏱ 78h09m │ +180 −0 │ cache cold │ aws 1h37m │ no-git │ ticket-validator-session
```

`references/segments.md` has the reference card: every segment, each state it can show, its colours and the payload field it reads. `scripts/test.sh` pins this exact line as a golden test, so a format change has to be deliberate.

The scripts are the product; don't rewrite them from scratch, and don't hand-write a status line command instead. Customization is opt-in: only when the user explicitly asks for something different does it go in `~/.claude/statusline.json` — never into the scripts, so updates stay a plain copy.

| File | Installed to |
|---|---|
| `scripts/statusline.py` | `~/.claude/statusline.py` |
| `scripts/statusline-subagent.py` | `~/.claude/statusline-subagent.py` |
| (only if the user asks to customize) | `~/.claude/statusline.json` |

`references/spec.md` is the contract the scripts must keep — read it before changing either script.

## 1. Pre-flight (read-only, in parallel)

- `claude --version`. Below 2.1.251 there is no `prompt_cache` (cache segment stays hidden); below 2.1.205 subagent rows have no model or context %.
- The interpreter: `/usr/bin/python3` on macOS, otherwise `command -v python3`. Use it by **absolute path** — the status line shell does not get the interactive PATH. Needs Python 3.9+.
- Current state: the `statusLine` and `subagentStatusLine` keys of `~/.claude/settings.json`, and whether `~/.claude/statusline.py`, `statusline-subagent.py` and `statusline.json` exist.
- If the installed scripts exist, `diff` them against the bundled ones. A different status line command that isn't from this skill (a hand-written one-liner or another script) is replaced — the backup in step 2 keeps it; tell the user it was replaced.
- An existing `~/.claude/statusline.json` changes the output. Show its contents and ask once whether to keep it or remove it (removing it restores the standard line). This is the only question the skill asks.

## 2. Install

1. **Back up** `~/.claude/settings.json` to `settings.json.bak-<YYYYMMDD-HHMMSS>`, and any script that will be replaced to `<name>.bak-<ts>`.
2. Copy both scripts to `~/.claude/` and `chmod +x` them.
3. Don't write `~/.claude/statusline.json`. The defaults in `statusline.py` are the standard line. Write it only when the user asked for a change, with only the changed keys (see **Changing it** below).
4. Patch `~/.claude/settings.json` by **loading, modifying and dumping JSON** — never a text edit. Keep every existing key, and confirm afterwards that the key set is unchanged apart from these two:

   ```json
   "statusLine": {"type": "command", "command": "<python> ~/.claude/statusline.py", "padding": 1, "refreshInterval": 30},
   "subagentStatusLine": {"type": "command", "command": "<python> ~/.claude/statusline-subagent.py"}
   ```

   `refreshInterval` keeps the cache and AWS countdowns current while the session is idle. Keep a `padding` the user already had.

## 3. Verify before saying it works

1. `bash scripts/test.sh` (from this skill's directory). It runs every case in `references/spec.md` against a throwaway HOME and throwaway repos — no real credentials or settings are read — and checks the exact default line (golden test). Show the PASS/FAIL summary. Any FAIL: fix the script, not the test, unless the test is wrong, and say which.
2. Render the installed script on the last real payload, if there is one: `<python> ~/.claude/statusline.py < /tmp/statusline-last-input.json`.
3. After your next reply renders the status line for real, read `/tmp/statusline-last-input.json` (and the subagent dump, if a subagent ran). Confirm each field the chosen segments use is present, using `references/segments.md`. Don't print paths or the transcript location back to the user — field names only.

Report: the rendered line (ANSI stripped), the backup paths, the test result, and any segment showing a fallback state or hidden for a known reason (`no-aws`, no `usage` on a provider without `rate_limits`, `aws EXPIRED`, `no-git`, `ctx --`) with the reason from the reference card.

## Changing it (only when asked)

- **Add / remove / reorder a segment, a second row, the weekly usage limit, AWS only when in use:** write those keys in `~/.claude/statusline.json` (keys in `references/segments.md`). No script change, no restart; it applies on the next render.
- **Back to the standard line:** delete `~/.claude/statusline.json`.
- **Blank status line:** run the `statusLine` command by hand on `/tmp/statusline-last-input.json`; check the interpreter path exists; `claude --debug` logs the script's stderr.
- **A new segment or a change to the standard line:** edit `scripts/statusline.py` in this repo (a `seg_<name>` function plus its `SEGMENTS` entry), update the golden line in `scripts/test.sh`, the example at the top of this file and the reference card in `references/segments.md`, run the tests, then re-install with this skill.

## Guardrails

- **Never print a credential.** The AWS segment reads expiry fields only; don't widen what it reads, and never `cat` or `grep` a credentials or token-cache file to debug it — read the parsed expiry instead.
- **It must never go blank:** every path prints something and exits 0. Keep that when editing.
- **No org-specific values in the scripts** — no profile names, hosts or paths. They go in `~/.claude/statusline.json` if they're ever needed.
- **Back up before every write** to `settings.json` or an installed script, and never touch other keys.
