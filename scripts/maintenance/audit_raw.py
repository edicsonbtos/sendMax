import psycopg
from decimal import Decimal
from src.config.settings import settings

def audit_raw_data():
    print("\n🔍 --- AUDITORÍA DE DATOS CRUDOS (Últimas 5 Órdenes) ---\n")
    
    query = """
        SELECT 
            public_id, 
            origin_country, 
            amount_origin, 
            commission_pct,
            status,
            created_at
        FROM orders 
        ORDER BY created_at DESC 
        LIMIT 5;
    """
    
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            
            if not rows:
                print("❌ No hay órdenes en la base de datos.")
                return

            print(f"{'ID':<5} | {'PAÍS':<10} | {'MONTO GUARDADO (amount_origin)':<30} | {'COMISIÓN':<10}")
            print("-" * 65)
            
            for row in rows:
                pid, country, amount, comm, status, date = row
                
                # Análisis en vivo
                print(f"#{pid:<4} | {country:<10} | {amount:<30} | {comm}%")
                
                # Alerta visual si el monto parece Fiat (muy grande)
                if amount > 500:
                    print(f"      ⚠️ ¡ALERTA! Este monto parece FIAT, no USDT.")
                    print(f"      🧮 Cálculo Bot: {amount} * {comm}% = {amount * (comm/Decimal(100))} USDT de ganancia (¡ERROR!)")
                else:
                    print(f"      ✅ Este monto parece USDT real.")
                print("-" * 65)

if __name__ == "__main__":
    try:
        audit_raw_data()
    except Exception as e:
        print(f"Error conectando a DB: {e}")
