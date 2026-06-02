# Sistema de Chamados, Service Desk e Inventario

Sistema web em Django para helpdesk/service desk, governanca de acessos, base de conhecimento e inventario de rede.

Repositorio:

```text
https://github.com/mcetrangolo/sistema_chamados
```

## Banco de dados atual

Neste momento o projeto esta configurado para usar **SQLite**.

Isso vale para:

- desenvolvimento local no Windows;
- instalacao inicial no Debian/Ubuntu;
- backup e restauracao pela tela `Configuracoes > Backup e restauracao`.

O PostgreSQL ficou apenas como opcao futura para ambientes maiores.

## Recursos principais

- Portal publico para abertura e consulta de chamados.
- Area interna de gestao com filas, SLA, anexos, respostas, impressao e historico.
- Catalogo de servicos com aprovacao quando necessario.
- Base de conhecimento publica e interna, com imagem e video do YouTube.
- Relatorios com filtros e exportacao em XLS/PDF.
- Governanca com formularios de usuario/acessos e Wi-Fi corporativo, gerando PDF.
- Inventario de rede com ativos editaveis, ocorrencias, chamados vinculados e exclusao em lote.
- Descoberta por Ping/ICMP, DNS reverso, TCP/portas, SNMP e Active Directory.
- Configuracao institucional com nome, CNPJ, endereco, logo, temas visuais, cores e rodape.
- Backup e restauracao com SQLite e pasta `media`.

## Instalacao rapida em Debian/Ubuntu usando SQLite

Use este caminho em uma maquina Debian/Ubuntu limpa.

### 1. Instalar o Git

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

O instalador faz automaticamente:

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

Para descobrir o IP do servidor:

```bash
hostname -I
```

## Criar usuario administrador

Depois da instalacao:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py createsuperuser
```

Acesse a area interna:

```text
http://IP_DO_SERVIDOR/login/
```

## Ajustes depois da instalacao

Edite:

```bash
nano /opt/sistema-chamados/.env
```

Campos principais:

```env
ALLOWED_HOSTS=IP_DO_SERVIDOR,NOME_DO_SERVIDOR
CSRF_TRUSTED_ORIGINS=http://IP_DO_SERVIDOR,http://NOME_DO_SERVIDOR

DB_ENGINE=sqlite
SQLITE_NAME=data/db.sqlite3
```

SMTP, quando for configurar e-mail real:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seudominio.local
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=usuario
EMAIL_HOST_PASSWORD=senha
DEFAULT_FROM_EMAIL=helpdesk@seudominio.local
```

Active Directory, quando for integrar:

```env
AD_SERVER=ldap://dc.seudominio.local
AD_USER=SEUDOMINIO\usuario_consulta
AD_PASSWORD=senha
AD_BASE_DN=DC=seudominio,DC=local
```

Aplicar alteracoes:

```bash
cd /opt/sistema-chamados
docker compose up -d
```

Validar:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py validar_producao
```

Testes opcionais:

```bash
docker compose exec web python manage.py testar_smtp seu.email@dominio.local
docker compose exec web python manage.py testar_ad
docker compose exec web python manage.py testar_snmp 192.168.0.1 --community public
```

## Atualizar o sistema no servidor

Quando houver melhorias enviadas ao GitHub:

```bash
cd /opt/sistema-chamados
bash scripts/deploy_linux.sh
```

Rotina recomendada antes de atualizar:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py backup_local
bash scripts/deploy_linux.sh
```

Tambem existe uma tela em:

```text
Configuracoes > Atualizacoes
```

Ela mostra branch, commit atual, repositorio e atualizacoes pendentes. Quando a instalacao estiver rodando a partir de uma pasta Git, a tela tambem permite verificar e aplicar atualizacoes. Em Docker/servidor, o metodo mais seguro continua sendo `bash scripts/deploy_linux.sh` no terminal.

## Backup e restauracao com SQLite

Pela interface web:

```text
Configuracoes > Backup e restauracao
```

A tela permite:

- criar backup;
- baixar backup;
- apagar backups antigos;
- restaurar um backup salvo no servidor;
- restaurar enviando um arquivo `.zip` do computador.

Para restaurar pela tela, selecione o arquivo e digite:

```text
RESTAURAR
```

Depois da restauracao, reinicie o servidor da aplicacao.

Pelo terminal:

```bash
docker compose exec web python manage.py backup_local
docker compose exec web python manage.py listar_backups
docker compose exec web python manage.py restaurar_backup_local backups/NOME_DO_BACKUP.zip --confirmar
```

## Operacao diaria

Ver logs:

```bash
cd /opt/sistema-chamados
docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f scheduler
```

Reiniciar:

```bash
docker compose restart
```

Parar:

```bash
docker compose down
```

Executar comandos Django:

```bash
docker compose exec web python manage.py COMANDO
```

## Execucao local no Windows

Copie `.env.example` para `.env` se necessario. O padrao local tambem usa SQLite.

Instale as dependencias:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python manage.py migrate
python manage.py seed_chamados
python manage.py runserver 0.0.0.0:8000
```

Acesse:

```text
http://127.0.0.1:8000/
```

## PostgreSQL no futuro

PostgreSQL nao e obrigatorio neste momento.

Se futuramente quiser migrar para PostgreSQL em Docker, ha um arquivo separado:

```text
docker-compose.postgresql.yml
```

O comando base seria:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgresql.yml up -d --build
```

Antes de migrar, faca backup e planeje a transferencia dos dados SQLite para PostgreSQL.

## Enderecos principais

- Portal publico: `/`
- Consulta de chamado: `/consultar/`
- Catalogo de servicos: `/catalogo/`
- Base de conhecimento: `/conhecimento/`
- Governanca: `/governanca/`
- Login interno: `/login/`
- Gestao: `/gestao/`
- Chamados: `/gestao/chamados/`
- Relatorios: `/gestao/relatorios/chamados/`
- Aprovacoes: `/gestao/aprovacoes/`
- Configuracao institucional: `/configuracoes/institucional/`
- Backup e restauracao: `/configuracoes/backup/`
- Atualizacoes: `/configuracoes/atualizacoes/`
- Inventario: `/inventario/`

## Observacoes

- O arquivo `.env` nunca deve ser enviado ao GitHub.
- O banco SQLite, backups, logs, midias e `staticfiles` ficam fora do Git.
- No Docker atual, o SQLite fica no volume `sqlite_data`, usando o caminho `data/db.sqlite3`.
- Em producao interna, prefira acessar por IP interno ou nome DNS da rede.
- Para HTTPS/dominio publico, ajuste `CSRF_TRUSTED_ORIGINS` e as opcoes `SECURE_*` no `.env`.
