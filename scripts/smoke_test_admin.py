import urllib.request
import urllib.error
import os
import sys

# Configuración
API_BASE = "https://apii-maxx-production.up.railway.app"
API_KEY = os.getenv("BACKOFFICE_API_KEY")

endpoints = [
    "/metrics/control-center",
    "/admin/metrics/vault",
    "/admin/metrics/treasury",
    "/admin/metrics/daily_snapshot?date=2026-03-26",
    "/admin/payment-methods",
    "/alerts/stuck-30m"
]

def run_smoke_tests():
    if not API_KEY:
        print("❌ ERROR: La variable de entorno BACKOFFICE_API_KEY no está definida.")
        print("Ejecución manual (Powershell):")
        print("$env:BACKOFFICE_API_KEY='tu_clave_aqui'; python scripts/smoke_test_admin.py")
        sys.exit(1)

    print(f"Iniciando Smoke Test contra: {API_BASE}")
    print("-" * 60)

    all_passed = True

    for endpoint in endpoints:
        url = f"{API_BASE}{endpoint}"
        req = urllib.request.Request(url)
        req.add_header("X-API-KEY", API_KEY)
        
        try:
            response = urllib.request.urlopen(req, timeout=10)
            status = response.getcode()
            print(f"✅ [OK]   {status} | {endpoint}")
        except urllib.error.HTTPError as e:
            status = e.code
            print(f"❌ [FAIL] {status} | {endpoint}")
            all_passed = False
        except Exception as e:
            print(f"❌ [FAIL] ERR | {endpoint} -> {str(e)}")
            all_passed = False

    print("-" * 60)
    if all_passed:
        print("🚀 RESULTADO: TODOS LOS ENDPOINTS PASARON (Smoke Test Exitoso)")
        sys.exit(0)
    else:
        print("⚠️ RESULTADO: ALGUNOS ENDPOINTS FALLARON (Revisar logs del servidor)")
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_tests()
