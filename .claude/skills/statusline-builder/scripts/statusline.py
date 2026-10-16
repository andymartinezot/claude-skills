#!/usr/bin/env python3
"""Claude Code status line.

Default output (one row, always this order):

  Opus 5.5 high │ ctx 13% │ $3.62 │ usage 7% ↻3h05m · wk 1% │ ⏱ 78h09m │ +180 −0 │ cache cold │ aws 1h37m │ no-git │ session-name

Segments (DEFAULTS["segments"] is the default line; override in ~/.claude/statusline.json):
  model    model name, fast, effort level
  context  ctx NN%, green / yellow / red
  cost     session cost
  usage    plan usage as /usage shows it: current session (5-hour window), time to reset, current week
  duration session wall-clock time
  lines    lines added / removed this session
  cache    prompt cache: "cache warm 58m" until it goes cold, or "cache cold"
  aws      time until the active AWS credentials expire, or "no-aws"
  agents   live subagent count (best-effort, off by default)
  git      repo, branch, dirty mark, ahead / behind upstream, or "no-git"
  session  session name
  newline  pseudo-segment: start a second row

Design notes:
  - Invoked with the statusLine JSON on stdin. A non-zero exit or empty stdout
    blanks the status line, so every path is wrapped and always prints a line.
  - Uses absolute binary paths; the status line shell does not necessarily
    have the interactive PATH.
  - Any payload field can be missing or null. Absent data drops its segment;
    it never renders as a fake 0.
  - Never prints a credential. The aws segment reads expiry fields only.
  - Python 3.9 compatible (macOS system python).
"""
import glob
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

CONFIG = os.path.expanduser("~/.claude/statusline.json")
DUMP = os.environ.get("STATUSLINE_DUMP", "/tmp/statusline-last-input.json")  # tests redirect it

DEFAULTS = {
    "segments": ["model", "context", "cost", "usage", "duration", "lines", "cache", "aws", "git", "session"],
    # dropped first-to-last while the row is wider than the terminal
    "drop_order": ["session", "lines", "duration", "agents", "cost", "usage", "cache", "aws"],
    "branch_max": 28,
    "session_max": 24,
    "agent_fresh_secs": 45,   # a log touched more recently than this = agent still working
    "cache_warn_secs": 120,   # cache countdown turns yellow below this
    "usage_week": True,       # false: hide the weekly limit ("· wk NN%")
    "aws": {
        "mode": "always",     # always: "no-aws" when no expiry is found | auto: only with CLAUDE_CODE_USE_BEDROCK or AWS_PROFILE | off
        "warn_secs": 3600,
        "crit_secs": 600,
    },
}

# ANSI
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
SKY = "\033[38;5;75m"
GRAY = "\033[90m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def find_git():
    for p in ("/usr/bin/git", "/opt/homebrew/bin/git", "/usr/local/bin/git", "/bin/git"):
        if os.access(p, os.X_OK):
            return p
    return "git"


GIT = find_git()


def load_config():
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(CONFIG) as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    except Exception:
        pass  # missing or broken config = defaults
    return cfg


