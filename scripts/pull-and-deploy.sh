#!/usr/bin/env bash
# scripts/pull-and-deploy.sh - Pull latest code and restart Docker Compose stack.

set -euo pipefail

PROJECT_PATH="${1:-}"
BRANCH="${2:-}"
COMPOSE_FILE="${3:-}"

if [[ -z "$PROJECT_PATH" || -z "$BRANCH" || -z "$COMPOSE_FILE" ]]; then
  echo "Usage: $0 <project_path> <branch> <compose_file>" >&2
  exit 2
fi

log() {
  local now
  now="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "[$now] $*"
}

log "Starting deployment for path=$PROJECT_PATH branch=$BRANCH compose_file=$COMPOSE_FILE"

if [[ ! -d "$PROJECT_PATH" ]]; then
  log "Project path does not exist: $PROJECT_PATH"
  exit 1
fi

cd "$PROJECT_PATH"

log "Fetching latest changes"
git fetch --prune origin

log "Resetting repository to origin/$BRANCH"
git reset --hard "origin/$BRANCH"

log "Pulling Docker images"
docker compose -f "$COMPOSE_FILE" pull

log "Rebuilding and starting services"
docker compose -f "$COMPOSE_FILE" up -d --build

log "Pruning unused Docker images"
docker image prune -f

log "Deployment finished successfully"
