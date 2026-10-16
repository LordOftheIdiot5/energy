#!/usr/bin/env bash
# One-time setup on the VPS. Re-runnable.
set -euo pipefail

DEST=/opt/energy-trigger
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -d -m 755 "$DEST"
install -m 755 "$HERE/trigger.sh" "$DEST/trigger.sh"
install -m 644 "$HERE/energy-fetch.service" /etc/systemd/system/
install -m 644 "$HERE/energy-fetch.timer"   /etc/systemd/system/

if [[ ! -f /etc/stockwatch-trigger.env ]]; then
  echo "WARNING: /etc/stockwatch-trigger.env is missing." >&2
  echo "It holds GITHUB_TOKEN, shared with the stockwatch trigger." >&2
fi

systemctl daemon-reload
systemctl enable --now energy-fetch.timer
systemctl list-timers energy-fetch.timer --no-pager
