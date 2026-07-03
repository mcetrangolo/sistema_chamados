# Agente Windows de InventÃ¡rio

Agente compatÃ­vel com Windows 7, 8, 10 e 11 em um Ãºnico instalador. A coleta usa WMI, serializaÃ§Ã£o JSON prÃ³pria compatÃ­vel com PowerShell 2.0 e o agendamento usa `schtasks.exe` para evitar dependÃªncia dos cmdlets modernos de tarefas agendadas. Pedidos feitos pelo botÃ£o **Solicitar coleta** sÃ£o consultados a cada minuto sem executar o inventÃ¡rio completo quando nÃ£o hÃ¡ pedido pendente.

## PrÃ©-requisitos

- Executar o instalador como Administrador.
- PowerShell habilitado. No Windows 7, o agente evita recursos exclusivos do PowerShell 3+.
- .NET Framework 3.5 ou superior para o instalador grÃ¡fico e o Ã­cone da bandeja.
- O servidor pode usar o token local padrao ou ter `INVENTARIO_AGENT_TOKEN` configurado no `.env`.
- O computador cliente precisa acessar o servidor na URL informada, por exemplo `http://192.168.0.10:8000`.

## Gerar instalador EXE

No computador de desenvolvimento:

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File .\scripts\agent\windows\build_installer.ps1
```

O arquivo serÃ¡ gerado em:

```text
dist\SistemaChamadosAgentSetup.exe
releases\agents\windows\SistemaChamadosAgentSetup.exe
```

O instalador atual e um `.exe` standalone compilado em C#, sem IExpress. Ele nao depende de arquivos temporarios extraidos pelo Windows para iniciar.
Durante o build, o script tenta compilar com .NET Framework 3.5 primeiro para manter compatibilidade com Windows 7; se o compilador 3.5 nao existir, usa .NET Framework 4.x.

O `.exe` versionado em `releases\agents\windows` usa o token padrao `sistema-chamados-agent-local`. Se o servidor usar outro `INVENTARIO_AGENT_TOKEN`, gere novamente o instalador com:

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File .\scripts\agent\windows\build_installer.ps1 -AgentToken "TOKEN_DO_SERVIDOR"
```

## Antivirus / falso positivo

O instalador e um executavel interno sem assinatura digital que grava scripts PowerShell locais, cria tarefas agendadas e envia inventario para o servidor configurado. Antiviruses corporativos podem classificar executaveis internos sem reputacao como desconhecidos, principalmente quando o pacote ainda nao possui assinatura digital.

A partir da versao 1.4.8, o instalador usa `ExecutionPolicy RemoteSigned` em vez de `Bypass` e evita iniciar a instalacao grafica como processo explicitamente oculto. Isso reduz alertas heurísticos sem alterar a coleta.

Para ambiente de producao, o caminho mais profissional e assinar digitalmente `SistemaChamadosAgentSetup.exe` e `SistemaChamadosAgentTray.exe` com certificado de publicador da instituicao. Se o antivirus ainda bloquear, gere o hash SHA256 do instalador publicado e cadastre excecao apenas para esse hash, nunca para uma pasta inteira.

O codigo-fonte completo do instalador e do agente permanece disponivel em `scripts\agent\windows` para auditoria.

## Instalar manualmente

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File .\install_gui.ps1
```

O instalador pergunta:

- IP:porta ou URL do servidor.
- NÃºmero de sÃ©rie/patrimÃ´nio manual, opcional.

Por padrao, o token ja vai embutido no instalador local. Se o servidor usar outro token no `.env`, ajuste o valor no script e gere novamente o instalador.

O instalador exibe janelas simples de boas-vindas e configuraÃ§Ã£o. Ao final, o agente fica registrado em **Painel de Controle > Programas e Recursos** como `Sistema Chamados Agent`.

Ao atualizar uma instalacao existente, o instalador reaproveita automaticamente servidor, token e numero de patrimonio do `config.json`. Ele tambem instala um icone na bandeja do Windows com comandos para configurar a conexao, enviar uma coleta, reiniciar o agente, abrir o sistema e consultar o ultimo log.

O instalador, os atalhos, o Painel de Controle e a bandeja usam o icone proprio azul do agente com indicador verde de atividade.

O pacote `.exe` grava os scripts internos em `C:\ProgramData\SistemaChamadosAgent`, solicita permissao de Administrador via UAC, cria as tarefas agendadas e executa a primeira coleta sem janela preta de console.

O log da ultima execucao fica em:

```text
C:\ProgramData\SistemaChamadosAgent\last-run.log
```

## Tarefas criadas

- `SistemaChamadosAgentStartup`: executa ao iniciar o Windows.
- `SistemaChamadosAgentInterval`: executa a cada 6 horas por padrÃ£o.
- `SistemaChamadosAgentSolicitacoes`: verifica a cada minuto se o servidor solicitou uma coleta manual.

## Arquivos instalados

```text
C:\ProgramData\SistemaChamadosAgent\
```

Inclui `agent.ps1`, `config.json` e `last-run.log`.

## Desinstalar

Use o Painel de Controle ou execute:

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -File C:\ProgramData\SistemaChamadosAgent\uninstall.ps1
```
