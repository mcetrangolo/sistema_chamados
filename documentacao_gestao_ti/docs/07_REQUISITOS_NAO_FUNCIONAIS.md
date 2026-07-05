# Requisitos Não Funcionais

## Segurança

- RNF001 — O sistema deve possuir autenticação segura.
- RNF002 — O sistema deve registrar logs de ações relevantes.
- RNF003 — O sistema deve aplicar controle de acesso por perfil.
- RNF004 — Senhas devem ser armazenadas com hash seguro.
- RNF005 — Sessões devem possuir tempo de expiração.
- RNF006 — Operações críticas devem ser auditáveis.

## Desempenho

- RNF020 — Telas principais devem carregar rapidamente em ambiente interno.
- RNF021 — Listagens devem possuir paginação.
- RNF022 — Consultas devem evitar N+1.
- RNF023 — Relatórios pesados devem ser assíncronos quando necessário.

## Usabilidade

- RNF040 — Interface simples e responsiva.
- RNF041 — Usuário deve encontrar informações principais em poucos cliques.
- RNF042 — Campos obrigatórios devem ser claramente indicados.
- RNF043 — Mensagens de erro devem ser compreensíveis.

## Manutenibilidade

- RNF060 — Código deve seguir padrões definidos.
- RNF061 — Regras de negócio devem ficar em services.
- RNF062 — Modelos devem possuir nomes claros.
- RNF063 — APIs devem ser documentadas.

## Escalabilidade

- RNF080 — Arquitetura deve permitir novos módulos.
- RNF081 — Banco deve possuir índices para consultas frequentes.
- RNF082 — Agente deve suportar múltiplas máquinas enviando dados.
