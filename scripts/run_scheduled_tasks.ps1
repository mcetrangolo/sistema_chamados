Set-Location -Path $PSScriptRoot\..
python manage.py executar_varreduras
python manage.py verificar_status_ativos
python manage.py backup_local
