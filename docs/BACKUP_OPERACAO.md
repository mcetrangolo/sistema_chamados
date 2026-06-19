# Backup, Restauracao e Operacao Diaria

## Backup pela interface

Acesse:

```text
Configuracoes > Backup e restauracao
```

A tela permite:

- criar backup;
- baixar backup;
- apagar backups antigos;
- restaurar backup salvo no servidor;
- restaurar enviando um arquivo `.zip`.

Para restaurar pela tela, selecione o arquivo e digite:

```text
RESTAURAR
```

Depois da restauracao, reinicie a aplicacao.

## Backup pelo terminal

```bash
cd /opt/sistema-chamados
docker compose exec web python manage.py backup_local
docker compose exec web python manage.py listar_backups
```

Restaurar:

```bash
docker compose exec web python manage.py restaurar_backup_local backups/NOME_DO_BACKUP.zip --confirmar
```

## Logs

```bash
cd /opt/sistema-chamados
docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f scheduler
```

## Controle de servicos

```bash
docker compose restart
docker compose down
docker compose up -d
```

Pela interface:

```text
Configuracoes > Controle de servicos
```

Superusuarios podem:

- reiniciar servicos;
- parar servicos;
- solicitar reboot do servidor;
- solicitar desligamento do servidor.

Reboot/desligamento ficam bloqueados por padrao. Para habilitar:

```env
ALLOW_SERVER_POWER_ACTIONS=True
```

Use apenas em servidor interno administrado.
