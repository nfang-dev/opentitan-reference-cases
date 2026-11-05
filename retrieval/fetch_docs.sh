#!/usr/bin/env bash
# Fetch only the OpenTitan documentation files that the retrieval corpus is built from,
# at the revision recorded in retrieval/queries.json.
#
# Usage: retrieval/fetch_docs.sh <destination-directory>
set -euo pipefail

dest="$1"
here="$(cd "$(dirname "$0")" && pwd)"
revision="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["opentitan_revision"])' \
  "$here/queries.json")"

git init -q "$dest"
git -C "$dest" remote add origin https://github.com/lowRISC/opentitan.git
git -C "$dest" sparse-checkout set --no-cone \
  '/hw/ip/**/*.md' \
  '/hw/ip_templates/**/*.md' \
  '/hw/ip_templates/**/*.md.tpl' \
  '/hw/top_*/ip_autogen/**/*.md'
git -C "$dest" fetch -q --depth 1 --filter=blob:none origin "$revision"
git -C "$dest" checkout -q FETCH_HEAD
echo "OpenTitan $(git -C "$dest" rev-parse HEAD) documentation checked out in $dest"