def sh(args, timeout=1.0):
    """Run a command, return stripped stdout or None. Never raises."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def fmt_secs(secs):
    secs = int(secs)
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    return f"{secs // 3600}h{(secs % 3600) // 60:02d}m"


def truncate(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


# ---- segments ----------------------------------------------------------------

def seg_model(d, cfg):
    m = d.get("model") or {}
    name = m.get("display_name") or m.get("id") or "?"
    s = f"{SKY}{name}{RESET}"
    if d.get("fast_mode"):
        s += f" {GRAY}fast{RESET}"
    eff = (d.get("effort") or {}).get("level")
    if eff:
        s += f" {GRAY}{eff}{RESET}"
    return s


def seg_context(d, cfg):
    cw = d.get("context_window") or {}
    pct = cw.get("used_percentage")
    if not isinstance(pct, (int, float)):
        return f"{DIM}ctx --{RESET}"  # null before the first API response
    colour = GREEN if pct < 50 else (YELLOW if pct < 80 else RED)
    out = f"{colour}ctx {pct:.0f}%{RESET}"
    # exceeds_200k_tokens is a FIXED 200k threshold, not relative to the real
    # window: on a 1M-context model it fires at 20% used. Only trust it <=200k.
    size = cw.get("context_window_size")
    if d.get("exceeds_200k_tokens") and isinstance(size, (int, float)) and size <= 200_000:
        out += f"{RED}!{RESET}"
    return out


def seg_cost(d, cfg):
    cost = (d.get("cost") or {}).get("total_cost_usd")
    if not isinstance(cost, (int, float)):
        return None
    return f"{GRAY}${cost:.2f}{RESET}"


def _usage_colour(pct):
    return GRAY if pct < 60 else (YELLOW if pct < 85 else RED)


def seg_usage(d, cfg):
    """Plan usage, as /usage shows it: current session (5-hour window) and current week."""
    rl = d.get("rate_limits") or {}  # absent on some providers (e.g. Bedrock)
    five = rl.get("five_hour") or {}
    bits = []
    pct = five.get("used_percentage")
    if isinstance(pct, (int, float)):
        s = f"{_usage_colour(pct)}{pct:.0f}%{RESET}"
        reset = five.get("resets_at")
        if isinstance(reset, (int, float)) and reset > time.time():
            s += f" {GRAY}↻{fmt_secs(reset - time.time())}{RESET}"
        bits.append(s)
    week = (rl.get("seven_day") or {}).get("used_percentage")
    if cfg.get("usage_week") and isinstance(week, (int, float)):
        bits.append(f"{_usage_colour(week)}wk {week:.0f}%{RESET}")
    if not bits:
        return None
    return f"{GRAY}usage{RESET} " + f" {GRAY}·{RESET} ".join(bits)


def seg_duration(d, cfg):
    ms = (d.get("cost") or {}).get("total_duration_ms")
    if not isinstance(ms, (int, float)):
        return None
    return f"{GRAY}⏱ {fmt_secs(ms / 1000)}{RESET}"


def seg_lines(d, cfg):
    c = d.get("cost") or {}
    add, rem = c.get("total_lines_added"), c.get("total_lines_removed")
    if not isinstance(add, int) and not isinstance(rem, int):
        return None  # field absent: don't invent a 0
    add = add if isinstance(add, int) else 0
    rem = rem if isinstance(rem, int) else 0
    return f"{GREEN}+{add}{RESET} {RED}−{rem}{RESET}"


def seg_cache(d, cfg):
    pc = d.get("prompt_cache")
    if not isinstance(pc, dict) or not pc.get("caching_observed"):
        return None  # absent before the first response, or caching not reported
    exp = pc.get("expires_at")
    if pc.get("warm") and isinstance(exp, (int, float)):
        left = exp - time.time()
        if left > 0:
            colour = GREEN if left >= cfg["cache_warn_secs"] else YELLOW
            return f"{colour}cache warm {fmt_secs(left)}{RESET}"
    return f"{YELLOW}cache cold{RESET}"


def _parse_expiry(v):
    """Epoch seconds / millis, or ISO-8601. Returns epoch seconds or None."""
    v = str(v).strip().strip('"')
    if re.fullmatch(r"\d+(\.\d+)?", v):
        t = float(v)
        return t / 1000.0 if t > 1e11 else t
    try:
        v = re.sub(r"\.\d+", "", v).replace("Z", "+00:00")
        if re.search(r"UTC$", v):
            v = v.replace("UTC", "+00:00").strip()
        return datetime.fromisoformat(v).timestamp()
    except Exception:
        return None


def _profile_expiry(profile):
    """Expiry of `profile` in the shared credentials file. Reads expiry keys only."""
    path = os.environ.get("AWS_SHARED_CREDENTIALS_FILE") or os.path.expanduser("~/.aws/credentials")
    try:
        with open(path) as f:
            section = None
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    section = line.strip("[]").strip()
                    continue
                if section != profile or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                if "expir" in key.strip().lower():
                    return _parse_expiry(val)
    except Exception:
        pass
    return None


def _sso_expiry():
    """Latest expiresAt across AWS SSO token caches."""
    latest = None
    for p in glob.glob(os.path.expanduser("~/.aws/sso/cache/*.json")):
        try:
            with open(p) as f:
                j = json.load(f)
            if "accessToken" not in j or "expiresAt" not in j:
                continue  # client registrations carry a different expiry
            t = _parse_expiry(j["expiresAt"])
            if t and (latest is None or t > latest):
                latest = t
        except Exception:
            continue
    return latest


def seg_aws(d, cfg):
    a = cfg["aws"]
    mode = a.get("mode", "always")
    if mode == "off":
        return None
    profile = os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")
    bedrock = str(os.environ.get("CLAUDE_CODE_USE_BEDROCK", "")).lower() in ("1", "true")
    if mode == "auto" and not (bedrock or profile):
        return None
    env_exp = os.environ.get("AWS_CREDENTIAL_EXPIRATION")  # set by aws-vault, granted, etc.
    exp = (_parse_expiry(env_exp) if env_exp else None) or _profile_expiry(profile or "default") or _sso_expiry()
    if exp is None:
        # static keys, or no AWS at all
        return f"{GRAY}no-aws{RESET}" if mode == "always" else None
    left = exp - time.time()
    if left <= 0:
        return f"{RED}aws EXPIRED{RESET}"
    colour = GREEN if left > a["warn_secs"] else (YELLOW if left > a["crit_secs"] else RED)
    return f"{colour}aws {fmt_secs(left)}{RESET}"


def seg_agents(d, cfg):
    """Best-effort count of subagents still working.

    The statusLine payload carries no subagent data (only subagentStatusLine
    gets it), and a finished agent's log has no terminal marker. So freshness
    of the log file is the only available signal.
    """
    tp = d.get("transcript_path")
    if not tp or not tp.endswith(".jsonl"):
        return None
    sub = tp[: -len(".jsonl")] + "/subagents"
    try:
        now, n = time.time(), 0
        with os.scandir(sub) as it:
            for e in it:
                if e.name.startswith("agent-") and e.name.endswith(".jsonl"):
                    if now - e.stat().st_mtime < cfg["agent_fresh_secs"]:
                        n += 1
        if n:
            return f"{MAGENTA}⚙ {n} agent{'s' if n > 1 else ''}{RESET}"
    except Exception:
        pass
    return None


def seg_git(d, cfg):
    cwd = (d.get("workspace") or {}).get("current_dir") or d.get("cwd") or os.getcwd()
    if sh([GIT, "-C", cwd, "rev-parse", "--is-inside-work-tree"]) != "true":
        return f"{GRAY}no-git{RESET}"
    branch = sh([GIT, "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"]) or "?"
    detached = branch == "HEAD"
    if detached:
        short = sh([GIT, "-C", cwd, "rev-parse", "--short", "HEAD"])
        branch = f"detached@{short}" if short else "detached"
    branch = truncate(branch, cfg["branch_max"])
    # -uno skips untracked files: much faster, and editor/OS noise is irrelevant
    dirty = sh([GIT, "-C", cwd, "status", "--porcelain", "-uno"], timeout=1.5)
    mark = f"{RED}*{RESET}" if dirty else ""
    root = sh([GIT, "-C", cwd, "rev-parse", "--show-toplevel"])
    repo = os.path.basename(root) if root else ""
    out = (f"{BLUE}{repo}{RESET} " if repo else "") + f"{YELLOW}⎇ {branch}{RESET}{mark}"
    if not detached and branch != "?":
        counts = sh([GIT, "-C", cwd, "rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
        if counts:
            ahead, behind = (int(x) for x in counts.split())
            if ahead:
                out += f" {YELLOW}↑{ahead}{RESET}"
            if behind:
                out += f" {CYAN}↓{behind}{RESET}"
        elif sh([GIT, "-C", cwd, "rev-parse", "--verify", "-q", "HEAD"]):
            out += f" {DIM}↑?{RESET}"  # has commits, no upstream: never pushed
    return out


def seg_session(d, cfg):
    name = d.get("session_name")
    if not name:
        return None
    return f"{GRAY}{truncate(str(name), cfg['session_max'])}{RESET}"


SEGMENTS = {
    "model": seg_model, "context": seg_context, "cost": seg_cost, "usage": seg_usage,
    "duration": seg_duration, "lines": seg_lines, "cache": seg_cache,
    "aws": seg_aws, "agents": seg_agents, "git": seg_git, "session": seg_session,
}
SEP = f" {GRAY}│{RESET} "


def visible_len(s):
    return len(ANSI_RE.sub("", s))


def fit(row, cols, drop_order):
    """Drop low-priority segments until the row fits the terminal width."""
    if cols <= 0:
        return row
    for name in drop_order:
        if visible_len(SEP.join(t for _, t in row)) <= cols:
            break
        row = [(n, t) for n, t in row if n != name]
    return row


def render(d, cfg):
    rows, row = [], []
    for name in cfg["segments"]:
        if name == "newline":
            rows.append(row)
            row = []
            continue
        fn = SEGMENTS.get(name)
        if not fn:
            continue
        try:
            text = fn(d, cfg)
        except Exception:
            text = None  # one broken segment must not blank the line
        if text:
            row.append((name, text))
    rows.append(row)
    try:
        cols = int(os.environ.get("COLUMNS") or 0)
    except ValueError:
        cols = 0
    lines = [SEP.join(t for _, t in fit(r, cols, cfg["drop_order"])) for r in rows]
    return "\n".join(l for l in lines if l) or f"{DIM}…{RESET}"


def main():
    raw = sys.stdin.read()
    try:
        d = json.loads(raw)
        if not isinstance(d, dict):
            raise ValueError
    except Exception:
        print(f"{DIM}statusline: unparseable input{RESET}")
        return
    # keep the last payload so field names can be checked against reality
    try:
        with open(DUMP, "w") as f:
            f.write(raw)
    except Exception:
        pass
    print(render(d, load_config()))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never blank the status line
        print(f"{DIM}statusline error: {type(e).__name__}{RESET}")
    sys.exit(0)
