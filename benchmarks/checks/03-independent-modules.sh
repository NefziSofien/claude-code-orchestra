#!/usr/bin/env bash
# Pass criteria for task 03. Usage: 03-independent-modules.sh <work-dir>
set -u
cd "${1:?usage: $0 <work-dir>}" || exit 2
for m in slugify bytesize dateparse; do
  [ -f "utils/$m.py" ] || { echo "FAIL: utils/$m.py missing"; exit 1; }
  [ -f "tests/test_$m.py" ] || { echo "FAIL: tests/test_$m.py missing"; exit 1; }
done
python3 -c '
from utils.slugify import slugify
from utils.bytesize import human_bytes
from utils.dateparse import parse_duration
assert slugify("Héllo World") == "hello-world"
assert human_bytes(1536) == "1.5 KiB"
assert parse_duration("1h30m") == 5400
' 2>/dev/null || { echo "FAIL: prompt examples do not hold"; exit 1; }
python3 -m unittest discover >/dev/null 2>&1 || { echo "FAIL: unittest discover"; exit 1; }
echo PASS
