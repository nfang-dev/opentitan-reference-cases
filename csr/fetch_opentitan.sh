#!/usr/bin/env bash
# Fetch OpenTitan's hw/ and util/ at the revision recorded in csr/ips.json.
#
# Usage: csr/fetch_opentitan.sh <destination-directory>
set -euo pipefail
dest="$1"
here="$(cd "$(dirname "$0")" && pwd)"
revision="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["opentitan_revision"])' "$here/ips.json")"
git init -q "$dest"
git -C "$dest" remote add origin https://github.com/lowRISC/opentitan.git
git -C "$dest" sparse-checkout set hw util
git -C "$dest" fetch -q --depth 1 --filter=blob:none origin "$revision"
git -C "$dest" checkout -q FETCH_HEAD
echo "OpenTitan $(git -C "$dest" rev-parse HEAD) hw/ and util/ checked out in $dest"
