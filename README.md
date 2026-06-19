# Sistema de Chamados, Service Desk e Inventario

Sistema web em Django para helpdesk/service desk, governanca de acessos, base de conhecimento, contratos e inventario de rede.

Repositorio:

```text
https://github.com/mcetrangolo/sistema_chamados
```

## Recursos principais

- Portal publico para abertura e consulta de chamados.
- Area interna de gestao com filas, SLA, anexos, respostas, impressao e historico.
- Catalogo de servicos com aprovacao quando necessario.
- Base de conhecimento publica e interna.
- Relatorios com filtros e exportacao em XLS/PDF.
- Governanca de acessos e Wi-Fi com aceite e PDF.
- Inventario de ativos, licencas, agentes Windows/Linux e descoberta por rede.
- Descoberta por Nmap, Ping/ICMP, DNS reverso, TCP/portas, SNMP e Active Directory.
- Backup/restauracao, atualizacao via GitHub e controle de servicos pela interface.

## Instalacao rapida em Debian/Ubuntu

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/mcetrangolo/sistema_chamados.git /tmp/sistema-chamados
cd /tmp/sistema-chamados
bash scripts/install_linux.sh https://github.com/mcetrangolo/sistema_chamados.git
```

Depois crie o usuario administrador:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py createsuperuser
```

Acesse:

```text
http://IP_DO_SERVIDOR/
http://IP_DO_SERVIDOR/login/
```

## Atualizacao rapida

No servidor:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py backup_local
bash scripts/deploy_linux.sh
```

Pela interface, superusuarios tambem podem acessar:

```text
Configuracoes > Atualizacoes
```

## Configuracao essencial do .env

O arquivo `.env` controla endereco do servidor, seguranca, banco, e-mail, AD e agente de inventario.

Quando definir IP fixo ou DNS do servidor, revise principalmente:

```env
PUBLIC_BASE_URL=http://IP_DO_SERVIDOR
ALLOWED_HOSTS=IP_DO_SERVIDOR,NOME_DO_SERVIDOR,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://IP_DO_SERVIDOR,http://NOME_DO_SERVIDOR
INVENTARIO_AGENT_TOKEN=gere-um-token-grande-e-secreto
```

Depois reinicie:

```bash
cd /opt/sistema-chamados
docker compose restart
```

Guia completo: [Configuracao do .env](docs/CONFIGURACAO_ENV.md).

## Enderecos principais

- Portal publico: `/`
- Consulta de chamado: `/consultar/`
- Catalogo de servicos: `/catalogo/`
- Base de conhecimento: `/conhecimento/`
- Login interno: `/login/`
- Gestao: `/gestao/`
- Chamados: `/gestao/chamados/`
- Relatorios: `/gestao/relatorios/chamados/`
- Configuracao institucional: `/configuracoes/institucional/`
- Backup e restauracao: `/configuracoes/backup/`
- Atualizacoes: `/configuracoes/atualizacoes/`
- Controle de servicos: `/configuracoes/servicos/`
- Inventario: `/inventario/`

## Documentacao

- [Instalacao e primeiro acesso](docs/INSTALACAO.md)
- [Configuracao do .env, IP fixo e DNS](docs/CONFIGURACAO_ENV.md)
- [Atualizacao pelo GitHub](docs/ATUALIZACAO.md)
- [Backup, restauracao e operacao diaria](docs/BACKUP_OPERACAO.md)
- [Agentes de inventario Windows/Linux](docs/AGENTES_INVENTARIO.md)

## Observacoes importantes

- O arquivo `.env` nunca deve ser enviado ao GitHub.
- O banco SQLite, backups, logs, midias e `staticfiles` ficam fora do Git.
- No Docker atual, o SQLite fica no volume `sqlite_data`, usando o caminho `data/db.sqlite3`.
- Em producao interna, prefira acessar por IP fixo interno ou nome DNS da rede.
- Para HTTPS/dominio publico, ajuste `CSRF_TRUSTED_ORIGINS` e as opcoes `SECURE_*` no `.env`.
