#!/usr/bin/env python3
"""SubagentStop hook: require the 5-field worker report, at most 10 lines.

Reads the hook JSON on stdin. On a bad report it prints a block decision
(decision=block + reason) so the subagent keeps running and fixes it.
"""
import json
import sys

FIELDS = ["STATUS", "CHANGED", "DECISIONS", "OPEN", "VERIFIED"]
MAX_LINES = 10


def check(report):
    lines = [l for l in report.splitlines() if l.strip() and not l.strip().startswith("```")]
    problems = []
    for f in FIELDS:
        if not any(l.lstrip().startswith(f + ":") for l in lines):
            problems.append("missing %s:" % f)
    if len(lines) > MAX_LINES:
        problems.append("%d lines, max %d" % (len(lines), MAX_LINES))
    return problems


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0  # not our input; never break the session
    if data.get("stop_hook_active"):
        return 0  # already asked once; avoid a loop
    report = data.get("last_assistant_message") or (data.get("tool_input") or {}).get("message") or ""
    problems = check(report)
    if problems:
        print(json.dumps({"decision": "block", "reason": "Worker report invalid (%s). Re-send exactly: STATUS / CHANGED / DECISIONS / OPEN / VERIFIED, max %d lines." % ("; ".join(problems), MAX_LINES)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
