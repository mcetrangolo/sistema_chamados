Set-Location -Path $PSScriptRoot\..
python manage.py executar_varreduras
python manage.py backup_local
