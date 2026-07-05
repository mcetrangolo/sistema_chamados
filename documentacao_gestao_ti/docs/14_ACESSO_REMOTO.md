# Módulo de Acesso Remoto

## Objetivo

Permitir que técnicos acessem remotamente equipamentos de forma controlada, integrada ao inventário e aos chamados.

## Integrações previstas

- Apache Guacamole;
- RustDesk;
- VNC;
- RDP;
- SSH.

## Funcionalidades

- Associar método de acesso remoto ao ativo;
- Iniciar conexão a partir do cadastro do ativo;
- Iniciar conexão a partir do chamado;
- Registrar técnico que iniciou acesso;
- Registrar data/hora;
- Registrar justificativa;
- Controlar permissões;
- Exibir histórico de acessos.

## Regras de segurança

- Acesso remoto deve ser permitido apenas a técnicos autorizados.
- Acesso deve ser registrado em auditoria.
- Quando possível, vincular acesso a um chamado.
- Evitar armazenar senhas em texto claro.
- Utilizar cofres de credenciais ou mecanismos seguros quando implementados.

## Diretriz

O acesso remoto deve reduzir o tempo de atendimento sem comprometer segurança, rastreabilidade e transparência.
