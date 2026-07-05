# CMDB

## Objetivo

Criar uma base de configuração capaz de representar relacionamentos entre ativos, serviços, sistemas e infraestrutura.

## Entidades sugeridas

- Ativo;
- Serviço;
- Sistema;
- Servidor;
- Banco de dados;
- Link de internet;
- Switch;
- Firewall;
- Nobreak;
- Contrato;
- Fornecedor.

## Relacionamentos possíveis

- Serviço depende de servidor.
- Servidor depende de switch.
- Sistema depende de banco de dados.
- Link de internet depende de fornecedor.
- Equipamento está protegido por nobreak.
- Contrato cobre determinado serviço.

## Uso prático

A CMDB deve permitir responder perguntas como:

- Quais serviços são afetados se este servidor parar?
- Quais sistemas dependem deste banco de dados?
- Quais setores serão impactados por falha em determinado link?
- Quais equipamentos pertencem a determinado contrato?

## Diretriz

A CMDB deve ser implementada apenas após o inventário e o helpdesk estarem estáveis.
