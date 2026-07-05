# Implantação

## Ambientes

- Desenvolvimento;
- Homologação;
- Produção.

## Requisitos gerais

- Servidor web;
- Banco de dados;
- Rotina de backup;
- HTTPS em produção;
- Controle de acesso;
- Logs;
- Monitoramento básico.

## Boas práticas

- Nunca desenvolver diretamente em produção.
- Usar controle de versão.
- Manter arquivo `.env` fora do repositório público.
- Documentar variáveis de ambiente.
- Realizar backup antes de atualizações.
- Testar restauração periodicamente.

## Checklist de produção

- DEBUG desativado;
- HTTPS configurado;
- Banco protegido;
- Backup agendado;
- Logs ativos;
- Usuário administrador criado;
- Permissões revisadas;
- Agente configurado;
- Documentação atualizada.
