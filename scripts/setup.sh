#!/usr/bin/env bash
# scripts/setup.sh - Install and configure AutoPull on Ubuntu/Debian VPS.

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "This installer must run as root. Use: sudo bash scripts/setup.sh" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/usr/lib/autopull"
CONFIG_DIR="/etc/autopull"
LOG_DIR="/var/log/autopull"
SERVICE_PATH="/etc/systemd/system/autopull.service"
AUTOPULL_USER="autopull"

log() {
  local now
  now="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$now] $*"
}

install_dependencies() {
  log "Installing system dependencies"
  apt-get update

  local packages=(git docker.io docker-compose-plugin python3 python3-venv)
  if [[ "${AUTOPULL_SKIP_NGINX:-0}" != "1" ]]; then
    packages+=(nginx)
  fi

  DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
}

create_user() {
  if id "$AUTOPULL_USER" >/dev/null 2>&1; then
    log "User '$AUTOPULL_USER' already exists"
  else
    log "Creating system user '$AUTOPULL_USER'"
    useradd --system --create-home --home-dir "/home/$AUTOPULL_USER" \
      --shell /usr/sbin/nologin "$AUTOPULL_USER"
  fi

  usermod -aG docker "$AUTOPULL_USER"
}

create_directories() {
  log "Creating application directories"
  install -d -m 0755 "$INSTALL_DIR"
  install -d -m 0750 "$CONFIG_DIR"
  install -d -m 0755 "$LOG_DIR"

  chown "$AUTOPULL_USER:$AUTOPULL_USER" "$LOG_DIR"
}

copy_project_files() {
  log "Copying AutoPull source files"
  rsync -a --delete "$ROOT_DIR/autopull/" "$INSTALL_DIR/autopull/"
  rsync -a --delete "$ROOT_DIR/scripts/" "$INSTALL_DIR/scripts/"

  chmod +x "$INSTALL_DIR/scripts/pull-and-deploy.sh"
  chmod +x "$INSTALL_DIR/scripts/setup-ssh-deploy-key.sh"
  chmod +x "$INSTALL_DIR/scripts/uninstall.sh"

  if [[ -f "$ROOT_DIR/config/projects.example.json" ]]; then
    install -m 0640 -o root -g "$AUTOPULL_USER" \
      "$ROOT_DIR/config/projects.example.json" "$CONFIG_DIR/projects.example.json"
  fi

  if [[ ! -f "$CONFIG_DIR/projects.json" ]]; then
    log "Initializing $CONFIG_DIR/projects.json from example"
    install -m 0640 -o root -g "$AUTOPULL_USER" \
      "$ROOT_DIR/config/projects.example.json" "$CONFIG_DIR/projects.json"
  fi
}

install_systemd_service() {
  log "Installing systemd service"
  install -m 0644 "$ROOT_DIR/systemd/autopull.service" "$SERVICE_PATH"
  systemctl daemon-reload
  systemctl enable --now autopull.service
}

install_nginx_example() {
  if [[ -f "$ROOT_DIR/nginx/autopull.conf" ]]; then
    log "Installing Nginx example config"
    install -m 0644 "$ROOT_DIR/nginx/autopull.conf" \
      /etc/nginx/sites-available/autopull.conf

    if [[ ! -L /etc/nginx/sites-enabled/autopull.conf ]]; then
      ln -s /etc/nginx/sites-available/autopull.conf \
        /etc/nginx/sites-enabled/autopull.conf
    fi

    if nginx -t; then
      systemctl reload nginx || true
    else
      log "Nginx config test failed; leaving service unchanged"
    fi
  fi
}

print_post_install() {
  cat <<'EOF'

AutoPull installation completed.

Next steps:
1. Edit /etc/autopull/projects.json and set your project paths and branch names.
2. Export webhook secret environment variables for the autopull service.
3. Run: sudo /usr/lib/autopull/scripts/setup-ssh-deploy-key.sh
4. Add the generated deploy key to each GitHub repository as a read-only Deploy Key.
5. Configure GitHub webhooks to POST to https://your-domain/<project-name>
6. Check service status: sudo systemctl status autopull
7. Follow logs: sudo journalctl -u autopull -f

EOF
}

main() {
  install_dependencies
  create_user
  create_directories
  copy_project_files
  install_systemd_service
  install_nginx_example
  print_post_install
}

main "$@"
