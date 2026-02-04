import sys
from decimal import Decimal
from src.db.repositories.orders_repo import get_order_by_public_id

def audit(public_id):
    print(f"\n🔍 --- AUDITORÍA DE ORDEN #{public_id} ---\n")
    
    order = get_order_by_public_id(public_id)
    
    if not order:
        print(f"❌ La orden #{public_id} NO existe en la base de datos.")
        return

    print(f"🌍 Ruta: {order.origin_country} -> {order.dest_country}")
    print(f"👤 Operador ID: {order.operator_user_id}")
    print(f"📊 Estado: {order.status}")
    print("-" * 30)
    
    # Valores Crudos
    amount = order.amount_origin
    pct = order.commission_pct
    
    print(f"💰 Monto Origen: {amount} USDT")
    print(f"📈 Comisión Configurada: {pct} %")
    
    # Recálculo en vivo
    calc_profit = amount * (pct / Decimal("100"))
    
    print("-" * 30)
    print(f"🧮 CÁLCULO DE GANANCIA:")
    print(f"   {amount} * ({pct} / 100)")
    print(f"   = {amount} * {pct/Decimal('100')}")
    print(f"   = {calc_profit} USDT (Ganancia Teórica)")
    
    print("-" * 30)
    # Ver si hay profit guardado en la orden (si la columna existe en tu modelo dataclass)
    if hasattr(order, 'profit_usdt'):
        print(f"💾 Ganancia Guardada en DB: {order.profit_usdt} USDT")
    else:
        print("⚠️ El campo 'profit_usdt' no aparece en el dataclass actual (quizás se guarda directo en ledger).")

if __name__ == "__main__":
    try:
        audit(19)
    except Exception as e:
        print(f"Error: {e}")
