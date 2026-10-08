#!/usr/bin/env bash
# Every repository's tracker at its default branch, read over the wire, for the
# checks that judge the catalogue against all of them at once (OPS-R74, OPS-R78).
#
#   scripts/fetch_trackers.sh <directory>
#
# Clones each repository some version is satisfied in into <directory>/<repo>,
# checking out its tracker alone — status.toml or status/ — and the binary's
# Markdown page while its tracker is still in the milestone shape and is read
# through it. Then prints the arguments maturity.py takes, one to a line.
#
# Every failure stops the run, a repository keeping no status.toml included: each
# one a version is satisfied in keeps one (OPS-R74), and a tracker missing from the
# derivation would read as work nobody did. Call it so its exit status is seen —
# into a file, not through a process substitution, which discards it.
set -euo pipefail
dir="$1"
mkdir -p "$dir"
python3 scripts/status_check.py repos --spec . > "${dir}/repos.txt"
[[ -s "${dir}/repos.txt" ]] || { echo "::error::no repository is named by any manifest" >&2; exit 1; }
args=()
while read -r repo; do
  [[ -n "$repo" ]] || continue
  # The tracker alone, at the default branch: status.toml, or status/ where the
  # repository splits it by feature.
  git clone --quiet --depth 1 --filter=blob:none --sparse \
    "https://github.com/lemonfiber/${repo}.git" "${dir}/${repo}"
  git -C "${dir}/${repo}" sparse-checkout set --no-cone /status.toml /status/ /IMPLEMENTATION-STATUS.md
  if [[ ! -f "${dir}/${repo}/status.toml" && ! -d "${dir}/${repo}/status" ]]; then
    echo "::error::${repo} keeps no tracker at its default branch (OPS-R74)" >&2
    exit 1
  fi
  args+=(--tracker "${repo}=${dir}/${repo}")
done < "${dir}/repos.txt"
# The binary's page only while its tracker is still in the milestone shape.
if grep -q '^\[\[milestone\]\]' "${dir}/lemonfiber/status.toml" 2>/dev/null; then
  args+=(--legacy "${dir}/lemonfiber/IMPLEMENTATION-STATUS.md")
fi
printf '%s\n' "${args[@]}"
