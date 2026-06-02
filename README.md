# Sistema de Controle de Chamados, Service Desk e Inventário

Sistema web em Django para helpdesk/service desk, governança de acessos, base de conhecimento e inventário de rede.

## Recursos principais

- Portal público para abertura e consulta de chamados.
- Área interna de gestão com filas, SLA, anexos, respostas, impressão e histórico.
- Catálogo de serviços com aprovação quando necessário.
- Base de conhecimento pública e interna, com imagem e vídeo do YouTube.
- Relatórios com filtros e exportação em XLS/PDF.
- Governança com formulários de usuário/acessos e Wi-Fi corporativo, gerando PDF.
- Inventário de rede com ativos editáveis, ocorrências, chamados vinculados e exclusão em lote.
- Descoberta por Ping/ICMP, DNS reverso, TCP/portas, SNMP e Active Directory.
- Configuração institucional com nome, CNPJ, endereço, logo, temas visuais, cores e rodapé.
- Backup e restauração para ambiente local e produção Docker/PostgreSQL.

## Instalação fácil em produção

O caminho recomendado para Debian/Ubuntu é usar:

```text
GitHub -> Docker Compose -> Nginx -> Gunicorn -> Django -> PostgreSQL
```

### 1. Enviar o projeto para o GitHub

No seu computador:

```bash
git init
git add .
git commit -m "Versao inicial do sistema de chamados"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/sistema-chamados.git
git push -u origin main
```

Use um repositório privado. O arquivo `.env`, banco local, logs, backups, mídia e `staticfiles` não devem ser enviados.

### 2. Instalar no servidor Linux

No servidor Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/SEU_USUARIO/sistema-chamados.git /tmp/sistema-chamados
cd /tmp/sistema-chamados
bash scripts/install_linux.sh https://github.com/SEU_USUARIO/sistema-chamados.git
```

O instalador cria o projeto em `/opt/sistema-chamados`, instala Docker, gera `.env`, sobe os containers e valida a aplicação.

Ao final, acesse:

```text
http://IP_DO_SERVIDOR/
```

## Ajustes obrigatórios depois da instalação

Edite:

```bash
nano /opt/sistema-chamados/.env
```

Configure SMTP:

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

Configure Active Directory:

```env
AD_SERVER=ldap://dc.seudominio.local
AD_USER=SEUDOMINIO\usuario_consulta
AD_PASSWORD=senha
AD_BASE_DN=DC=seudominio,DC=local
```

Depois aplique:

```bash
cd /opt/sistema-chamados
docker compose up -d
docker compose exec web python manage.py validar_producao
docker compose exec web python manage.py testar_smtp seu.email@dominio.local
docker compose exec web python manage.py testar_ad
```

Para SNMP:

```bash
docker compose exec web python manage.py testar_snmp 192.168.0.1 --community public
```

## Atualização

Quando você alterar o projeto no PC e enviar para o GitHub:

```bash
cd /opt/sistema-chamados
bash scripts/deploy_linux.sh
```

## Backup e restauração

### Ambiente local com SQLite

Pela interface web:

```text
Configurações > Backup e restauração
```

A tela permite criar, baixar, apagar e restaurar backups locais. Para restaurar em caso de catástrofe, escolha o arquivo `.zip` salvo no seu computador e digite `RESTAURAR`.

Criar backup:

```bash
python manage.py backup_local
```

Listar backups:

```bash
python manage.py listar_backups
```

Validar um backup antes de restaurar:

```bash
python manage.py restaurar_backup_local backups/backup_20260601_230000.zip
```

Restaurar de verdade:

```bash
python manage.py restaurar_backup_local backups/backup_20260601_230000.zip --confirmar
```

O comando cria backup prévio do estado atual antes da restauração. Depois de restaurar, reinicie o servidor da aplicação.

### Produção Docker com PostgreSQL

Criar backup:

```bash
cd /opt/sistema-chamados
bash scripts/backup_docker.sh
```

Restaurar banco PostgreSQL:

```bash
cd /opt/sistema-chamados
bash scripts/restore_docker.sh backups/postgres_20260601_230000.dump
```

O script pede confirmação digitando `RESTAURAR`, para os containers `web` e `scheduler`, restaura o dump e sobe os serviços novamente.

Observação: arquivos enviados, logos e anexos ficam no volume/pasta `media`. Para restauração completa em produção, mantenha também cópia do volume `media_data` ou da pasta `media` exportada pelo backup local.

## Operação diária

Ver logs:

```bash
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

Criar usuário administrador:

```bash
docker compose exec web python manage.py createsuperuser
```

## Execução local no Windows

Instale as dependências:

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

## Endereços principais

- Portal público: `/`
- Consulta de chamado: `/consultar/`
- Catálogo de serviços: `/catalogo/`
- Base de conhecimento: `/conhecimento/`
- Governança: `/governanca/`
- Login interno: `/login/`
- Gestão: `/gestao/`
- Chamados: `/gestao/chamados/`
- Relatórios: `/gestao/relatorios/chamados/`
- Aprovações: `/gestao/aprovacoes/`
- Configuração institucional: `/configuracoes/institucional/`
- Inventário: `/inventario/`
