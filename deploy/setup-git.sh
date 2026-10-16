#!/usr/bin/env bash
# Local git settings this repo expects. Run once per clone.
#
# .gitattributes asks for the "ours" merge driver on data/energy.json, but a
# driver named in attributes has to exist in config or git silently falls
# back to a conflict. "true" is the whole implementation: succeed, changing
# nothing, which keeps the version already on the branch.
set -euo pipefail
git config merge.ours.driver true
echo "merge.ours.driver set; data/energy.json will stop conflicting"
