import sqlite3
import os

db_path = os.path.join('instance', 'edugest.db')

print("🛠️ Agregando columna de fecha CreatedAt...")

try:
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()
    
    # Eliminamos el DEFAULT CURRENT_TIMESTAMP para respetar la regla de SQLite
    query = "ALTER TABLE edugest_curriculum_plan ADD COLUMN CreatedAt DATETIME;"
    
    try:
        cursor.execute(query)
        print("✅ Columna 'CreatedAt' agregada con éxito.")
    except sqlite3.OperationalError as e:
        print(f"⚠️ La columna ya existe o hubo un detalle: {e}")

    conexion.commit()
    conexion.close()
    
except Exception as e:
    print(f"❌ Error al conectar con la base de datos: {e}")