Set-Location -Path $PSScriptRoot\..
python -m waitress --listen=0.0.0.0:8000 config.wsgi:application
