# Sistema de Chamados, Service Desk e Inventario

Sistema web em Django para helpdesk/service desk, governanca de acessos, base de conhecimento e inventario de rede.

Repositorio:

```text
https://github.com/mcetrangolo/sistema_chamados
```

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
- Backup e restauracao para ambiente local e producao Docker/PostgreSQL.

## Instalacao rapida em Debian/Ubuntu

Use este caminho em uma VPS ou servidor Linux limpo com Debian/Ubuntu.

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
- cria o arquivo `.env` inicial;
- gera `SECRET_KEY` e senha do PostgreSQL;
- sobe PostgreSQL, Django/Gunicorn, Nginx e scheduler;
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

Edite o arquivo de ambiente:

```bash
nano /opt/sistema-chamados/.env
```

Campos mais importantes:

```env
ALLOWED_HOSTS=IP_DO_SERVIDOR,NOME_DO_SERVIDOR
CSRF_TRUSTED_ORIGINS=http://IP_DO_SERVIDOR,http://NOME_DO_SERVIDOR
```

SMTP:

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

Active Directory:

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
docker compose exec web python manage.py testar_smtp seu.email@dominio.local
docker compose exec web python manage.py testar_ad
```

SNMP:

```bash
docker compose exec web python manage.py testar_snmp 192.168.0.1 --community public
```

## Atualizar o sistema no servidor

Quando houver melhorias enviadas ao GitHub, atualize o servidor com:

```bash
cd /opt/sistema-chamados
bash scripts/deploy_linux.sh
```

Rotina recomendada antes de atualizar:

```bash
cd /opt/sistema-chamados
bash scripts/backup_docker.sh
bash scripts/deploy_linux.sh
```

## Backup e restauracao

### Pela interface web

No sistema:

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

### Backup em producao Docker/PostgreSQL

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

O script pede confirmacao digitando `RESTAURAR`.

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
- Inventario: `/inventario/`

## Observacoes

- O arquivo `.env` nunca deve ser enviado ao GitHub.
- O banco local `db.sqlite3`, backups, logs, midias e `staticfiles` ficam fora do Git.
- Em producao, prefira acessar por IP interno ou nome DNS da rede.
- Para HTTPS/domino publico, ajuste `CSRF_TRUSTED_ORIGINS` e as opcoes `SECURE_*` no `.env`.
