# Decisões Arquiteturais

Este documento registra decisões relevantes do projeto.

## ADR001 — Plataforma modular

### Decisão

A plataforma será organizada em módulos independentes.

### Motivo

Facilitar manutenção, evolução e testes.

### Consequência

Cada módulo deve possuir responsabilidades claras e se comunicar preferencialmente por services/APIs.

---

## ADR002 — API First

### Decisão

Funcionalidades devem ser expostas por API interna.

### Motivo

Facilitar integração com frontend, agente, dashboards, IA e sistemas externos.

### Consequência

Toda nova funcionalidade relevante deve considerar endpoints e documentação.

---

## ADR003 — Agente próprio

### Decisão

Será utilizado agente próprio para coleta de inventário.

### Motivo

Permitir controle total da coleta e integração com a plataforma.

### Consequência

O agente deve ser versionado, documentado e compatível com ambientes legados quando possível.

---

## ADR004 — Simplicidade operacional

### Decisão

A plataforma priorizará simplicidade de uso em vez de excesso de funcionalidades.

### Motivo

O público-alvo inclui pequenas e médias equipes de TI.

### Consequência

Funcionalidades complexas devem ser implementadas apenas quando houver necessidade real.
