# Instalacao e Primeiro Acesso

## Instalacao em Debian/Ubuntu

Use este caminho em uma maquina Debian/Ubuntu limpa.

### 1. Instalar Git

```bash
sudo apt update
sudo apt install -y git
```

### 2. Baixar o projeto

```bash
git clone https://github.com/mcetrangolo/sistema_chamados.git /tmp/sistema-chamados
cd /tmp/sistema-chamados
```

### 3. Rodar o instalador automatico

```bash
bash scripts/install_linux.sh https://github.com/mcetrangolo/sistema_chamados.git
```

O instalador:

- instala Docker e Docker Compose;
- copia o projeto para `/opt/sistema-chamados`;
- cria o arquivo `.env` inicial usando SQLite;
- gera uma `SECRET_KEY`;
- sobe Django/Gunicorn, Nginx e scheduler;
- executa migrations e collectstatic;
- carrega dados iniciais;
- valida a aplicacao.

Ao final, acesse:

```text
http://IP_DO_SERVIDOR/
```

Para descobrir o IP:

```bash
hostname -I
```

## Criar usuario administrador

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py createsuperuser
```

Acesse:

```text
http://IP_DO_SERVIDOR/login/
```

## Se a instalacao falhar no Debian 13

Verifique Docker Compose e logs:

```bash
cd /opt/sistema-chamados
docker compose version || docker-compose version
docker compose ps || docker-compose ps
docker compose logs -f web || docker-compose logs -f web
```

Erros comuns:

- `docker: 'compose' is not a docker command`: instale Compose com `sudo apt install -y docker-compose || sudo apt install -y docker-compose-plugin`.
- `port is already allocated`: pare Apache/Nginx local ou altere a porta do servico `nginx` em `docker-compose.yml`.
- falha em `seed_chamados`: confira logs do `web`; se migrations terminaram, rode `docker compose exec web python manage.py seed_chamados`.

## Execucao local no Windows

Copie `.env.example` para `.env` se necessario. O padrao local usa SQLite.

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_chamados
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Acesse:

```text
http://127.0.0.1:8000/
```
