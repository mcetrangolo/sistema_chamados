# Agente Linux de Inventario

Agente para Debian, Ubuntu, Proxmox e distribuicoes Linux com Python 3.

O agente consulta a cada minuto se existe uma coleta solicitada pelo servidor. A coleta completa continua sendo executada periodicamente e somente é antecipada quando há um pedido pendente.

## Instalar

Baixe o script pela tela de inventario e execute:

```sh
sudo sh sistema-chamados-agent-linux.sh
```

O instalador pergunta:

- IP:porta ou URL do servidor.
- Numero de serie/patrimonio manual, opcional.

## Frequencia

Com `systemd`, o instalador cria:

- `sistema-chamados-agent.service`
- `sistema-chamados-agent.timer`

O timer executa no boot e a cada 6 horas.

Se o sistema nao tiver `systemd`, o instalador cria `/etc/cron.d/sistema-chamados-agent`.

## Arquivos

```text
/opt/sistema-chamados-agent/agent.py
/opt/sistema-chamados-agent/uninstall.sh
/etc/sistema-chamados-agent/config.env
/var/log/sistema-chamados-agent.log
```

## Desinstalar

```sh
sudo sh /opt/sistema-chamados-agent/uninstall.sh
```
