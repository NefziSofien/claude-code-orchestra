#!/usr/bin/env bash
# Pass criteria for task 02. Usage: 02-coupled-refactor.sh <work-dir>
set -u
cd "${1:?usage: $0 <work-dir>}" || exit 2
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
printf 'name = probe\n' > "$tmp"
python3 -c '
import dataclasses, sys
from orchid.config import parse_config
cfg = parse_config(sys.argv[1])
sys.exit(0 if dataclasses.is_dataclass(cfg) and not isinstance(cfg, type) else 1)
' "$tmp" 2>/dev/null || { echo "FAIL: parse_config does not return a dataclass instance"; exit 1; }
if grep -rnE --include='*.py' '\[["'"'"'][A-Za-z_]+["'"'"']\]' orchid tests; then
  echo "FAIL: string-key indexing remains"; exit 1
fi
python3 -m unittest >/dev/null 2>&1 || { echo "FAIL: unittest"; exit 1; }
echo PASS
