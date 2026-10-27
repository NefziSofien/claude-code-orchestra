#!/usr/bin/env python3
"""PreToolUse hook (Edit|Write): deny paths outside ORCHESTRA_SCOPE.

ORCHESTRA_SCOPE is a colon-separated list of globs, matched against the
absolute path and the path relative to the hook's cwd. Unset or empty: allow.
"""
import fnmatch
import json
import os
import sys


def allowed(file_path, cwd, scope):
    globs = [g for g in scope.split(":") if g]
    if not globs:
        return True
    cands = [file_path]
    try:
        cands.append(os.path.relpath(file_path, cwd))
    except ValueError:
        pass
    return any(fnmatch.fnmatch(c, g) or fnmatch.fnmatch(c, g.rstrip("/") + "/*")
               for c in cands for g in globs)


def main():
    scope = os.environ.get("ORCHESTRA_SCOPE", "")
    if not scope:
        return 0
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    path = (data.get("tool_input") or {}).get("file_path")
    if not path:
        return 0
    cwd = data.get("cwd") or os.getcwd()
    if allowed(os.path.normpath(path), cwd, scope):
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Outside worker SCOPE (%s): %s" % (scope, path)}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
