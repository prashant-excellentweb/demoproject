# Start ChatApp backend on port 9000
Set-Location $PSScriptRoot\backend
if (-not (Test-Path .\venv\Scripts\activate.ps1)) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    .\venv\Scripts\pip install -r requirements.txt
}
.\venv\Scripts\activate.ps1
python manage.py migrate --noinput
Write-Host "Backend starting at http://localhost:9000"
Write-Host "Swagger UI: http://localhost:9000/api/docs/"
daphne -b 127.0.0.1 -p 9000 config.asgi:application
