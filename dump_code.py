import os
import glob

# Ruta segura y absoluta a los artifacts del chat
output_file = r"C:\Users\edics\.gemini\antigravity\brain\4fec9202-d549-4734-aff3-bf838874b3c2\requested_code.md"

with open(output_file, "w", encoding="utf-8") as out:
    out.write("# ARCHIVOS Y CÓDIGO SOLICITADO\n\n")
    
    # 1. new_order_flow.py
    out.write("## 1. src/telegram_app/flows/new_order_flow.py\n```python\n")
    try:
        with open("src/telegram_app/flows/new_order_flow.py", "r", encoding="utf-8") as f:
            out.write(f.read())
    except FileNotFoundError:
        out.write("Archivo no encontrado.")
    out.write("\n```\n\n")

    # 2. models.py
    out.write("## 2. src/db/models.py\n```python\n")
    try:
        with open("src/db/models.py", "r", encoding="utf-8") as f:
            out.write(f.read())
    except FileNotFoundError:
        out.write("Archivo no encontrado.")
    out.write("\n```\n\n")

    # 3. internal_rates.py
    out.write("## 3. src/api/internal_rates.py\n```python\n")
    try:
        with open("src/api/internal_rates.py", "r", encoding="utf-8") as f:
            out.write(f.read())
    except FileNotFoundError:
        out.write("Archivo no encontrado.")
    out.write("\n```\n\n")

    # 4. ls src/api/
    out.write("## 4. Archivos en src/api/\n```text\n")
    try:
        for item in os.listdir("src/api"):
            out.write(item + "\n")
    except FileNotFoundError:
        out.write("Directorio no encontrado.")
    out.write("```\n\n")

    # 5. ls src/telegram_app/handlers/
    out.write("## 5. Archivos en src/telegram_app/handlers/\n```text\n")
    try:
        for item in os.listdir("src/telegram_app/handlers"):
            out.write(item + "\n")
    except FileNotFoundError:
        out.write("Directorio no encontrado.")
    out.write("```\n\n")

    # 6. schema.sql
    out.write("## 6. Archivos SQL (Scripts de Migración y DB)\n")
    sql_files = glob.glob("scripts/*.sql") + glob.glob("*.sql")
    for sql_file in sql_files:
        out.write(f"### {sql_file}\n```sql\n")
        try:
            with open(sql_file, "r", encoding="utf-8") as f:
                out.write(f.read())
        except Exception as e:
            out.write(f"Error leyendo archivo: {e}")
        out.write("\n```\n\n")

print("Generado el archivo en:", output_file)
