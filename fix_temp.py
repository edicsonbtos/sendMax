with open('backoffice_web/src/app/daily-close/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Modificar headers del CSV
content = content.replace(
    'const headers = [\'Pais\', \'Moneda\', \'Entradas\', \'Salidas\', \'Neto\', \'Pendientes_Verificando\', \'OK_Cerrar\', \'Cerrado\', \'Neto_Al_Cierre\', \'Nota_Cierre\'];',
    'const headers = [\'Pais\', \'Moneda\', \'Saldo_Inicial\', \'Entradas\', \'Salidas\', \'Neto\', \'Saldo_Final\', \'Pendientes_Verificando\', \'OK_Cerrar\', \'Cerrado\', \'Neto_Al_Cierre\', \'Nota_Cierre\'];'
)

# Modificar rows del CSV
old_csv_row = '''const rows = report.map((r) => [
      sanitizeCSV(r.origin_country),
      sanitizeCSV(r.fiat_currency),
      formatMoneyCSV(r.in_amount, r.fiat_currency),
      formatMoneyCSV(r.out_amount, r.fiat_currency),
      formatMoneyCSV(r.net_amount, r.fiat_currency),
      String(r.pending_origin_verificando_count),
      r.ok_to_close ? 'SI' : 'NO',
      r.closed ? 'SI' : 'NO',
      r.net_amount_at_close != null ? formatMoneyCSV(r.net_amount_at_close, r.fiat_currency) : '',
      sanitizeCSV(r.close_note),
    ]);'''

new_csv_row = '''const rows = report.map((r) => {
      const bal = balances.find(b => b.origin_country === r.origin_country && b.fiat_currency === r.fiat_currency);
      return [
        sanitizeCSV(r.origin_country),
        sanitizeCSV(r.fiat_currency),
        bal ? formatMoneyCSV(bal.opening_balance, r.fiat_currency) : '0',
        formatMoneyCSV(r.in_amount, r.fiat_currency),
        formatMoneyCSV(r.out_amount, r.fiat_currency),
        formatMoneyCSV(r.net_amount, r.fiat_currency),
        bal ? formatMoneyCSV(bal.current_balance, r.fiat_currency) : '0',
        String(r.pending_origin_verificando_count),
        r.ok_to_close ? 'SI' : 'NO',
        r.closed ? 'SI' : 'NO',
        r.net_amount_at_close != null ? formatMoneyCSV(r.net_amount_at_close, r.fiat_currency) : '',
        sanitizeCSV(r.close_note),
      ];
    });'''

content = content.replace(old_csv_row, new_csv_row)

with open('backoffice_web/src/app/daily-close/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK 5 - daily-close: CSV con saldos de apertura/cierre")
