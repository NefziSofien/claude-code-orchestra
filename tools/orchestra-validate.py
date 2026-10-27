#!/usr/bin/env python3
"""Validate an orchestrate-skill state file (.orchestra/state.md).

Usage: orchestra-validate.py [path]   (default .orchestra/state.md)
Exit 0 if valid, 1 if invalid (one message per problem on stderr), 2 on IO error.
"""
import re
import sys

MAX_RUNNING = 4
HEADER = ["id", "goal", "worker", "vehicle/model", "status", "branch/worktree"]
SECTIONS = ["## Units", "## Decisions", "## Open questions", "## Next"]
RUNNING_RE = re.compile(r"\b(running|dispatched)\b", re.I)
EMPTY_BRANCH = {"", "-", "n/a", "none"}


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_done(status):
    return status.lower().startswith("done")


def validate(text):
    problems = []
    lines = text.splitlines()
    if len(lines) < 3:
        return ["file has fewer than 3 lines (need Task, Updated, Wave)"]
    if not re.match(r"# Task: \S", lines[0]):
        problems.append("line 1 must be '# Task: <one line>'")
    if not re.match(r"Updated: \d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?\S*)?\s*$", lines[1]):
        problems.append("line 2 must be 'Updated: <ISO date-time>'")
    if not re.match(r"Wave: \d+/\d+\s*$", lines[2]):
        problems.append("line 3 must be 'Wave: <n/m>'")

    idx = {}
    for name in SECTIONS:
        hits = [i for i, l in enumerate(lines) if l.strip() == name]
        if not hits:
            problems.append("missing section '%s'" % name)
        elif len(hits) > 1:
            problems.append("duplicate section '%s'" % name)
        else:
            idx[name] = hits[0]
    order = [idx[n] for n in SECTIONS if n in idx]
    if order != sorted(order):
        problems.append("sections out of order (expected %s)" % ", ".join(SECTIONS))

    def body(name):
        if name not in idx:
            return []
        end = min([j for j in idx.values() if j > idx[name]] + [len(lines)])
        return lines[idx[name] + 1:end]

    for name in SECTIONS[1:]:
        for l in body(name):
            if l.strip() and not l.lstrip().startswith("- "):
                problems.append("'%s': line is not a '- ' bullet: %s" % (name, l.strip()))

    rows = []
    table = [l for l in body("## Units") if l.strip()]
    if "## Units" in idx:
        if len(table) < 2 or not table[0].lstrip().startswith("|"):
            problems.append("'## Units' needs a table header and separator")
        else:
            if [c.lower() for c in split_row(table[0])] != HEADER:
                problems.append("Units header must be: | " + " | ".join(HEADER) + " |")
            if not re.match(r"^\|?[\s:|-]+\|?$", table[1]) or "-" not in table[1]:
                problems.append("Units table missing separator row")
            for l in table[2:]:
                if not l.lstrip().startswith("|"):
                    problems.append("Units: non-table line: %s" % l.strip())
                    continue
                cells = split_row(l)
                if len(cells) != len(HEADER):
                    problems.append("Units row has %d columns, expected %d: %s" % (len(cells), len(HEADER), l.strip()))
                    continue
                rows.append(cells)

    seen = set()
    for c in rows:
        if not c[0]:
            problems.append("unit with empty id: %s" % c[1])
        elif c[0] in seen:
            problems.append("duplicate unit id '%s'" % c[0])
        seen.add(c[0])

    running = [c[0] for c in rows if RUNNING_RE.search(c[4]) and not is_done(c[4])]
    if len(running) > MAX_RUNNING:
        problems.append("%d units running/dispatched at once (max %d): %s" % (len(running), MAX_RUNNING, ", ".join(running)))

    by_branch = {}
    for c in rows:
        b = c[5].strip("` ").lower()
        if is_done(c[4]) or b in EMPTY_BRANCH:
            continue
        by_branch.setdefault(b, []).append(c[0])
    for b, ids in by_branch.items():
        if len(ids) > 1:
            problems.append("units %s share branch/worktree '%s'" % (", ".join(ids), b))
    return problems


def main(argv):
    path = argv[1] if len(argv) > 1 else ".orchestra/state.md"
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("cannot read %s: %s" % (path, e), file=sys.stderr)
        return 2
    problems = validate(text)
    for p in problems:
        print("%s: %s" % (path, p), file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
