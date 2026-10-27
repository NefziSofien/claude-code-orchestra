#!/usr/bin/env bash
# Wire lean-ctx into Claude Code (and Cursor) with the hardened shell policy used by this repo.
# Requires lean-ctx on PATH: see lean-ctx/README.md for install commands.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: lean-ctx/setup.sh [--privacy] [--dry-run]

  --privacy   also turn lean-ctx telemetry off and limit file access to project folders
  --dry-run   print what would happen, change nothing

Steps: lean-ctx wrap claude (and cursor if ~/.cursor exists), shell_hook_mode=deny,
merge lean-ctx/claude-permissions.json into your Claude Code settings.json (backed up first).
EOF
}

PRIVACY=no
DRY=no
for arg in "$@"; do
  case "$arg" in
    --privacy) PRIVACY=yes ;;
    --dry-run) DRY=yes ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage >&2; exit 1 ;;
  esac
done

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

run() {
  echo "  \$ $*"
  if [ "$DRY" = no ]; then "$@"; fi
}

if ! command -v lean-ctx >/dev/null 2>&1; then
  echo "lean-ctx is not installed. Install it first, for example:" >&2
  echo "  curl -fsSL https://leanctx.com/install.sh | sh" >&2
  echo "  (or: brew tap yvgude/lean-ctx && brew install lean-ctx / npm install -g lean-ctx-bin)" >&2
  exit 1
fi

echo "lean-ctx: $(lean-ctx --version 2>/dev/null | head -1)"
echo "Connect agents"
run lean-ctx wrap claude
if [ -d "$HOME/.cursor" ]; then run lean-ctx wrap cursor; fi

echo "Shell policy: every command goes through ctx_shell and its allowlist"
run lean-ctx config set shell_hook_mode deny

if [ "$PRIVACY" = yes ]; then
  echo "Privacy"
  run lean-ctx telemetry off
  run lean-ctx config set path_jail_scope projects
fi

echo "Claude Code permissions ($CLAUDE_DIR/settings.json)"
PY="$(command -v python3 || command -v python || true)"
if [ -n "$PY" ]; then
  if [ "$DRY" = yes ]; then
    "$PY" "$HERE/merge_permissions.py" "$CLAUDE_DIR/settings.json" --dry-run
  else
    "$PY" "$HERE/merge_permissions.py" "$CLAUDE_DIR/settings.json"
  fi
else
  echo "  python3 not found: merge lean-ctx/claude-permissions.json into $CLAUDE_DIR/settings.json by hand."
fi

CONFIG="$(lean-ctx config path 2>/dev/null || true)"
if [ -n "$CONFIG" ] && [ -f "$CONFIG" ] && grep -q '"sudo"' "$CONFIG"; then
  echo "Warning: 'sudo' is in your lean-ctx allowlist ($CONFIG). Remove it from shell_allowlist_extra."
fi

cat <<'EOF'

Done. Next steps:
  1. Restart Claude Code / Cursor so the MCP server and hooks reload.
  2. Run `lean-ctx doctor` and fix anything it flags.
  3. Allow the build and test commands your projects need, one by one: `lean-ctx allow <cmd>`.
EOF
