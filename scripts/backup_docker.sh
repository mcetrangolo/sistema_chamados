#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
DOCKER="${DOCKER:-docker}"

mkdir -p "$BACKUP_DIR"

$DOCKER compose exec -T db pg_dump \
  -U "${POSTGRES_USER:-sistema_chamados}" \
  -d "${POSTGRES_DB:-sistema_chamados}" \
  -F c > "$BACKUP_DIR/postgres_$STAMP.dump"

$DOCKER compose exec -T web python manage.py backup_local

echo "Backup Docker concluido em $BACKUP_DIR."
