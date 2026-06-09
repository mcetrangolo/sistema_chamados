# Agente Windows de Inventário

Agente compatível com Windows 7, 8, 10 e 11. A coleta usa WMI e o agendamento usa `schtasks.exe` para evitar dependência dos cmdlets modernos de tarefas agendadas.

## Pré-requisitos

- Executar o instalador como Administrador.
- PowerShell habilitado.
- O servidor pode usar o token local padrao ou ter `INVENTARIO_AGENT_TOKEN` configurado no `.env`.
- O computador cliente precisa acessar o servidor na URL informada, por exemplo `http://192.168.0.10:8000`.

## Gerar instalador EXE

No computador de desenvolvimento:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\agent\windows\build_installer.ps1
```

O arquivo será gerado em:

```text
dist\SistemaChamadosAgentSetup.exe
```

Se o Windows não tiver IExpress, distribua a pasta indicada pelo script e execute `install.cmd`.

## Instalar manualmente

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\install.ps1
```

O instalador pergunta:

- IP:porta ou URL do servidor.
- Número de série/patrimônio manual, opcional.

Por padrao, o token ja vai embutido no instalador local. Se o servidor usar outro token no `.env`, ajuste o valor no script e gere novamente o instalador.

O instalador exibe janelas simples de boas-vindas e configuração. Ao final, o agente fica registrado em **Painel de Controle > Programas e Recursos** como `Sistema Chamados Agent`.

## Tarefas criadas

- `SistemaChamadosAgentStartup`: executa ao iniciar o Windows.
- `SistemaChamadosAgentInterval`: executa a cada 6 horas por padrão.

## Arquivos instalados

```text
C:\ProgramData\SistemaChamadosAgent\
```

Inclui `agent.ps1`, `config.json` e `last-run.log`.

## Desinstalar

Use o Painel de Controle ou execute:

```powershell
powershell.exe -ExecutionPolicy Bypass -File C:\ProgramData\SistemaChamadosAgent\uninstall.ps1
```
