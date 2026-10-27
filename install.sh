#!/usr/bin/env bash
# Install the orchestrate skill, agents and Cursor rules into your home directory.
# Default: symlinks, so `git pull` in this repo updates your setup.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./install.sh [--copy] [--no-cursor] [--with-claude-md] [--dry-run]

  --copy            copy files instead of symlinking them
  --no-cursor       skip the Cursor rule and agents (~/.cursor)
  --with-claude-md  append the "Orchestrate big tasks" rule to ~/.claude/CLAUDE.md
  --dry-run         print what would happen, change nothing

Existing files are backed up as <file>.bak-<timestamp> before being replaced.
EOF
}

MODE=link
CURSOR=auto
CLAUDE_MD=no
DRY=no
for arg in "$@"; do
  case "$arg" in
    --copy) MODE=copy ;;
    --no-cursor) CURSOR=no ;;
    --with-claude-md) CLAUDE_MD=yes ;;
    --dry-run) DRY=yes ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage >&2; exit 1 ;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
CURSOR_DIR="$HOME/.cursor"

run() {
  if [ "$DRY" = yes ]; then echo "  [dry-run] $*"; else "$@"; fi
}

install_file() {
  local src="$1" dst="$2"
  run mkdir -p "$(dirname "$dst")"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then
    echo "  ok       $dst (already linked)"
    return
  fi
  if [ "$MODE" = copy ] && [ -f "$dst" ] && [ ! -L "$dst" ] && cmp -s "$src" "$dst"; then
    echo "  ok       $dst (already up to date)"
    return
  fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    run mv "$dst" "$dst.bak-$STAMP"
    echo "  backup   $dst.bak-$STAMP"
  fi
  if [ "$MODE" = link ]; then run ln -s "$src" "$dst"; else run cp "$src" "$dst"; fi
  echo "  $MODE     $dst"
}

echo "Claude Code ($CLAUDE_DIR)"
install_file "$REPO/claude/skills/orchestrate/SKILL.md" "$CLAUDE_DIR/skills/orchestrate/SKILL.md"
for agent in explorer implementer verifier; do
  install_file "$REPO/claude/agents/$agent.md" "$CLAUDE_DIR/agents/$agent.md"
done

if [ "$CLAUDE_MD" = yes ]; then
  if grep -qs '^## Orchestrate big tasks' "$CLAUDE_DIR/CLAUDE.md"; then
    echo "  ok       $CLAUDE_DIR/CLAUDE.md already has the rule"
  elif [ "$DRY" = yes ]; then
    echo "  [dry-run] append claude/CLAUDE.snippet.md to $CLAUDE_DIR/CLAUDE.md"
  else
    { [ -s "$CLAUDE_DIR/CLAUDE.md" ] && echo; cat "$REPO/claude/CLAUDE.snippet.md"; } >> "$CLAUDE_DIR/CLAUDE.md"
    echo "  append   $CLAUDE_DIR/CLAUDE.md"
  fi
fi

if [ "$CURSOR" = no ] || { [ "$CURSOR" = auto ] && [ ! -d "$CURSOR_DIR" ]; }; then
  echo "Cursor: skipped"
else
  echo "Cursor ($CURSOR_DIR)"
  install_file "$REPO/cursor/rules/orchestrate.mdc" "$CURSOR_DIR/rules/orchestrate.mdc"
  for agent in explorer verifier; do
    install_file "$REPO/cursor/agents/$agent.md" "$CURSOR_DIR/agents/$agent.md"
  done
fi

cat <<EOF

Done. Next steps:
  1. Restart Claude Code / Cursor so they pick up the new skill and agents.
  2. Optional: copy examples/project-skills/* into <your-project>/.claude/skills/ and adapt them.
EOF
[ "$CLAUDE_MD" = yes ] || echo "  3. Optional: add claude/CLAUDE.snippet.md to ~/.claude/CLAUDE.md (or rerun with --with-claude-md) so big tasks trigger orchestration automatically."
