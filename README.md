# Sistema de Chamados, Service Desk e Inventário

Sistema web em Django para helpdesk/service desk, governança de acessos, base de conhecimento, contratos e inventário de rede. Esta solução foi criada como uma alternativa open source e gratuita para setores de TI de órgãos municipais. A ideia é algo simples e eficiente, que qualquer um possa usar e melhorar.

Repositório:

```text
https://github.com/mcetrangolo/sistema_chamados
```

## Recursos principais

- Portal público para abertura e consulta de chamados.
- Área interna de gestão com filas, SLA, anexos, respostas, impressão e histórico.
- Catálogo de serviços com aprovação quando necessário.
- Base de conhecimento pública e interna.
- Relatórios com filtros e exportação em XLS/PDF.
- Governança de acessos e Wi-Fi como chamados GOV restritos para tramitação pela equipe autorizada.
- Inventário de ativos, agentes Windows/Linux e descoberta por rede.
- Descoberta por Nmap, Ping/ICMP, DNS reverso, TCP/portas, SNMP e Active Directory.
- Backup/restauração e atualização via GitHub pela interface.

## Instalação rápida em Debian/Ubuntu

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/mcetrangolo/sistema_chamados.git /tmp/sistema-chamados
cd /tmp/sistema-chamados
bash scripts/install_linux.sh https://github.com/mcetrangolo/sistema_chamados.git
```

Depois crie o usuário administrador:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py createsuperuser
```

Acesse:

```text
http://IP_DO_SERVIDOR/
http://IP_DO_SERVIDOR/login/
```

## Atualização rápida

No servidor:

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py backup_local
bash scripts/deploy_linux.sh
```

Pela interface, superusuários também podem acessar:

```text
Configurações > Atualizações
```

## Configuração essencial do .env

O arquivo `.env` controla endereço do servidor, segurança, banco, e-mail, AD e agente de inventário.

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

Guia completo: [Configuração do .env](docs/CONFIGURACAO_ENV.md).

## Endereços principais

- Portal público: `/`
- Consulta de chamado: `/consultar/`
- Catálogo de serviços: `/catalogo/`
- Base de conhecimento: `/conhecimento/`
- Login interno: `/login/`
- Gestão: `/gestao/`
- Chamados: `/gestao/chamados/`
- Relatórios: `/gestao/relatorios/chamados/`
- Configuração institucional: `/configuracoes/institucional/`
- Backup e restauração: `/configuracoes/backup/`
- Atualizações: `/configuracoes/atualizacoes/`
- Inventário: `/inventario/`

## Documentação

- [Instalação e primeiro acesso](docs/INSTALACAO.md)
- [Configuração do .env, IP fixo e DNS](docs/CONFIGURACAO_ENV.md)
- [Atualização pelo GitHub](docs/ATUALIZACAO.md)
- [Backup, restauração e operação diária](docs/BACKUP_OPERACAO.md)
- [Agentes de inventário Windows/Linux](docs/AGENTES_INVENTARIO.md)

## Observações importantes

- O arquivo `.env` nunca deve ser enviado ao GitHub.
- O banco SQLite, backups, logs, mídias e `staticfiles` ficam fora do Git.
- No Docker atual, o SQLite fica no volume `sqlite_data`, usando o caminho `data/db.sqlite3`.
- Em produção interna, prefira acessar por IP fixo interno ou nome DNS da rede.
- Para HTTPS/domínio público, ajuste `CSRF_TRUSTED_ORIGINS` e as opções `SECURE_*` no `.env`.
