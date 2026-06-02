#!/usr/bin/env bash
set -euo pipefail

DOCKER="${DOCKER:-docker}"

$DOCKER compose exec -T web python manage.py backup_local

echo "Backup SQLite/media concluido. Veja os arquivos em Configuracoes > Backup e restauracao."
