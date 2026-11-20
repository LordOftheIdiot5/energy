#!/usr/bin/env bash
# Only run in an isolated GitHub Actions checkout. Never force-push or pick a side in an archive conflict.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true ]]; then echo "Requires isolated CI checkout"; exit 2; fi
git config user.name "energy"
git config user.email "actions@github.com"
validate() {
  python tests/test_payload.py
  python -m unittest discover -s tests -p test_energy_geography.py
  python -m unittest discover -s tests -p test_asset_reference.py
  python scripts/build_public_site.py --check-only
}
commit_data() {
  python scripts/build_public_site.py --check-only
  git add -- data/
  git diff --staged --quiet || git commit -m "fetch: $(date -u '+%Y-%m-%d %H:%M UTC')"
}
commit_data
recollected=0
for attempt in 1 2 3; do
  git fetch origin main
  if ! git rebase origin/main; then
    git rebase --abort
    if [[ "$recollected" == 1 ]]; then
      echo "::error::Second concurrent archive conflict; no overwrite attempted."
      exit 1
    fi
    # Keep candidate locally for diagnostics, restart from the latest remote so all remote history remains.
    git branch "fetch-conflicted-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}" HEAD
    git reset --hard origin/main
    echo "::notice::Concurrent source writer detected; recollecting once from latest main."
    python scripts/fetch.py
    validate
    commit_data
    recollected=1
  fi
  python scripts/build_public_site.py --check-only
  if git push origin HEAD:main; then exit 0; fi
  sleep 5
done
echo "::error::Unable to publish after three safe attempts."
exit 1
