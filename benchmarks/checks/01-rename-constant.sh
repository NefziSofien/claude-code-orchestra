#!/usr/bin/env bash
# Pass criteria for task 01. Usage: 01-rename-constant.sh <work-dir>
set -u
cd "${1:?usage: $0 <work-dir>}" || exit 2
if grep -rq --include='*.py' MAX_RETRIES .; then echo "FAIL: MAX_RETRIES still present"; exit 1; fi
defs="$(grep -rEh --include='*.py' '^RETRY_LIMIT[[:space:]]*=' . | wc -l)"
[ "$defs" -eq 1 ] || { echo "FAIL: RETRY_LIMIT defined $defs times, expected 1"; exit 1; }
grep -rq --include='*.py' 'import.*RETRY_LIMIT' . || { echo "FAIL: RETRY_LIMIT not imported anywhere"; exit 1; }
python3 -m unittest >/dev/null 2>&1 || { echo "FAIL: unittest"; exit 1; }
echo PASS
