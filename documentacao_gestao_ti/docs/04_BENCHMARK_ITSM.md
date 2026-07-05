# Benchmark ITSM

## Objetivo

Este documento compara soluções consolidadas de gestão de TI para orientar a evolução da plataforma própria, sem intenção de copiar integralmente nenhuma delas.

## GLPI

O GLPI é uma das soluções Open Source mais completas para gestão de ativos de TI e Service Desk.

### Pontos fortes

- Inventário;
- Gestão de ativos;
- Helpdesk;
- SLA;
- Base de conhecimento;
- Gestão de contratos;
- Licenças;
- Plugins;
- Comunidade ampla.

### Pontos fracos

- Pode se tornar complexo;
- Algumas funcionalidades dependem de plugins;
- Arquitetura carrega decisões antigas;
- Nem sempre é simples para pequenas equipes.

## iTop

O iTop é fortemente voltado para ITIL e CMDB.

### Pontos fortes

- CMDB robusta;
- Relação entre ativos, serviços e infraestrutura;
- Gestão de incidentes;
- Gestão de problemas;
- Gestão de mudanças;
- Modelagem de dependências.

### Pontos fracos

- Curva de aprendizado elevada;
- Requer boa disciplina de cadastro;
- Pode ser excessivo para equipes pequenas.

## Znuny

O Znuny é sucessor comunitário do antigo OTRS e tem foco em Service Desk.

### Pontos fortes

- Tickets;
- Filas;
- SLA;
- Escalonamentos;
- Workflows;
- Automações;
- Templates.

### Pontos fracos

- Inventário limitado;
- Gestão patrimonial fraca;
- Interface menos moderna;
- Customizações podem exigir conhecimento específico.

## Comparação com a plataforma própria

A plataforma própria ainda não compete em maturidade com GLPI, iTop ou Znuny. Essas soluções possuem muitos anos de desenvolvimento, comunidade e uso em produção.

O diferencial da plataforma própria deve ser outro:

- Simplicidade;
- Integração nativa;
- Agente próprio;
- Foco em órgão público;
- Baixo acoplamento;
- Controle total da arquitetura;
- API interna;
- Experiência unificada.

## Diretriz

Não tentar superar o GLPI em quantidade de funcionalidades. O objetivo é resolver melhor os problemas específicos do público-alvo.
