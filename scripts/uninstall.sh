#!/usr/bin/env bash
# scripts/uninstall.sh - Remove AutoPull service and installed files.

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "This script must run as root. Use: sudo bash scripts/uninstall.sh" >&2
  exit 1
fi

AUTOPULL_USER="autopull"
INSTALL_DIR="/usr/lib/autopull"
CONFIG_DIR="/etc/autopull"
LOG_DIR="/var/log/autopull"
SERVICE_PATH="/etc/systemd/system/autopull.service"

log() {
  local now
  now="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$now] $*"
}

log "Stopping and disabling autopull service"
systemctl disable --now autopull.service 2>/dev/null || true

if [[ -f "$SERVICE_PATH" ]]; then
  rm -f "$SERVICE_PATH"
fi

log "Removing installed files"
rm -rf "$INSTALL_DIR"

if [[ "${AUTOPULL_REMOVE_CONFIG:-0}" == "1" ]]; then
  rm -rf "$CONFIG_DIR"
else
  log "Keeping configuration directory at $CONFIG_DIR"
fi

if [[ "${AUTOPULL_REMOVE_LOGS:-0}" == "1" ]]; then
  rm -rf "$LOG_DIR"
else
  log "Keeping log directory at $LOG_DIR"
fi

if [[ "${AUTOPULL_REMOVE_USER:-0}" == "1" ]] && id "$AUTOPULL_USER" >/dev/null 2>&1; then
  log "Removing system user '$AUTOPULL_USER'"
  userdel -r "$AUTOPULL_USER" 2>/dev/null || userdel "$AUTOPULL_USER"
fi

systemctl daemon-reload
log "AutoPull uninstall completed"
