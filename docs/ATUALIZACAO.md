# Atualizacao pelo GitHub

## Caminho recomendado no servidor

Antes de atualizar, crie backup:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py backup_local
```

Atualize:

```bash
bash scripts/deploy_linux.sh
```

O script executa:

- `git pull --ff-only`;
- rebuild/restart dos containers;
- `python manage.py check`;
- `python manage.py validar_producao`.

## Pela interface web

Superusuarios podem acessar:

```text
Configuracoes > Atualizacoes
```

A tela mostra:

- branch atual;
- commit atual;
- repositorio remoto;
- commits pendentes;
- estado local do Git;
- resultado da ultima verificacao ou atualizacao.

Quando o ambiente permite, o botao usa o mesmo script do README:

```bash
bash scripts/deploy_linux.sh
```

Quando o script nao esta disponivel, usa fallback interno:

```bash
git fetch --prune
git pull --ff-only
python manage.py migrate
python manage.py collectstatic --noinput
```

## Atualizacao manual

```bash
cd /opt/sistema-chamados
git status --short
docker compose exec web python manage.py backup_local
git fetch --prune
git pull --ff-only origin main
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose restart
docker compose exec web python manage.py check
docker compose exec web python manage.py validar_producao
```

Se `git status --short` mostrar arquivos modificados, pare antes do `git pull` e confira o que mudou.
