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

# Never commit data/intraday_index.json unless it records at least one captured series. The
# rest of the repository treats the presence of that file as "captures exist" (the verifier
# applies its strict intraday checks, the derive workflow runs the study, the site renders the
# stock divisions), so an index holding nothing but failures would turn a vendor outage into a
# red build. A zero-capture attempt is recorded in data/intraday_capture_report.json instead,
# which the diagnostics step commits on every run.
skip_index=0
for path in "$@"; do
  if [ "$path" = "data/intraday_index.json" ] && [ -f "$path" ]; then
    captured=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['_meta'].get('captured_count',0))" "$path" 2>/dev/null || echo 0)
    if [ "${captured:-0}" -le 0 ]; then
      skip_index=1
      echo "::warning::data/intraday_index.json records 0 captured series - not committing it (see data/intraday_capture_report.json)"
    fi
  fi
done

git config user.name "github-actions[capture]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

for path in "$@"; do
  if [ "$skip_index" = "1" ] && [ "$path" = "data/intraday_index.json" ]; then
    continue
  fi
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
  exit 0
fi

# A second capture run may have committed while this one was fetching. Rebase onto the
# remote branch and retry once: captures are additive per series, so taking the remote
# first and re-applying local changes keeps every stored file that was already verified.
echo "::notice::push rejected - rebasing onto origin/${GITHUB_REF_NAME} and retrying"
# -X theirs during a rebase keeps OUR (newest) capture for any file both sides touched: a
# conflicting data/intraday_index.json is resolved in favour of the run that just fetched it,
# and a later --only-failed run tops up anything the other run had and this one did not.
if git pull --rebase --autostash -X theirs origin "${GITHUB_REF_NAME}" && git push origin "HEAD:${GITHUB_REF_NAME}"; then
  echo "::notice::committed to ${GITHUB_REF_NAME} at $(git rev-parse --short HEAD) after rebase: $message"
else
  echo "::warning::push failed for: $message (a later step will retry)"
fi
exit 0
