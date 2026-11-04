#!/usr/bin/env bash
# Fetch only the OpenTitan files that the given cases refer to, at the revision they record.
#
# Usage: tools/fetch_opentitan.sh <destination-directory> [case.json ...]
# Without case files, all cases under cases/ are used. All cases must record the same
# OpenTitan revision.
set -euo pipefail

dest="$1"
shift
if [ "$#" -eq 0 ]; then
  set -- cases/*/case.json
fi

read -r revision paths < <(python3 - "$@" <<'EOF'
import json, sys
revisions, dirs = set(), set()
for path in sys.argv[1:]:
    case = json.load(open(path, encoding="utf-8"))
    revisions.add(case["opentitan_revision"])
    for item in case["requirements"] + case["design"]:
        dirs.add(item["file"].rsplit("/", 1)[0])
if len(revisions) != 1:
    sys.exit(f"cases record different OpenTitan revisions: {sorted(revisions)}")
print(revisions.pop(), " ".join(sorted(dirs)))
EOF
)

git init -q "$dest"
git -C "$dest" remote add origin https://github.com/lowRISC/opentitan.git
git -C "$dest" sparse-checkout set $paths
git -C "$dest" fetch -q --depth 1 --filter=blob:none origin "$revision"
git -C "$dest" checkout -q FETCH_HEAD
echo "OpenTitan $(git -C "$dest" rev-parse HEAD) checked out in $dest"
echo "paths: $paths"
