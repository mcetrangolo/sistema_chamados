#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
DOCKER="${DOCKER:-docker}"

set -a
if [ -f ".env" ]; then
  # shellcheck disable=SC1091
  . ./.env
fi
set +a

mkdir -p "$BACKUP_DIR"

$DOCKER compose -f docker-compose.yml -f docker-compose.postgresql.yml exec -T db pg_dump \
  -U "${POSTGRES_USER:-sistema_chamados}" \
  -d "${POSTGRES_DB:-sistema_chamados}" \
  -F c > "$BACKUP_DIR/postgres_$STAMP.dump"

echo "Backup PostgreSQL concluido em $BACKUP_DIR/postgres_$STAMP.dump."
