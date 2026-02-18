# Leer .env actual
$content = Get-Content ".env" -Encoding utf8

# Verificar si ya existe BACKOFFICE_API_KEY
if ($content -notmatch "BACKOFFICE_API_KEY") {
    # Generar key aleatoria segura
    $randomKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    
    # Agregar al .env
    Add-Content ".env" -Value "
BACKOFFICE_API_KEY=$randomKey" -Encoding utf8
    
    Write-Host "✅ BACKOFFICE_API_KEY agregada: $randomKey" -ForegroundColor Green
} else {
    Write-Host "✅ BACKOFFICE_API_KEY ya existe" -ForegroundColor Yellow
}
