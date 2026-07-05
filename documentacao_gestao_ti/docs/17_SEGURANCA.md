# Segurança

## Objetivo

Definir práticas mínimas de segurança para a plataforma.

## Controle de acesso

- Usuários devem possuir perfis.
- Perfis devem definir permissões.
- Operações críticas devem exigir permissão específica.
- Técnicos devem visualizar apenas o necessário para sua função, quando aplicável.

## Auditoria

Registrar:

- Login;
- Logout;
- Criação de registros;
- Alteração de registros;
- Exclusão de registros;
- Acesso remoto;
- Alteração de permissões;
- Exportação de relatórios.

## Dados sensíveis

- Evitar armazenar senhas.
- Não armazenar informações pessoais desnecessárias.
- Proteger credenciais de acesso remoto.
- Sanitizar entradas do usuário.

## Boas práticas

- Validar dados no backend.
- Usar HTTPS em produção.
- Manter dependências atualizadas.
- Evitar exposição de stack trace.
- Criar rotina de backup.
- Testar restauração de backup.
