#!/usr/bin/env python3
"""Claude Code subagent status line.

Receives {"columns": N, "tasks": [...]} on stdin and writes one JSON line per
row it overrides: {"id": "<task id>", "content": "<row body>"}. Plain text is
ignored by Claude Code. A task left out keeps the default rendering; an empty
content string hides the row (used for completed tasks).

Row: name · status · progress label · context % · short model · elapsed.
Every task field except id may be absent; absent fields are skipped.
Python 3.9 compatible (macOS system python).
"""
import json
import os
import re
import sys
import time

DUMP = os.environ.get("STATUSLINE_SUBAGENT_DUMP", "/tmp/statusline-subagent-last-input.json")  # tests redirect it
HIDE = ("completed", "done")

DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
ANSI_RE = re.compile(r"\033\[[0-9;]*m")

STATUS_COLOUR = {
    "running": MAGENTA, "in_progress": MAGENTA, "active": MAGENTA,
    "pending": YELLOW, "queued": YELLOW,
    "failed": RED, "error": RED, "killed": RED, "cancelled": DIM,
}


def elapsed(start):
    """Human-readable age from a start time in epoch millis (or seconds)."""
    try:
        t = float(start)
    except (TypeError, ValueError):
        return None
    if t > 1e11:
        t /= 1000.0
    secs = max(0, int(time.time() - t))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m{secs % 60:02d}s"
    return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"


def short_model(m):
    """'global.anthropic.claude-haiku-4-5-20251001-v1:0' -> 'haiku-4-5'."""
    s = str(m)
    s = s.split("claude-", 1)[1] if "claude-" in s else s.rsplit(".", 1)[-1]
    s = re.sub(r"\[.*\]$", "", s)                       # [1m] context suffix
    s = re.sub(r"-\d{8}(-v\d+[:.]\d+)?$", "", s)        # trailing date / version stamp
    s = re.sub(r"-v\d+([:.]\d+)?$", "", s)
    return s or str(m)


def truncate(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def fit(content, cols):
    """Cut a row to the usable width, keeping ANSI codes intact."""
    if not cols or len(ANSI_RE.sub("", content)) <= cols:
        return content
    out, seen = [], 0
    for part in re.split(r"(\033\[[0-9;]*m)", content):
        if ANSI_RE.fullmatch(part or "x"):
            out.append(part)
            continue
        room = cols - 1 - seen
        if room <= 0:
            continue
        out.append(part[:room])
        seen += min(len(part), room)
    return "".join(out) + "…" + RESET


def row(t):
    status = str(t.get("status") or "").lower()
    colour = STATUS_COLOUR.get(status, "")
    name = str(t.get("name") or t.get("agentType") or t.get("description") or t.get("type") or "agent")
    bits = [f"{colour}⚙ {truncate(name, 30)}{RESET if colour else ''}"]
    if status:
        bits.append(f"{DIM}{status}{RESET}")

    # label is the live progress summary; it equals description when there is none
    label = str(t.get("label") or t.get("description") or "").strip()
    if label and label != name:
        bits.append(truncate(label, 40))

    tok, size = t.get("tokenCount"), t.get("contextWindowSize")
    if isinstance(tok, (int, float)) and isinstance(size, (int, float)) and size:
        pct = 100.0 * tok / size
        c = GREEN if pct < 50 else (YELLOW if pct < 80 else RED)
        bits.append(f"{c}{pct:.0f}%{RESET}")
    elif isinstance(tok, (int, float)) and tok:
        bits.append(f"{DIM}{tok / 1000:.0f}k{RESET}")

    if t.get("model"):
        bits.append(f"{CYAN}{short_model(t['model'])}{RESET}")
    age = elapsed(t.get("startTime"))
    if age:
        bits.append(f"{DIM}{age}{RESET}")
    return f" {DIM}·{RESET} ".join(bits)


def main():
    raw = sys.stdin.read()
    try:
        with open(DUMP, "w") as f:
            f.write(raw)
    except Exception:
        pass
    try:
        d = json.loads(raw)
    except Exception:
        return  # no output = default rows, the correct fallback
    if not isinstance(d, dict) or not isinstance(d.get("tasks"), list):
        return
    try:
        cols = int(d.get("columns") or 0)
    except (TypeError, ValueError):
        cols = 0
    for t in d["tasks"]:
        if not isinstance(t, dict) or not t.get("id"):
            continue
        try:
            status = str(t.get("status") or "").lower()
            content = "" if status in HIDE else fit(row(t), cols)
        except Exception:
            continue  # leave this row to the default rendering
        print(json.dumps({"id": t["id"], "content": content}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # silence = default rows
    sys.exit(0)
