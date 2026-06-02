#!/usr/bin/env bash
set -euo pipefail

DUMP_FILE="${1:-}"
DOCKER="${DOCKER:-docker}"

if [ -z "$DUMP_FILE" ]; then
  echo "Informe o arquivo .dump gerado pelo backup."
  echo "Exemplo: bash scripts/restore_docker.sh backups/postgres_20260601_230000.dump"
  exit 1
fi

if [ ! -f "$DUMP_FILE" ]; then
  echo "Arquivo nao encontrado: $DUMP_FILE"
  exit 1
fi

set -a
if [ -f ".env" ]; then
  # shellcheck disable=SC1091
  . ./.env
fi
set +a

POSTGRES_DB="${POSTGRES_DB:-sistema_chamados}"
POSTGRES_USER="${POSTGRES_USER:-sistema_chamados}"

echo "ATENCAO: esta operacao vai substituir os dados atuais do banco $POSTGRES_DB."
read -r -p "Digite RESTAURAR para continuar: " CONFIRMACAO
if [ "$CONFIRMACAO" != "RESTAURAR" ]; then
  echo "Restore cancelado."
  exit 1
fi

echo "Parando servicos da aplicacao..."
$DOCKER compose -f docker-compose.yml -f docker-compose.postgresql.yml stop web scheduler

echo "Restaurando banco PostgreSQL..."
cat "$DUMP_FILE" | $DOCKER compose -f docker-compose.yml -f docker-compose.postgresql.yml exec -T db pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner

echo "Subindo servicos..."
$DOCKER compose -f docker-compose.yml -f docker-compose.postgresql.yml up -d

echo "Validando aplicacao..."
$DOCKER compose -f docker-compose.yml -f docker-compose.postgresql.yml exec -T web python manage.py check

echo "Restore concluido."
