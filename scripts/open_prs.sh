#!/usr/bin/env bash
# Every open pull request in the named repositories, with its title, author,
# dates, branch, body and its commits' messages, as the one JSON object goals.py
# reads for claims (OPS-R77) and board.py for the pull requests it lists.
#
#   scripts/open_prs.sh <owner> <repo> [<repo> ...] > prs.json
#
# Drafts included: opening a draft pull request is how a claim is taken. A
# repository the forge will not answer for stops the run, since a claim missing
# from the report reads as nobody working on it.
set -euo pipefail
owner="$1"; shift
query='query($owner:String!,$name:String!){repository(owner:$owner,name:$name){pullRequests(states:OPEN,first:100){nodes{number url title isDraft createdAt updatedAt headRefName author{login __typename} body commits(last:100){nodes{commit{message}}}}}}}'
printf '{'
first=1
for repo in "$@"; do
  listed=$(gh api graphql -f query="$query" -F owner="$owner" -F name="$repo" \
    --jq '[.data.repository.pullRequests.nodes[] | {number, url, title, isDraft, createdAt, updatedAt, headRefName, author, body, commits: [.commits.nodes[].commit | {message}]}]')
  [[ "$first" = 1 ]] || printf ','
  first=0
  printf '"%s":%s' "$repo" "$listed"
done
printf '}\n'
