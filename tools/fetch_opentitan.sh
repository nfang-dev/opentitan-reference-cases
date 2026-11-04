#!/usr/bin/env bash
# Fetch only the OpenTitan files a case refers to, at the revision the case records.
#
# Usage: tools/fetch_opentitan.sh <case.json> <destination-directory>
set -euo pipefail

case_file="$1"
dest="$2"

read -r revision paths < <(python3 - "$case_file" <<'EOF'
import json, sys
case = json.load(open(sys.argv[1], encoding="utf-8"))
items = case["requirements"] + case["design"]
dirs = sorted({item["file"].rsplit("/", 1)[0] for item in items})
print(case["opentitan_revision"], " ".join(dirs))
EOF
)

git init -q "$dest"
git -C "$dest" remote add origin https://github.com/lowRISC/opentitan.git
git -C "$dest" sparse-checkout set $paths
git -C "$dest" fetch -q --depth 1 --filter=blob:none origin "$revision"
git -C "$dest" checkout -q FETCH_HEAD
echo "OpenTitan $(git -C "$dest" rev-parse HEAD) checked out in $dest (paths: $paths)"
