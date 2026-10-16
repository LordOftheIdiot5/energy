#!/usr/bin/env bash
# Starts the Fetch workflow from somewhere that actually keeps time.
#
# GitHub's scheduled workflows are best effort. On 2026-08-27 every firing for
# eighteen hours was dropped on the stockwatch repo while the workflow sat
# enabled and every previous run showed success. Nothing is broken in that
# state, so nothing reports it - the page just quietly goes stale.
#
# A systemd timer does not drop firings. The fetch itself still runs on GitHub,
# so any repository secrets stay where they are. Only the clock moves.
#
#   sudo bash deploy/install.sh     # one-time setup
#   bash deploy/trigger.sh          # or run it by hand
#
# The token lives in the stockwatch env file because one fine-grained token
# covers both repositories. The filename is historical; keeping one file means
# one thing to rotate rather than two copies of the same credential drifting
# apart.

set -euo pipefail

REPO="${REPO:-LordOftheIdiot5/energy}"
WORKFLOW="${WORKFLOW:-fetch.yml}"
REF="${REF:-main}"
ENV_FILE="${ENV_FILE:-/etc/stockwatch-trigger.env}"

if [[ -z "${GITHUB_TOKEN:-}" && -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is not set and $ENV_FILE has no value for it." >&2
  echo "Needs a token with Actions: read and write on $REPO." >&2
  exit 1
fi

api() {
  curl --silent --show-error --fail-with-body \
    --max-time 30 \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Skip when a run is already going. Two fetches racing would both try to commit
# to data/ and one would lose to a non-fast-forward push - which looks like a
# fetch failure rather than what it is.
running=$(api "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?status=in_progress&per_page=1" \
  | grep -c '"id"' || true)
if [[ "$running" -gt 0 ]]; then
  echo "a fetch is already running, skipping"
  exit 0
fi

echo "dispatching ${WORKFLOW} on ${REPO}@${REF}"

# Three attempts. A transient 5xx should not cost the hour's fetch, and not
# depending on best-effort delivery is the entire point of this script.
for attempt in 1 2 3; do
  if api -X POST \
      "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
      -d "{\"ref\":\"${REF}\"}" >/dev/null; then
    echo "dispatched"
    exit 0
  fi
  echo "attempt ${attempt} failed" >&2
  sleep $((attempt * 10))
done

echo "could not dispatch after 3 attempts" >&2
exit 1
