# Princípios de Desenvolvimento

## Princípios gerais

Todo código deve ser:

- Simples;
- Modular;
- Legível;
- Testável;
- Reutilizável;
- Documentado quando necessário;
- Coerente com a arquitetura;
- Seguro por padrão;
- Preparado para auditoria.

## O que evitar

- Duplicação de código;
- Regras de negócio no frontend;
- Consultas SQL espalhadas;
- Funções muito longas;
- Classes com responsabilidades excessivas;
- Telas duplicadas;
- Dependências desnecessárias;
- Implementações provisórias sem registro;
- Funcionalidades fora do roadmap sem justificativa.

## Decisão técnica padrão

Sempre que houver dúvida entre uma solução complexa e uma solução simples que atenda ao requisito, escolher a solução simples.

## Regra de ouro

Antes de implementar qualquer funcionalidade, verificar:

1. O objetivo do produto;
2. O roadmap;
3. O módulo relacionado;
4. O modelo de dados;
5. Os padrões de código;
6. As decisões arquiteturais já registradas.
