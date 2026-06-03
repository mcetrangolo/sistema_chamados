#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/sistema-chamados}"

cd "$PROJECT_DIR"

docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "Docker Compose nao foi encontrado."
    echo "Instale com: sudo apt install docker-compose docker-compose-plugin"
    exit 1
  fi
}

git pull --ff-only
docker_compose up -d --build
docker_compose exec -T web python manage.py check
docker_compose exec -T web python manage.py validar_producao

echo "Deploy concluido."
