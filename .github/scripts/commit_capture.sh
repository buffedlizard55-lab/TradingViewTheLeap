#!/usr/bin/env bash
# Stage, commit and push capture output to the branch the workflow is running on.
#
# Used by capture-intraday.yml after EACH interval so partial progress survives a run
# that later hits the vendor's rate limiter: a 20-minute capture that stores two of three
# intervals must not lose the two.
#
# Usage: commit_capture.sh "<commit message>" <path> [<path> ...]

set -uo pipefail

message="$1"
shift

git config user.name "github-actions[capture]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

for path in "$@"; do
  if [ -e "$path" ]; then
    git add "$path"
  fi
done

if git diff --cached --quiet; then
  echo "::notice::nothing to commit for: $message"
  exit 0
fi

git commit -m "$message"
if git push origin "HEAD:${GITHUB_REF_NAME}"; then
  echo "::notice::committed to ${GITHUB_REF_NAME} at $(git rev-parse --short HEAD): $message"
else
  echo "::warning::push failed for: $message (a later step will retry)"
fi
exit 0
