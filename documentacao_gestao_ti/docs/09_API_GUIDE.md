# Guia de API

## Princípios

A API deve ser previsível, consistente e documentada.

## Convenções

- Usar JSON como formato padrão.
- Usar rotas REST quando aplicável.
- Usar nomes no plural para recursos.
- Usar versionamento quando necessário.

## Exemplos de rotas

```text
GET    /api/ativos/
POST   /api/ativos/
GET    /api/ativos/{id}/
PATCH  /api/ativos/{id}/
DELETE /api/ativos/{id}/

GET    /api/chamados/
POST   /api/chamados/
GET    /api/chamados/{id}/
PATCH  /api/chamados/{id}/
POST   /api/chamados/{id}/comentarios/
```

## Respostas

### Sucesso

```json
{
  "success": true,
  "data": {}
}
```

### Erro

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Campos obrigatórios não informados."
  }
}
```

## Autenticação

A autenticação deve suportar login local e integração com Active Directory/LDAP.

## Auditoria

Operações de criação, edição e exclusão devem registrar usuário, data, IP e recurso alterado.
