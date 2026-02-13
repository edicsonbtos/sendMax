import psycopg, json
conn = psycopg.connect('postgresql://neondb_owner:npg_8Eqh0xcTGVXQ@ep-damp-wave-ahgz5qnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require')
cur = conn.cursor()

cur.execute("SELECT key, value_json, updated_at FROM settings ORDER BY key")
print("=== SETTINGS ACTUALES ===")
for r in cur.fetchall():
    val = json.dumps(r[1], indent=2) if isinstance(r[1], dict) else str(r[1])
    print(f"\n--- {r[0]} --- (updated: {r[2]})")
    print(f"  {val}")

# Verificar permisos
cur.execute("SELECT privilege_type FROM information_schema.table_privileges WHERE table_name='settings' AND grantee='backoffice_rw' ORDER BY 1")
perms = [r[0] for r in cur.fetchall()]
print(f"\n=== PERMISOS backoffice_rw en settings: {', '.join(perms) if perms else 'SIN PERMISOS'} ===")

cur.execute("SELECT privilege_type FROM information_schema.table_privileges WHERE table_name='audit_log' AND grantee='backoffice_rw' ORDER BY 1")
perms2 = [r[0] for r in cur.fetchall()]
print(f"=== PERMISOS backoffice_rw en audit_log: {', '.join(perms2) if perms2 else 'SIN PERMISOS'} ===")

# Otorgar si faltan
if not perms or not perms2:
    print("\nOtorgando permisos...")
    cur.execute("GRANT SELECT, INSERT, UPDATE ON settings TO backoffice_rw")
    cur.execute("GRANT SELECT, INSERT ON audit_log TO backoffice_rw")
    conn.commit()
    print("Permisos otorgados!")

conn.close()
