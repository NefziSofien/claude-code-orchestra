#!/usr/bin/env bash
# Pass criteria for task 04. Usage: 04-independent-audits.sh <work-dir>
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${1:?usage: $0 <work-dir>}" || exit 2
for p in auth billing search notifications; do
  [ -f "docs/$p.md" ] || { echo "FAIL: docs/$p.md missing"; exit 1; }
  ls tests/test_*"$p"*.py >/dev/null 2>&1 || { echo "FAIL: no test file for $p"; exit 1; }
  python3 -c '
import ast, pathlib, sys
pkg = sys.argv[1]
doc = pathlib.Path("docs/%s.md" % pkg).read_text()
missing = []
for src in pathlib.Path("packages", pkg).glob("*.py"):
    for node in ast.parse(src.read_text()).body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_") and node.name not in doc:
            missing.append(node.name)
if missing:
    print("missing from docs/%s.md: %s" % (pkg, ", ".join(missing)))
    sys.exit(1)
' "$p" || { echo "FAIL: docs/$p.md incomplete"; exit 1; }
done
# Files under packages/ must be unchanged (bytecode caches ignored).
(LC_ALL=C find packages -name '*.py' | LC_ALL=C sort | xargs sha256sum) | cmp -s - "$HERE/04-independent-audits.sha256" \
  || { echo "FAIL: files under packages/ changed"; exit 1; }
python3 -m unittest discover >/dev/null 2>&1 || { echo "FAIL: unittest discover"; exit 1; }
echo PASS
