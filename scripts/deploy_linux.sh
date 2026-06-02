#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/sistema-chamados}"
DOCKER="${DOCKER:-docker}"

cd "$PROJECT_DIR"

git pull --ff-only
$DOCKER compose up -d --build
$DOCKER compose exec -T web python manage.py check
$DOCKER compose exec -T web python manage.py validar_producao

echo "Deploy concluido."
