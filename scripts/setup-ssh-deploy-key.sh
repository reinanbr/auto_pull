#!/usr/bin/env bash
# scripts/setup-ssh-deploy-key.sh - Generate deploy key for GitHub repository access.

set -euo pipefail

AUTOPULL_USER="autopull"
AUTOPULL_HOME="/home/$AUTOPULL_USER"
SSH_DIR="$AUTOPULL_HOME/.ssh"
KEY_PATH="$SSH_DIR/deploy_key"
CONFIG_PATH="$SSH_DIR/config"

if [[ "$EUID" -ne 0 ]]; then
  echo "This script must run as root. Use: sudo bash scripts/setup-ssh-deploy-key.sh" >&2
  exit 1
fi

if ! id "$AUTOPULL_USER" >/dev/null 2>&1; then
  echo "User '$AUTOPULL_USER' does not exist. Run setup.sh first." >&2
  exit 1
fi

install -d -m 0700 -o "$AUTOPULL_USER" -g "$AUTOPULL_USER" "$SSH_DIR"

if [[ ! -f "$KEY_PATH" ]]; then
  sudo -u "$AUTOPULL_USER" ssh-keygen -t ed25519 -N "" \
    -C "autopull-deploy-key@$(hostname)" -f "$KEY_PATH"
else
  echo "Deploy key already exists at $KEY_PATH"
fi

cat > "$CONFIG_PATH" <<'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/deploy_key
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
EOF

chown "$AUTOPULL_USER:$AUTOPULL_USER" "$CONFIG_PATH"
chmod 0600 "$CONFIG_PATH"

echo
echo "Public deploy key (add this in GitHub repository settings > Deploy keys):"
echo "-----------------------------------------------------------------------"
cat "$KEY_PATH.pub"
echo "-----------------------------------------------------------------------"
echo
echo "Instructions:"
echo "1. Open GitHub repository > Settings > Deploy keys > Add deploy key"
echo "2. Paste the public key shown above"
echo "3. Keep 'Allow write access' disabled (read-only)"
