#!/usr/bin/env bash
# Fetch OpenTitan's hardware sources (hw/) at the revision recorded in case 001.
#
# Usage: behavior/fetch_hw.sh <destination-directory>
set -euo pipefail

dest="$1"
here="$(cd "$(dirname "$0")" && pwd)"
revision="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["opentitan_revision"])' \
  "$here/../cases/001-pinmux-mio-outsel-reset/case.json")"

git init -q "$dest"
git -C "$dest" remote add origin https://github.com/lowRISC/opentitan.git
git -C "$dest" sparse-checkout set hw
git -C "$dest" fetch -q --depth 1 --filter=blob:none origin "$revision"
git -C "$dest" checkout -q FETCH_HEAD
echo "OpenTitan $(git -C "$dest" rev-parse HEAD) hardware sources checked out in $dest"
