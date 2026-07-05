# Padrões de Código

## Organização

- Separar regras de negócio em services.
- Separar acesso a dados em repositories ou camada equivalente.
- Evitar lógica complexa em controllers/views.
- Reutilizar componentes.
- Nomear arquivos de forma clara.

## Funções

- Funções devem ter responsabilidade única.
- Evitar funções muito longas.
- Nome da função deve indicar claramente sua finalidade.

## Banco de dados

- Utilizar migrations.
- Criar índices para consultas frequentes.
- Usar chaves estrangeiras quando aplicável.
- Evitar campos genéricos desnecessários.
- Registrar timestamps.

## API

- Padronizar respostas.
- Validar entrada.
- Retornar códigos HTTP adequados.
- Documentar endpoints novos.

## Frontend

- Evitar duplicação de componentes.
- Não colocar regra de negócio no frontend.
- Validar dados também no backend.
- Manter consistência visual.

## Testes

- Criar testes para regras críticas.
- Testar endpoints principais.
- Testar permissões.
- Testar rotinas do agente.
