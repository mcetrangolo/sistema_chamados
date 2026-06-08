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

### Se a instalacao falhar no Debian 13

O instalador tenta usar `docker compose` e, se necessario, `docker-compose`.
Para diagnosticar:

```bash
cd /opt/sistema-chamados
docker compose version || docker-compose version
docker compose ps || docker-compose ps
docker compose logs -f web || docker-compose logs -f web
```

Erros comuns:

- `docker: 'compose' is not a docker command`: instale Compose com `sudo apt install -y docker-compose || sudo apt install -y docker-compose-plugin` e rode o instalador novamente.
- `port is already allocated` ou erro na porta `80`: pare Apache/Nginx local ou altere a porta do servico `nginx` em `docker-compose.yml`.
- falha em `seed_chamados`: confira os logs do `web`; se as migrations terminaram, rode `docker compose exec web python manage.py seed_chamados` novamente.

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

Agente de inventario:

```env
INVENTARIO_AGENT_TOKEN=gere-um-token-grande-e-secreto
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
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

O comando `createsuperuser` cria o administrador inicial para acessar a area interna, cadastros, configuracoes e relatorios.

Acesse:

```text
http://127.0.0.1:8000/
```

## Enderecos principais

- Portal publico: `/`
- Consulta de chamado: `/consultar/`
- Catalogo de servicos: `/catalogo/`
- Base de conhecimento: `/conhecimento/`
- Governanca: centralizada no catalogo de servicos (`/catalogo/`); `/governanca/` redireciona para o catalogo.
- Login interno: `/login/`
- Gestao: `/gestao/`
- Chamados: `/gestao/chamados/`
- Relatorios: `/gestao/relatorios/chamados/`
- Aprovacoes: `/gestao/aprovacoes/`
- Configuracao institucional: `/configuracoes/institucional/`
- Backup e restauracao: `/configuracoes/backup/`
- Atualizacoes: `/configuracoes/atualizacoes/`
- Controle de servicos: `/configuracoes/servicos/`
- Inventario: `/inventario/`

## Controle de servicos pela interface

Superusuarios podem acessar:

```text
Configuracoes > Controle de servicos
```

A tela possui botoes para:

- reiniciar servicos da aplicacao;
- parar servicos da aplicacao;
- solicitar reboot do servidor;
- solicitar desligamento do servidor.

Reiniciar/parar servicos depende de Docker Compose estar disponivel para o processo web. Reboot e desligamento do servidor ficam bloqueados por padrao; para habilitar, defina no `.env`:

```env
ALLOW_SERVER_POWER_ACTIONS=True
```

Use essa opcao apenas em servidor interno administrado, porque a acao pode interromper o acesso ao sistema.

## Agente de inventario para Windows

O projeto inclui um agente inicial em PowerShell para coletar dados de computadores Windows e enviar para o servidor.

No servidor, configure no `.env`:

```env
INVENTARIO_AGENT_TOKEN=gere-um-token-grande-e-secreto
```

Reinicie a aplicacao depois de alterar o `.env`.

No computador Windows que sera inventariado, abra PowerShell como Administrador na pasta do projeto ou onde os arquivos foram copiados e execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\scripts\agent\windows\install.ps1
```

Durante a instalacao, informe o IP ou URL do servidor, por exemplo:

```text
192.168.0.10:8000
```

ou:

```text
https://chamados.seudominio.local
```

O instalador:

- pergunta o servidor e o token;
- permite informar um numero de serie manual/patrimonio opcional;
- copia o agente para `C:\ProgramData\SistemaChamadosAgent`;
- grava `config.json`;
- cria a tarefa agendada `SistemaChamadosAgent`;
- executa a primeira coleta.

Dados coletados pelo agente Windows:

- hostname, IP principal e MAC;
- usuario logado, dominio/grupo de trabalho;
- fabricante, modelo e numero de serie;
- versao/build do Windows e arquitetura;
- processador, memoria total e disco total;
- Microsoft Office/Microsoft 365 instalado, quando detectado;
- lista resumida de softwares instalados;
- interfaces de rede ativas.

O endpoint usado pelo agente e:

```text
POST /inventario/agente/coleta/
```

## Observacoes

- O arquivo `.env` nunca deve ser enviado ao GitHub.
- O banco SQLite, backups, logs, midias e `staticfiles` ficam fora do Git.
- No Docker atual, o SQLite fica no volume `sqlite_data`, usando o caminho `data/db.sqlite3`.
- Em producao interna, prefira acessar por IP interno ou nome DNS da rede.
- Para HTTPS/dominio publico, ajuste `CSRF_TRUSTED_ORIGINS` e as opcoes `SECURE_*` no `.env`.
