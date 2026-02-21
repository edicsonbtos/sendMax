# ============================================================
# SENDMAX — AUDITORÍA INTEGRAL FINAL (FASES 2 & 3) v2
# - Reporta SIEMPRE OK/WARN en cada sección
# - Copia reporte a clipboard (clip)
# Ejecutar desde la raíz del repo
# ============================================================

$ErrorActionPreference = "Stop"
$report = ""

function Add($s){ $script:report += $s + "`r`n" }
function Sec($s){ Add("`r`n=== $s ===") }
function OK($s){ Add("[OK]   $s") }
function WARN($s){ Add("[WARN] $s") }
function FAIL($s){ Add("[FAIL] $s") }

Sec "AUDITORÍA INTEGRAL SENDMAX: FASES 2 & 3 (FINAL v2)"
Add("Time: " + (Get-Date).ToString("s"))
Add("PWD : " + (Get-Location).Path)

if (!(Test-Path ".git")) { FAIL "No estás en la raíz del repo (.git no existe aquí)."; $report | clip; throw "No repo root" }

# 1) Sync
Sec "1/5 Git sync"
git fetch origin main | Out-Null
$local = (git rev-parse --short HEAD).Trim()
$remote = (git rev-parse --short origin/main).Trim()
Add("local  : $local")
Add("remote : $remote")
if ($local -eq $remote) { OK "PC y GitHub sincronizados" } else { WARN "PC NO sincronizado. Ejecuta: git pull origin main" }

# 2) Fase 2 (pool + FastAPI)
Sec "2/5 Fase 2 - Engine/DB"

$pool = Select-String -Path "src\db\connection.py" -Pattern "ConnectionPool|psycopg_pool" -Quiet -ErrorAction SilentlyContinue
$asyncPool = Select-String -Path "src\db\connection.py" -Pattern "AsyncConnectionPool" -Quiet -ErrorAction SilentlyContinue
$fastapiBot = Select-String -Path "src\main.py" -Pattern "\bFastAPI\b" -Quiet -ErrorAction SilentlyContinue
$fastapiApi = Select-String -Path "backoffice_api\app\main.py" -Pattern "\bFastAPI\b" -Quiet -ErrorAction SilentlyContinue

if ($pool) { OK "DB Pool detectado (ConnectionPool/psycopg_pool) en src/db/connection.py" } else { WARN "No detecté ConnectionPool/psycopg_pool en src/db/connection.py" }
if ($asyncPool) { OK "AsyncConnectionPool detectado (concurrencia mejorada)" } else { WARN "No detecté AsyncConnectionPool (no siempre aplica)" }

if (Test-Path "src\main.py") {
  if ($fastapiBot) { OK "src/main.py menciona FastAPI (webhook server / app server)" } else { WARN "src/main.py no menciona FastAPI" }
} else { WARN "No existe src/main.py" }

if (Test-Path "backoffice_api\app\main.py") {
  if ($fastapiApi) { OK "Backoffice API FastAPI detectado" } else { WARN "No detecté FastAPI en backoffice_api/app/main.py" }
} else { WARN "No existe backoffice_api/app/main.py" }

# 3) Fase 3 (guardrails comprobante)
Sec "3/5 Fase 3 - UX Guardrails (comprobante foto/documento)"

$flowFile = "src\telegram_app\flows\new_order_flow.py"
if (!(Test-Path $flowFile)) {
  FAIL "No existe src/telegram_app/flows/new_order_flow.py"
} else {
  $docHandler = Select-String -Path $flowFile -Pattern "filters\.Document\.ALL|MessageHandler\(filters\.Document" -Quiet -ErrorAction SilentlyContinue
  $docLogic = Select-String -Path $flowFile -Pattern "update\.message\.document|file_id = None|Envía el comprobante como foto o archivo" -Quiet -ErrorAction SilentlyContinue

  if ($docHandler -and $docLogic) {
    OK "Guardrails OK: acepta PHOTO + DOCUMENT y guía al usuario si falta file_id"
  } else {
    WARN "Guardrails incompletos: revisa ASK_PROOF handlers y receive_proof()"
  }
}

# 4) Fase 3 (admin awaiting/idempotencia)
Sec "4/5 Fase 3 - Admin awaiting/idempotencia (operador)"

$adminFile = "src\telegram_app\handlers\admin_orders.py"
if (!(Test-Path $adminFile)) {
  FAIL "No existe src/telegram_app/handlers/admin_orders.py"
} else {
  $awaitingBy = Select-String -Path $adminFile -Pattern "awaiting_paid_proof_by|list_orders_awaiting_paid_proof_by" -Quiet -ErrorAction SilentlyContinue
  $onePending = Select-String -Path $adminFile -Pattern "Ya tienes una orden en espera" -Quiet -ErrorAction SilentlyContinue

  if ($awaitingBy) { OK "awaiting_paid_proof_by OK: aislamiento por operador presente" } else { WARN "No detecté awaiting_paid_proof_by / list_orders_awaiting_paid_proof_by" }
  if ($onePending) { OK "Candado 1 pendiente por operador OK" } else { WARN "No detecté candado 1 pendiente por operador" }
}

# 5) Calidad visual (encoding)
Sec "5/5 Calidad - Ruido visual (?? / �)"
$noise = Select-String -Path "src\**\*.py" -Pattern "�|\?\?" -AllMatches -ErrorAction SilentlyContinue |
  Select-Object -First 10 Path,LineNumber,Line

if ($noise) {
  WARN "Se detectó posible ruido visual (muestra top 10):"
  $noise | ForEach-Object { Add(("  - {0}:{1} {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim())) }
} else {
  OK "Sin ruido visual detectado (� o ??)"
}

Sec "FIN"
Add("Reporte copiado al portapapeles (clip).")

$report | clip
Write-Host "AUDITORÍA FINAL v2 completada -> reporte en clipboard." -ForegroundColor Green
