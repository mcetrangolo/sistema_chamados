# Configuração do .env, IP Fixo e DNS

O arquivo `.env` controla como a aplicação responde na rede, quais origens podem enviar formulários, como agentes encontram o servidor e quais integrações técnicas ficam disponíveis.

No servidor Docker, edite:

```bash
nano /opt/sistema-chamados/.env
```

## Quando definir IP fixo no servidor

Se o servidor passou a usar um IP fixo, domínio interno ou nome DNS, atualize estas variáveis:

```env
PUBLIC_BASE_URL=http://192.168.0.10
ALLOWED_HOSTS=192.168.0.10,chamados.local,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.0.10,http://chamados.local
```

Se o sistema estiver em uma porta específica:

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

## O que cada variável faz

`PUBLIC_BASE_URL`

Endereço base exibido e usado pelo sistema para links, downloads de agentes e endpoints de coleta. Ajuste quando mudar IP, DNS, porta ou HTTPS.

`ALLOWED_HOSTS`

Lista de IPs/nomes pelos quais o Django aceita responder. Se faltar o IP ou DNS usado no navegador, o sistema pode bloquear o acesso.

`CSRF_TRUSTED_ORIGINS`

Lista de origens confiáveis para formulários. Se faltar, botões POST podem falhar quando o sistema é acessado por IP, DNS, HTTPS ou proxy.

`INVENTARIO_AGENT_TOKEN`

Token usado pelos agentes de inventário para enviar dados. Se estiver ausente, o sistema usa o valor fixo de compatibilidade `sistema-chamados-agent-local`. O valor efetivamente carregado e sua origem aparecem para o administrador em **Inventário > Agentes de inventário**. Em produção exposta, use um valor grande e exclusivo no `.env`.

## Efeito nos agentes já instalados

Se os agentes Windows/Linux foram instalados apontando para o IP antigo, eles podem continuar tentando enviar para o endereço antigo.

Nesses casos:

- no Windows, use o ícone do agente na bandeja para alterar servidor e token, ou execute o instalador atual sobre a instalação existente;
- no Linux, ajuste `/etc/sistema-chamados-agent/config.env` e reinicie o temporizador;
- valide uma coleta manual antes de aguardar o próximo ciclo automático.

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
- Se trocar `INVENTARIO_AGENT_TOKEN`, atualize o token nos agentes Windows e Linux ja instalados.
