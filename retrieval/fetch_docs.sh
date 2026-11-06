#!/usr/bin/env bash
# Fetch only the OpenTitan documentation files that the retrieval corpus is built from.
#
# Usage: retrieval/fetch_docs.sh <destination-directory> [current|earlier]
#   current (default): the revision recorded in retrieval/queries.json
#   earlier: the earlier revision recorded in retrieval/queries_changed.json
set -euo pipefail

dest="$1"
which="${2:-current}"
here="$(cd "$(dirname "$0")" && pwd)"
case "$which" in
  current) file="$here/queries.json"; key=opentitan_revision ;;
  earlier) file="$here/queries_changed.json"; key=earlier_revision ;;
  *) echo "unknown revision choice: $which (use current or earlier)" >&2; exit 2 ;;
esac
revision="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$file" "$key")"

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
