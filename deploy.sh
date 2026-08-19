#!/bin/bash
# Wow Chat — VPS-2 deploy script
# Runs on the server after GitHub Actions SSHs in.
set -e

DEPLOY_DIR="/opt/wow-chat"
COMPOSE="docker compose -f docker-compose.prod.yml"

echo "=== [Wow Chat Deploy] $(date) ==="

cd "$DEPLOY_DIR"

# Backup DB before any changes
BACKUP_DIR="$DEPLOY_DIR/backups"
mkdir -p "$BACKUP_DIR"
docker exec wowchat_postgres pg_dump -U "${POSTGRES_USER:-wowchat}" "${POSTGRES_DB:-wowchat}" \
  | gzip > "$BACKUP_DIR/pre_deploy_$(date +%Y%m%d_%H%M%S).sql.gz" 2>/dev/null || true
# Keep last 10 backups
ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null || true

echo ">>> Pulling latest code..."
git fetch origin
git reset --hard origin/main

echo ">>> Building images..."
$COMPOSE build --no-cache backend frontend

echo ">>> Starting / restarting containers..."
$COMPOSE up -d --remove-orphans

echo ">>> Waiting for backend to be ready..."
sleep 5

echo ">>> Running Django migrations..."
$COMPOSE exec -T backend python manage.py migrate --noinput

echo ">>> Collecting static files..."
$COMPOSE exec -T backend python manage.py collectstatic --noinput --clear 2>/dev/null || true

echo ">>> Container status:"
$COMPOSE ps

echo "=== Deploy complete: $(date) ==="
