# Agentes de Inventario Windows/Linux

Os agentes coletam dados do equipamento e enviam para:

```text
POST /inventario/agente/coleta/
```

Entre os dados coletados estao hostname, IP, MAC, usuario, fabricante, modelo, numero de serie, sistema operacional, processador, memoria, disco, interfaces de rede e softwares detectados.

## Download pelo sistema

Acesse:

```text
Inventario > Agentes de inventario
```

Estao disponiveis o instalador Windows `.exe` e o instalador Linux `.sh`. O antigo pacote ZIP do Windows nao e mais necessario.

## Windows

Baixe e execute `SistemaChamadosAgentSetup.exe` como administrador. O mesmo instalador atende Windows 7, 8, 10 e 11; no Windows 7 o agente evita recursos exclusivos do PowerShell 3+ e usa coleta via WMI. Durante a instalacao, informe o IP ou URL do servidor, a porta quando aplicavel e o token apresentado pelo administrador.

Exemplos de endereco:

```text
http://192.168.0.10
http://192.168.0.10:8000
https://chamados.seudominio.local
```

O instalador cria as tarefas `SistemaChamadosAgentStartup`, `SistemaChamadosAgentInterval` e `SistemaChamadosAgentSolicitacoes`. A coleta ocorre na inicializacao, a cada 6 horas e tambem quando o servidor marca uma coleta manual pela tela de agentes. A verificacao de solicitacoes e leve e nao executa inventario completo quando nao ha pedido pendente. O icone na bandeja permite:

- configurar servidor, porta e token;
- enviar uma coleta imediatamente;
- reiniciar as tarefas do agente;
- abrir o log e o sistema;
- consultar os dados da instalacao.

Uma atualizacao preserva a configuracao existente. A desinstalacao fica disponivel nos Aplicativos do Windows e no Menu Iniciar.

## Linux

Baixe o arquivo pela tela de agentes e execute:

```bash
sudo sh sistema-chamados-agent-linux.sh
```

Com systemd, o instalador cria um servico e um temporizador que executa no boot e a cada 6 horas. Sem systemd, usa cron. A configuracao fica em:

```text
/etc/sistema-chamados-agent/config.env
```

## Token do agente

No servidor, configure um valor grande e secreto no `.env`:

```env
INVENTARIO_AGENT_TOKEN=gere-um-token-grande-e-secreto
```

Por compatibilidade, o valor padrao e `sistema-chamados-agent-local`. O sistema identifica na tela **Inventario > Agentes de inventario** se esta usando esse token fixo ou um valor exclusivo definido no `.env`. Em redes expostas, sempre configure um token exclusivo.

Depois reinicie:

```bash
cd /opt/sistema-chamados
docker compose restart
```

Ao trocar o token, atualize tambem os equipamentos instalados. No Windows, use o icone da bandeja ou execute o instalador atual sobre a instalacao existente. No Linux, edite `/etc/sistema-chamados-agent/config.env` e reinicie o timer.

O retorno `403 - Token invalido ou nao configurado` indica que o token do equipamento nao coincide com o valor efetivamente exibido pelo servidor. No Windows, corrija pelo icone da bandeja; no Linux, atualize o arquivo de configuracao.
