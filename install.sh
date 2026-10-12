#!/usr/bin/env bash
#
# Install skills from this repo into a Claude Code skills directory by symlinking.
# Symlinks (not copies) so `git pull` here updates every install.
#
#   ./install.sh                        # install all skills for the current user (~/.claude/skills)
#   ./install.sh adr handoff resume-handoff     # install only these
#   ./install.sh --project ~/code/app   # install into that repo's .claude/skills instead
#   ./install.sh --list                 # show what's available and what's installed
#   ./install.sh --uninstall            # remove symlinks that point back into this repo
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_DIR/.claude/skills"
DEST_DIR="$HOME/.claude/skills"
MODE="install"
SELECTED=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) DEST_DIR="${2:?--project needs a path}/.claude/skills"; shift 2 ;;
    --dest)    DEST_DIR="${2:?--dest needs a path}"; shift 2 ;;
    --list)    MODE="list"; shift ;;
    --uninstall) MODE="uninstall"; shift ;;
    -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown flag: $1" >&2; exit 2 ;;
    *)  SELECTED+=("$1"); shift ;;
  esac
done

[[ -d "$SRC_DIR" ]] || { echo "no skills found at $SRC_DIR" >&2; exit 1; }

available=()
for d in "$SRC_DIR"/*/; do
  [[ -f "$d/SKILL.md" ]] && available+=("$(basename "$d")")
done
[[ ${#available[@]} -gt 0 ]] || { echo "no SKILL.md files under $SRC_DIR" >&2; exit 1; }

if [[ "$MODE" == "list" ]]; then
  echo "source: $SRC_DIR"
  echo "target: $DEST_DIR"
  echo
  for s in "${available[@]}"; do
    if [[ -L "$DEST_DIR/$s" ]]; then status="linked"
    elif [[ -e "$DEST_DIR/$s" ]]; then status="EXISTS (not a link)"
    else status="-"; fi
    printf '  %-28s %s\n' "$s" "$status"
  done
  exit 0
fi

targets=("${SELECTED[@]:-${available[@]}}")

if [[ "$MODE" == "uninstall" ]]; then
  for s in "${targets[@]}"; do
    link="$DEST_DIR/$s"
    if [[ -L "$link" && "$(readlink "$link")" == "$SRC_DIR/"* ]]; then
      rm "$link"; echo "removed  $s"
    else
      echo "skipped  $s (not a symlink into this repo)"
    fi
  done
  exit 0
fi

mkdir -p "$DEST_DIR"
for s in "${targets[@]}"; do
  src="$SRC_DIR/$s"
  [[ -f "$src/SKILL.md" ]] || { echo "skipped  $s (no SKILL.md)"; continue; }
  link="$DEST_DIR/$s"

  if [[ -L "$link" ]]; then
    [[ "$(readlink "$link")" == "$src" ]] && { echo "ok       $s"; continue; }
    ln -sfn "$src" "$link"; echo "relinked $s"
  elif [[ -e "$link" ]]; then
    echo "SKIPPED  $s — a real directory already exists at $link (move it aside first)" >&2
  else
    ln -s "$src" "$link"; echo "linked   $s"
  fi
done

echo
echo "Installed into $DEST_DIR — restart Claude Code, then run /help to confirm."
