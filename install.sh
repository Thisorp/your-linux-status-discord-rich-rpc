#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${HOME}/.local/share/linux-discord-rpc"
SYSTEMD_DIR="${HOME}/.config/systemd/user"

mkdir -p "${APP_DIR}" "${SYSTEMD_DIR}"

cp discord_rpc.py requirements.txt "${APP_DIR}/"
chmod 700 "${APP_DIR}/discord_rpc.py"

# Never overwrite a working user config during reinstall/upgrade.
if [[ ! -f "${APP_DIR}/config.json" ]]; then
    cp config.json "${APP_DIR}/config.json"
    echo "Created ${APP_DIR}/config.json"
else
    echo "Keeping existing ${APP_DIR}/config.json"
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required."
    exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "Python venv support is missing."
    echo "Install it with: sudo apt install python3-venv"
    exit 1
fi

if [[ ! -x "${APP_DIR}/.venv/bin/python" ]]; then
    python3 -m venv "${APP_DIR}/.venv"
fi

"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

cp discord-rpc.service "${SYSTEMD_DIR}/linux-discord-rpc.service"

systemctl --user daemon-reload
systemctl --user enable --now linux-discord-rpc.service

echo
echo "Installed/upgraded."
echo "Config: ${APP_DIR}/config.json"
echo "Restart: systemctl --user restart linux-discord-rpc"
echo "Logs:    journalctl --user -u linux-discord-rpc -f"
