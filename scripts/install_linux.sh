#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-${REPO_URL:-}}"
PROJECT_DIR="${PROJECT_DIR:-/opt/sistema-chamados}"
APP_HOSTS="${APP_HOSTS:-}"
INSTALL_USER="${SUDO_USER:-${USER:-$(id -un)}}"

if [ -z "$REPO_URL" ] && [ ! -d ".git" ]; then
  echo "Informe a URL do repositorio GitHub."
  echo "Exemplo: REPO_URL=https://github.com/usuario/sistema-chamados.git bash scripts/install_linux.sh"
  exit 1
fi

if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

echo "Instalando pacotes base..."
$SUDO apt-get update
$SUDO apt-get install -y ca-certificates curl git openssl

if ! command -v docker >/dev/null 2>&1; then
  $SUDO apt-get install -y docker.io
fi
$SUDO systemctl enable --now docker

install_compose() {
  if $SUDO docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then
    return 0
  fi

  echo "Instalando Docker Compose..."
  $SUDO apt-get install -y docker-compose-plugin \
    || $SUDO apt-get install -y docker-compose-v2 \
    || $SUDO apt-get install -y docker-compose
}

docker_compose() {
  if $SUDO docker compose version >/dev/null 2>&1; then
    $SUDO docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    $SUDO docker-compose "$@"
  else
    echo "Docker Compose nao foi encontrado."
    echo "Tente instalar manualmente: sudo apt install docker-compose docker-compose-plugin"
    exit 1
  fi
}

install_compose

if [ ! -d "$PROJECT_DIR/.git" ]; then
  echo "Preparando diretorio $PROJECT_DIR..."
  $SUDO mkdir -p "$PROJECT_DIR"
  $SUDO chown -R "$INSTALL_USER:$INSTALL_USER" "$PROJECT_DIR"
  if [ -n "$REPO_URL" ]; then
    git clone "$REPO_URL" "$PROJECT_DIR"
  else
    echo "Projeto ja esta local. Copie-o para $PROJECT_DIR ou informe REPO_URL."
    exit 1
  fi
fi

cd "$PROJECT_DIR"

SERVER_IP="$(hostname -I | awk '{print $1}')"
SERVER_NAME="$(hostname -f 2>/dev/null || hostname)"
if [ -z "$APP_HOSTS" ]; then
  APP_HOSTS="localhost,127.0.0.1,$SERVER_IP,$SERVER_NAME"
fi

if [ ! -f ".env" ]; then
  echo "Criando .env inicial para SQLite..."
  SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n')"
  INVENTARIO_AGENT_TOKEN="$(openssl rand -hex 32)"
  cat > .env <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$APP_HOSTS
CSRF_TRUSTED_ORIGINS=http://$SERVER_IP,http://$SERVER_NAME
SECURE_PROXY_SSL_HEADER=False
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

SQLITE_NAME=data/db.sqlite3
INVENTARIO_AGENT_TOKEN=$INVENTARIO_AGENT_TOKEN

GOVERNANCA_DOCUMENT_ROOT=media/governanca_documentos

AD_SERVER=
AD_USER=
AD_PASSWORD=
AD_BASE_DN=
AD_COMPUTERS_FILTER=(objectClass=computer)
AD_USERS_FILTER=(objectClass=user)

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_TIMEOUT=15
DEFAULT_FROM_EMAIL=helpdesk@$SERVER_NAME

LOG_LEVEL=INFO
SCHEDULER_INTERVAL_SECONDS=86400
EOF
  chmod 600 .env
else
  echo ".env ja existe. Mantendo configuracao atual."
fi

echo "Subindo containers..."
docker_compose up -d --build

echo "Carregando dados iniciais..."
docker_compose exec -T web python manage.py seed_chamados

echo "Validando instalacao..."
docker_compose exec -T web python manage.py check
docker_compose exec -T web python manage.py validar_producao || true

echo ""
echo "Instalacao concluida."
echo "Banco de dados: SQLite em volume Docker (data/db.sqlite3)."
echo "Acesse: http://$SERVER_IP/"
echo ""
echo "Comandos uteis:"
echo "  cd $PROJECT_DIR"
echo "  docker compose logs -f web"
echo "  bash scripts/deploy_linux.sh"
echo "  bash scripts/backup_docker.sh"
