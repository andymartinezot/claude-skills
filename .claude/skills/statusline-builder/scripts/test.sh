#!/usr/bin/env bash
# test.sh — prove the status line scripts render, never blank, and always exit 0.
#
#   bash test.sh [script-dir]     default: this script's directory
#   PY=/path/to/python3 bash test.sh
#
# Runs against a throwaway HOME (fake AWS credentials, fake config) and throwaway
# git repos, so it never reads real credentials or touches real settings.
# Prints each case's rendered output, then PASS/FAIL per check. Exit 1 on any FAIL.
set -uo pipefail

DIR="$(cd "${1:-$(dirname "${BASH_SOURCE[0]}")}" && pwd -P)"
MAIN="$DIR/statusline.py"; SUB="$DIR/statusline-subagent.py"
if [[ -z "${PY:-}" ]]; then
  if [[ -x /usr/bin/python3 ]]; then PY=/usr/bin/python3; else PY="$(command -v python3)"; fi
fi
GIT=/usr/bin/git; [[ -x $GIT ]] || GIT="$(command -v git)"

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; mkdir -p "$HOME/.aws" "$HOME/.claude"
unset AWS_SHARED_CREDENTIALS_FILE AWS_DEFAULT_PROFILE CLAUDE_CODE_USE_BEDROCK
export AWS_PROFILE=test COLUMNS=0
# keep the real /tmp payload dumps intact
export STATUSLINE_DUMP="$T/main-dump.json" STATUSLINE_SUBAGENT_DUMP="$T/sub-dump.json"
now=$(date +%s)
printf '[test]\naws_access_key_id = FAKE\nsession_expiration = %s\n[old]\nexpiration = %s\n' \
  $((now + 2730)) $((now - 60)) > "$HOME/.aws/credentials"

# repos: one pushed with 2 local commits ahead, one never pushed, one plain dir
g() { "$GIT" -c user.email=t@example.com -c user.name=t -c init.defaultBranch=main "$@" >/dev/null 2>&1; }
g init --bare "$T/remote.git"
g init "$T/repo"; g -C "$T/repo" commit --allow-empty -m one
g -C "$T/repo" remote add origin "$T/remote.git"; g -C "$T/repo" push -u origin main
g -C "$T/repo" commit --allow-empty -m two; g -C "$T/repo" commit --allow-empty -m three
g init "$T/fresh"; g -C "$T/fresh" commit --allow-empty -m one
mkdir -p "$T/plain"

fails=0
run() {  # run <label> <stdin> [dir] -> sets OUT, checks non-empty + exit 0
  local label="$1" input="$2" dir="${3:-$T/plain}" rc
  OUT="$(cd "$dir" && printf '%s' "$input" | "$PY" "$MAIN")"; rc=$?
  printf '%-26s %s\n' "$label" "$OUT"
  [[ $rc -eq 0 && -n "$OUT" ]] || { echo "FAIL  $label: exit=$rc, empty=$([[ -z $OUT ]] && echo yes || echo no)"; fails=$((fails + 1)); }
}
has()  { grep -qF -- "$2" <<<"$(sed $'s/\033\\[[0-9;]*m//g' <<<"$OUT")" || { echo "FAIL  $1: missing '$2'"; fails=$((fails + 1)); }; }
lacks(){ ! grep -qF -- "$2" <<<"$(sed $'s/\033\\[[0-9;]*m//g' <<<"$OUT")" || { echo "FAIL  $1: unexpected '$2'"; fails=$((fails + 1)); }; }

full() {  # full <cwd> [extra json merged at top level]
  cat <<JSON
{"session_name":"fix login flow","model":{"id":"claude-opus","display_name":"Opus"},"effort":{"level":"high"},
 "fast_mode":false,"workspace":{"current_dir":"$1"},
 "cost":{"total_cost_usd":1.234,"total_duration_ms":1260000,"total_lines_added":120,"total_lines_removed":8},
 "context_window":{"used_percentage":63,"context_window_size":1000000},"exceeds_200k_tokens":true,
 "rate_limits":{"five_hour":{"used_percentage":41,"resets_at":$((now + 11130))},"seven_day":{"used_percentage":12}},
 "prompt_cache":{"warm":true,"caching_observed":true,"expires_at":$((now + 200))}${2:-}}
JSON
}

