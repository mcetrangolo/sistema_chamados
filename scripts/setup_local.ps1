Set-Location -Path $PSScriptRoot\..
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_chamados
python manage.py collectstatic --noinput
python manage.py check
