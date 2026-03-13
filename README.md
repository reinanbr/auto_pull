# AutoPull

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/autopull/autopull/actions/workflows/ci.yml/badge.svg)](https://github.com/autopull/autopull/actions/workflows/ci.yml)

Self-hosted GitHub webhook server for automatic Docker deployments.

## Overview

AutoPull is a lightweight deployment listener designed for VPS-hosted applications managed with Docker Compose. On each GitHub push, AutoPull validates the webhook signature, resets the repository to the target branch, and rebuilds or restarts containers. It supports multiple projects on one host and centralizes deployment logs for auditability. The service is intended for Ubuntu and Debian servers where predictable, self-hosted deployment automation is preferred over external CI/CD runners.

## How It Works

```text
Developer pushes to GitHub
  -> GitHub POST webhook to https://your-domain/<project-name>
    -> Nginx forwards request to AutoPull (127.0.0.1:9000)
      -> AutoPull verifies X-Hub-Signature-256 (HMAC-SHA256)
        -> Runs pull-and-deploy.sh with project config
          -> git fetch + git reset --hard origin/<branch>
          -> docker compose pull && docker compose up -d --build
          -> Logs to /var/log/autopull/<project>.log
```

## Requirements

- Ubuntu 20.04+ or Debian 11+ VPS
- Docker Engine and Docker Compose plugin
- Python 3.8+
- Nginx (optional, recommended for TLS termination)

## Installation

1. Clone repository:
   ```bash
   git clone https://github.com/autopull/autopull.git
   cd autopull
   ```
2. Run installer:
   ```bash
   sudo bash scripts/setup.sh
   ```
3. Configure projects:
   ```bash
   sudo cp /etc/autopull/projects.example.json /etc/autopull/projects.json
   sudo nano /etc/autopull/projects.json
   ```
4. Start or restart service:
   ```bash
   sudo systemctl restart autopull
   sudo systemctl enable autopull
   ```

## Credentials Setup

### 1) SSH Deploy Key

Generate key:

```bash
sudo bash /usr/lib/autopull/scripts/setup-ssh-deploy-key.sh
```

Add the printed public key in each repository:

- GitHub repository -> Settings -> Deploy keys -> Add deploy key
- Paste key and keep write access disabled

### 2) Webhook Secret

Generate strong random secret:

```bash
openssl rand -hex 32
```

Use that value in two places:

- GitHub webhook "Secret" field
- Environment variable referenced in `/etc/autopull/projects.json`

Example:

```bash
sudo tee /etc/default/autopull >/dev/null <<'EOF'
MY_WEBSITE_WEBHOOK_SECRET=replace_with_real_secret
EOF
```

Then include `EnvironmentFile=-/etc/default/autopull` in your systemd service if desired.

### 3) Docker Login for Private Registries (Optional)

```bash
sudo -u autopull docker login
```

### 4) .env File for Application Secrets

Store app-specific runtime secrets in each project directory `.env` file and never commit them to Git.

### 5) Personal SSH Key for VPS Access

Use your personal SSH key for administrative login to the VPS and disable password login in SSH daemon settings when possible.

## GitHub Webhook Configuration

In GitHub repository settings:

1. Open Settings -> Webhooks -> Add webhook
2. Payload URL: `https://your-domain/<project-name>`
3. Content type: `application/json`
4. Secret: same value as project secret
5. Events: select `Just the push event`
6. Enable webhook and save

## Project Configuration

Main config file: `/etc/autopull/projects.json`

Supported fields per project:

- `path`: absolute repository path on VPS
- `secret`: webhook secret string or `${ENV_VAR}` reference
- `branch`: Git branch to deploy (default `main`)
- `compose_file`: Compose file path relative to `path` (default `docker-compose.yml`)

Example:

```json
{
  "my-website": {
    "path": "/var/www/my-website",
    "secret": "${MY_WEBSITE_WEBHOOK_SECRET}",
    "branch": "main",
    "compose_file": "docker-compose.yml"
  },
  "my-api": {
    "path": "/var/www/my-api",
    "secret": "${MY_API_WEBHOOK_SECRET}",
    "branch": "production",
    "compose_file": "docker-compose.prod.yml"
  },
  "my-worker": {
    "path": "/var/www/my-worker",
    "secret": "${MY_WORKER_WEBHOOK_SECRET}",
    "branch": "main",
    "compose_file": "docker-compose.yml"
  }
}
```

## Nginx Setup

Install config:

```bash
sudo cp nginx/autopull.conf /etc/nginx/sites-available/autopull.conf
sudo ln -s /etc/nginx/sites-available/autopull.conf /etc/nginx/sites-enabled/autopull.conf
sudo nginx -t && sudo systemctl reload nginx
```

Enable HTTPS with Certbot:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain
```

## Logs

AutoPull logs are available in two locations:

- Global log: `/var/log/autopull/autopull.log`
- Per-project log: `/var/log/autopull/<project>.log`

Follow logs live:

```bash
sudo journalctl -u autopull -f
sudo tail -f /var/log/autopull/autopull.log
```

## Multiple Projects

You can deploy multiple repositories from one VPS by adding additional keys in `/etc/autopull/projects.json`. Each project has its own route (`/<project-name>`) and its own deployment log file.

## Security Considerations

- Rotate webhook secrets periodically and after team membership changes.
- Keep deploy keys read-only.
- Never commit `.env` files, secrets, or private keys.
- Restrict inbound traffic with UFW or cloud firewall to ports 80/443.
- Run AutoPull behind Nginx TLS termination.
- Review logs regularly for repeated invalid signature attempts.

## Debian Package

Build package:

```bash
make deb
```

Install package:

```bash
sudo dpkg -i ../autopull_*.deb
sudo apt-get install -f -y
```

## Contributing

1. Fork the repository.
2. Create a feature branch from `main`.
3. Run `make lint` and `make test`.
4. Submit a pull request with clear description and test evidence.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
