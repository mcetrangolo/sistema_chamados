# Agentes de Inventario Windows/Linux

## Agente Windows

O agente Windows coleta dados da maquina e envia para:

```text
POST /inventario/agente/coleta/
```

Dados coletados:

- hostname, IP principal e MAC;
- usuario logado e dominio/grupo de trabalho;
- fabricante, modelo e numero de serie;
- versao/build do Windows e arquitetura;
- processador, memoria total e disco total;
- Microsoft Office/Microsoft 365 quando detectado;
- lista resumida de softwares instalados;
- interfaces de rede ativas.

## Download pelo sistema

Acesse:

```text
Inventario > Configurar agente
```

Downloads disponiveis:

- instalador Windows `.exe`;
- pacote Windows `.zip` sem executavel compilado;
- instalador Linux `.sh`.

O ZIP Windows e gerado com scripts e token atuais da instalacao e inclui:

```text
InstalarAgente.cmd
install_gui.ps1
install.ps1
agent.ps1
uninstall.ps1
README.md
```

## Instalar no Windows

Baixe o ZIP ou EXE pela tela de agentes.

No ZIP, extraia e execute como Administrador:

```text
InstalarAgente.cmd
```

Durante a instalacao, informe o IP ou URL do servidor:

```text
192.168.0.10
http://192.168.0.10
https://chamados.seudominio.local
```

O agente cria tarefas agendadas:

- `SistemaChamadosAgentStartup`;
- `SistemaChamadosAgentInterval`.

## Instalar no Linux

Baixe o arquivo pela tela de agentes e execute:

```bash
sudo sh sistema-chamados-agent-linux.sh
```

O agente usa `systemd timer` quando disponivel; caso contrario, usa cron.

## Token do agente

Configure no `.env`:

```env
INVENTARIO_AGENT_TOKEN=gere-um-token-grande-e-secreto
```

Depois reinicie:

```bash
docker compose restart
```

Se trocar o token, gere novamente o instalador ou use o ZIP atualizado pela tela.
