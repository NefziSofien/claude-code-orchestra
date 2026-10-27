"""Merge lean-ctx/claude-permissions.json into a Claude Code settings.json.

Adds missing entries to permissions.allow / ask / deny without removing anything.
A tool listed in "ask" is removed from "allow" (so ctx_execute stops running unasked).
Backs the file up first. Usage: python3 merge_permissions.py <settings.json> [--dry-run]
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 1
    target = args[0]

    with open(os.path.join(HERE, "claude-permissions.json"), encoding="utf-8") as f:
        wanted = json.load(f)["permissions"]

    settings = {}
    if os.path.exists(target):
        with open(target, encoding="utf-8") as f:
            text = f.read().strip()
        settings = json.loads(text) if text else {}

    perms = settings.setdefault("permissions", {})
    changes = []
    for key in ("allow", "ask", "deny"):
        current = perms.setdefault(key, [])
        for entry in wanted.get(key, []):
            if entry not in current:
                current.append(entry)
                changes.append(f"+ {key}: {entry}")
    for entry in wanted.get("ask", []):
        if entry in perms["allow"]:
            perms["allow"].remove(entry)
            changes.append(f"- allow: {entry} (now ask)")

    if not changes:
        print(f"  ok       {target} already has the lean-ctx permissions")
        return 0
    for line in changes:
        print(f"  {line}")
    if dry:
        print(f"  [dry-run] would update {target}")
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    if os.path.exists(target):
        backup = f"{target}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(target, backup)
        print(f"  backup   {backup}")
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  updated  {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
