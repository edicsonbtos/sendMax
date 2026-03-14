import os
import bcrypt
import psycopg2
import sys

# Ensure imports from root work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set.")
        return

    password = "Vdurbina26"
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    hash_str = hashed.decode('utf-8')
    print(f"Hash generado: {hash_str}")

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check current details (backup)
        cur.execute("SELECT id, alias, email, hashed_password, kyc_status FROM users WHERE id = 25;")
        old_data = cur.fetchone()
        if old_data:
            print("Datos antiguos:", old_data)
        
        # Execute UPDATE
        sql = "UPDATE users SET email = %s, hashed_password = %s WHERE id = 25;"
        print(f"Comando SQL a ejecutar: UPDATE users SET email='vdurbina.1993@gmail.com', hashed_password='{hash_str}' WHERE id=25;")
        cur.execute(sql, ('vdurbina.1993@gmail.com', hash_str))
        conn.commit()
        print(f"Resultado: UPDATE {cur.rowcount}")

        # Verification
        cur.execute("SELECT id, alias, email, kyc_status FROM users WHERE id = 25;")
        new_data = cur.fetchone()
        
        print("\nVerificación:")
        print("┌────┬───────────────┬───────────────────────────┬──────────────┐")
        print("│ id │ alias         │ email                     │ kyc_status   │")
        print("├────┼───────────────┼───────────────────────────┼──────────────┤")
        if new_data:
            print(f"│ {new_data[0]:<2} │ {new_data[1]:<13} │ {new_data[2]:<25} │ {new_data[3]:<12} │")
        print("└────┴───────────────┴───────────────────────────┴──────────────┘")

        cur.close()
        conn.close()
    except Exception as e:
        print("Database error:", e)

if __name__ == '__main__':
    main()
