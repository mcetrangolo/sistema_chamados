# Backup, Restauração e Operação Diária

## Backup pela interface

Acesse:

```text
Configurações > Backup e restauração
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

Depois da restauração, reinicie a aplicação.

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

## Reinício dos serviços

O controle de serviços deve ser feito pelo terminal do servidor:

```bash
cd /opt/sistema-chamados
docker compose restart
docker compose down
docker compose up -d
```

Em produção, faça backup antes de atualizar ou reiniciar a aplicação.
