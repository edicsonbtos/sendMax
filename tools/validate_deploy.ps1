# Validate Sendmax Deployment Syntax and Imports

function Check-PythonFile($path) {
    Write-Host "Checking $path ..." -ForegroundColor Cyan
    python -m py_compile $path
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Syntax error in $path"
        exit 1
    }
}

Write-Host "=== FASE 1: Sintaxis ===" -ForegroundColor Yellow
$files = Get-ChildItem -Recurse -Filter "*.py" | Where-Object { $_.FullName -notlike "*__pycache__*" }
foreach ($f in $files) {
    Check-PythonFile $f.FullName
}

Write-Host "`n=== FASE 2: Imports ===" -ForegroundColor Yellow
Write-Host "Verificando imports de Bot..."
python -c "import src.main; print('Bot imports OK')"
if ($LASTEXITCODE -ne 0) { Write-Error "Bot imports FAILED"; exit 1 }

Write-Host "Verificando imports de API..."
$env:PYTHONPATH = "."
$env:SECRET_KEY = "validation_only"
python -c "import backoffice_api.app.main; print('API imports OK')"
if ($LASTEXITCODE -ne 0) { Write-Error "API imports FAILED"; exit 1 }

Write-Host "`n=== VALIDACION EXITOSA ===" -ForegroundColor Green
