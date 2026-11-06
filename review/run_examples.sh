#!/usr/bin/env bash
# Write the example reports in review/examples/ (or the directory given) from a checkout of
# OpenTitan's hw/ and the earlier revision's documentation.
#
# Usage: review/run_examples.sh <opentitan-hw> <earlier-docs> [<out-dir>]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${3:-$here/examples}"
mkdir -p "$out"
while IFS=$'\t' read -r name question; do
  python3 "$here/review.py" ask "$question" --opentitan "$1" --earlier "$2" --out "$out/$name.md"
done < "$here/examples/questions.txt"
