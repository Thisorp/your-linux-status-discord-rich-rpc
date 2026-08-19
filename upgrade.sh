#!/usr/bin/env bash
set -euo pipefail
./install.sh
systemctl --user restart linux-discord-rpc
echo
echo "Upgrade complete."