echo "== main status line"
run "1 full payload" "$(full "$T/repo")" "$T/repo"
# golden: the exact default line, segment for segment. Change it only on purpose.
GOLDEN='Opus high │ ctx 63% │ $1.23 │ usage 41% ↻3h05m │ ⏱ 21m │ +120 −8 │ cache warm 3m │ aws 45m │ repo ⎇ main ↑2 │ fix login flow'
plain_out="$(sed $'s/\033\\[[0-9;]*m//g' <<<"$OUT")"
[[ "$plain_out" == "$GOLDEN" ]] && echo "PASS  golden default line" || { echo "FAIL  golden: expected '$GOLDEN'"; fails=$((fails + 1)); }
lacks "full (1M window ignores exceeds_200k)" "63%!"
lacks "full (no weekly by default)" "wk 12%"
run "usage absent (Bedrock)" '{"cost":{"total_cost_usd":0.5}}'; lacks "no rate_limits" "usage"
run "usage high, no reset" '{"rate_limits":{"five_hour":{"used_percentage":91}}}'; has "usage high" "usage 91%"; lacks "no reset" "↻"
run "2 {}" '{}'
run "3 malformed" '{"model":'
has "malformed" "unparseable"
run "4 empty stdin" ''
run "5 used_percentage null" '{"context_window":{"used_percentage":null}}'
has "null ctx" "ctx --"
run "6a git repo, ahead 2" "$(full "$T/repo")" "$T/repo"; has "repo" "repo ⎇ main"
run "6b never pushed" "{\"workspace\":{\"current_dir\":\"$T/fresh\"}}"; has "fresh" "↑?"
run "6c outside git" "{\"workspace\":{\"current_dir\":\"$T/plain\"}}"; has "plain" "no-git"
run "cache cold" '{"prompt_cache":{"warm":false,"caching_observed":true,"expires_at":null}}'; has "cold" "cache cold"
run "200k window warning" '{"context_window":{"used_percentage":90,"context_window_size":200000},"exceeds_200k_tokens":true}'; has "200k" "90%!"
AWS_PROFILE=old run "aws expired" '{}'; has "expired" "aws EXPIRED"
AWS_PROFILE= HOME="$T/noaws" run "aws always, none found" '{}'; has "no aws" "no-aws"
AWS_PROFILE= AWS_CREDENTIAL_EXPIRATION="$(date -u -r $((now + 5520)) +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d @$((now + 5520)) +%Y-%m-%dT%H:%M:%SZ)" \
  HOME="$T/noaws" run "aws from env expiration" '{}'; has "aws env" "aws 1h3"
run "lines zero still shown" '{"cost":{"total_lines_added":180,"total_lines_removed":0}}'; has "lines zero" "+180 −0"
run "no lines fields" '{}'; lacks "no lines" "+0"
COLUMNS=60 run "narrow terminal (60)" "$(full "$T/repo")" "$T/repo"
w=$("$PY" -c 'import re,sys; print(len(re.sub(r"\033\[[0-9;]*m","",sys.argv[1])))' "$OUT"); [[ $w -le 60 ]] || { echo "FAIL  narrow: $w cols"; fails=$((fails + 1)); }
has "narrow keeps git" "⎇ main"
echo '{"segments":["model","context","newline","git"]}' > "$HOME/.claude/statusline.json"
run "config: two rows" "$(full "$T/repo")" "$T/repo"
[[ $(wc -l <<<"$OUT") -eq 2 ]] || { echo "FAIL  two rows: got $(wc -l <<<"$OUT")"; fails=$((fails + 1)); }
echo '{"aws":{"mode":"auto"},"usage_week":true}' > "$HOME/.claude/statusline.json"
AWS_PROFILE= run "config: aws auto, weekly" "$(full "$T/repo")" "$T/repo"; lacks "aws auto" "aws"; has "weekly" "wk 12%"
echo 'not json' > "$HOME/.claude/statusline.json"
run "config: broken file" '{}'; has "broken config" "ctx --"
rm -f "$HOME/.claude/statusline.json"

echo; echo "== subagent rows"
tasks="{\"columns\":80,\"tasks\":[
 {\"id\":\"a1\",\"type\":\"local_agent\",\"agentType\":\"Explore\",\"status\":\"running\",\"description\":\"Find auth code\",\"label\":\"Reading src/auth\",\"startTime\":$(( (now - 95) * 1000 )),\"model\":\"global.anthropic.claude-haiku-4-5-20251001-v1:0\",\"contextWindowSize\":200000,\"tokenCount\":50000},
 {\"id\":\"b2\",\"type\":\"local_agent\",\"status\":\"completed\",\"description\":\"Done task\",\"label\":\"Done task\",\"startTime\":$(( now * 1000 ))},
 {\"type\":\"local_agent\",\"status\":\"running\"}]}"
SOUT="$(printf '%s' "$tasks" | "$PY" "$SUB")"; rc=$?
echo "$SOUT"
[[ $rc -eq 0 ]] || { echo "FAIL  subagent exit=$rc"; fails=$((fails + 1)); }
"$PY" - "$SOUT" <<'PYCHK' || fails=$((fails + 1))
import json, re, sys
rows = [json.loads(l) for l in sys.argv[1].splitlines() if l.strip()]
by = {r["id"]: r["content"] for r in rows}
plain = lambda s: re.sub(r"\033\[[0-9;]*m", "", s)
ok = (set(by) == {"a1", "b2"} and by["b2"] == ""
      and all(x in plain(by["a1"]) for x in ("Explore", "running", "Reading src/auth", "25%", "haiku-4-5", "1m3")))
print("PASS  subagent rows: running shown, completed hidden, id-less task left default" if ok
      else f"FAIL  subagent rows: {by}")
sys.exit(0 if ok else 1)
PYCHK
for bad in '' '{}' 'nope' '{"tasks":"x"}'; do
  o="$(printf '%s' "$bad" | "$PY" "$SUB")"; rc=$?
  [[ $rc -eq 0 && -z "$o" ]] || { echo "FAIL  subagent hostile input '$bad': exit=$rc out='$o'"; fails=$((fails + 1)); }
done

[[ -s "$STATUSLINE_DUMP" && -s "$STATUSLINE_SUBAGENT_DUMP" ]] || { echo "FAIL  payload dumps were not redirected"; fails=$((fails + 1)); }
echo; [[ $fails -eq 0 ]] && echo "ALL PASS ($PY)" || echo "$fails FAIL"
exit $(( fails > 0 ))
