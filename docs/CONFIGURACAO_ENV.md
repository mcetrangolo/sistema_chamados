# Configuracao do .env, IP Fixo e DNS

O arquivo `.env` controla como a aplicacao responde na rede, quais origens podem enviar formularios, como agentes encontram o servidor e quais integracoes estao ativas.

No servidor Docker, edite:

```bash
nano /opt/sistema-chamados/.env
```

## Quando definir IP fixo no servidor

Se o servidor passou a usar um IP fixo, dominio interno ou nome DNS, atualize estas variaveis:

```env
PUBLIC_BASE_URL=http://192.168.0.10
ALLOWED_HOSTS=192.168.0.10,chamados.local,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.0.10,http://chamados.local
```

Se o sistema estiver em uma porta especifica:

```env
PUBLIC_BASE_URL=http://192.168.0.10:8000
ALLOWED_HOSTS=192.168.0.10,chamados.local,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.0.10:8000,http://chamados.local:8000
```

Depois reinicie:

```bash
cd /opt/sistema-chamados
docker compose restart
```

Valide:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py validar_producao
```

## O que cada variavel faz

`PUBLIC_BASE_URL`

Endereco base exibido e usado pelo sistema para links, downloads de agentes e endpoints de coleta. Ajuste quando mudar IP, DNS, porta ou HTTPS.

`ALLOWED_HOSTS`

Lista de IPs/nomes pelos quais o Django aceita responder. Se faltar o IP ou DNS usado no navegador, o sistema pode bloquear o acesso.

`CSRF_TRUSTED_ORIGINS`

Lista de origens confiaveis para formularios. Se faltar, botoes POST podem falhar quando o sistema e acessado por IP, DNS, HTTPS ou proxy.

`INVENTARIO_AGENT_TOKEN`

Token usado pelos agentes de inventario para enviar dados. Em producao, use um valor grande e secreto.

## Efeito nos agentes ja instalados

Se os agentes Windows/Linux foram instalados apontando para o IP antigo, eles podem continuar tentando enviar para o endereco antigo.

Nesses casos:

- reinstale o agente usando o novo endereco; ou
- ajuste o `config.json` no Windows em `C:\ProgramData\SistemaChamadosAgent`; ou
- ajuste a configuracao do agente Linux em `/opt/sistema-chamados-agent`, conforme instalacao.

## E-mail SMTP

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.seudominio.local
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=usuario
EMAIL_HOST_PASSWORD=senha
DEFAULT_FROM_EMAIL=helpdesk@seudominio.local
```

Teste:

```bash
docker compose exec web python manage.py testar_smtp seu.email@dominio.local
```

## Active Directory

```env
AD_SERVER=ldap://dc.seudominio.local
AD_USER=SEUDOMINIO\usuario_consulta
AD_PASSWORD=senha
AD_BASE_DN=DC=seudominio,DC=local
```

Teste:

```bash
docker compose exec web python manage.py testar_ad
```

## Seguranca

- Nunca envie `.env` para o GitHub.
- Em producao, use `DEBUG=False`.
- Para HTTPS publico, revise `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE`.
- Se trocar `INVENTARIO_AGENT_TOKEN`, gere novamente o instalador Windows ou use o ZIP com o token atualizado.
