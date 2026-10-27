# Orchestra hooks

Python 3 stdlib only. Both scripts read the hook JSON on stdin and exit 0; blocking is done with JSON output.

- `subagent-report-check.py` (SubagentStop): blocks a worker whose final report lacks `STATUS:`, `CHANGED:`, `DECISIONS:`, `OPEN:` or `VERIFIED:`, or exceeds 10 lines. Uses `last_assistant_message`, falling back to `tool_input.message` (SubagentHandback). Skips when `stop_hook_active` is true to avoid loops.
- `scope-guard.py` (PreToolUse, Edit|Write): denies `tool_input.file_path` outside `ORCHESTRA_SCOPE` (colon-separated globs, matched on the absolute and cwd-relative path; a bare directory like `tools` also matches its contents). Unset means allow everything.

Validate state with `python3 tools/orchestra-validate.py [.orchestra/state.md]`.

## settings.json snippet

Adjust the path to where the scripts live (`.claude/settings.json` or `~/.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/hooks/scope-guard.py\"" }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/hooks/subagent-report-check.py\"" }
        ]
      }
    ]
  }
}
```

Set `ORCHESTRA_SCOPE` in the worker's environment, e.g. `ORCHESTRA_SCOPE="tools/*:tests/test_x.py:hooks/*"`.
