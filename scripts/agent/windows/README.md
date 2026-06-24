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
releases\agents\windows\SistemaChamadosAgentSetup.exe
```

O instalador atual e um `.exe` standalone compilado em C#, sem IExpress. Ele nao depende de arquivos temporarios extraidos pelo Windows para iniciar.

O `.exe` versionado em `releases\agents\windows` usa o token padrao `sistema-chamados-agent-local`. Se o servidor usar outro `INVENTARIO_AGENT_TOKEN`, gere novamente o instalador com:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\agent\windows\build_installer.ps1 -AgentToken "TOKEN_DO_SERVIDOR"
```

## Antivirus / CyberCapture

O instalador e um executavel interno sem assinatura digital que grava e executa scripts PowerShell. Antiviruses como Avast/CyberCapture podem classificar o arquivo como desconhecido e enviar para analise. O codigo-fonte completo do instalador e do agente permanece disponivel em `scripts\agent\windows` para auditoria e assinatura digital institucional.

## Instalar manualmente

```powershell
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File .\install_gui.ps1
```

O instalador pergunta:

- IP:porta ou URL do servidor.
- Número de série/patrimônio manual, opcional.

Por padrao, o token ja vai embutido no instalador local. Se o servidor usar outro token no `.env`, ajuste o valor no script e gere novamente o instalador.

O instalador exibe janelas simples de boas-vindas e configuração. Ao final, o agente fica registrado em **Painel de Controle > Programas e Recursos** como `Sistema Chamados Agent`.

Ao atualizar uma instalacao existente, o instalador reaproveita automaticamente servidor, token e numero de patrimonio do `config.json`. Ele tambem instala um icone na bandeja do Windows com comandos para configurar a conexao, enviar uma coleta, reiniciar o agente, abrir o sistema e consultar o ultimo log.

O instalador, os atalhos, o Painel de Controle e a bandeja usam o icone proprio azul do agente com indicador verde de atividade.

O pacote `.exe` grava os scripts internos em `C:\ProgramData\SistemaChamadosAgent`, solicita permissao de Administrador via UAC, cria as tarefas agendadas e executa a primeira coleta sem janela preta de console.

O log da ultima execucao fica em:

```text
C:\ProgramData\SistemaChamadosAgent\last-run.log
```

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
