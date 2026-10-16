#!/usr/bin/env bash
# One-time setup on the VPS. Re-runnable.
#
#   git clone https://github.com/LordOftheIdiot5/energy /opt/energy
#   sudo bash /opt/energy/deploy/install.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chmod +x "$HERE/trigger.sh"
install -m 644 "$HERE/energy-fetch.service" /etc/systemd/system/
install -m 644 "$HERE/energy-fetch.timer"   /etc/systemd/system/

if [[ ! -f /etc/stockwatch-trigger.env ]]; then
  echo "WARNING: /etc/stockwatch-trigger.env is missing." >&2
  echo "It holds GITHUB_TOKEN, shared with the stockwatch trigger." >&2
fi

systemctl daemon-reload
systemctl enable --now energy-fetch.timer
systemctl list-timers energy-fetch.timer --no-pager
