import sqlite3
import os

# Rutas a los archivos
db_path = os.path.join('instance', 'edugest.db')
sql_path = 'migration_v2.sql'

print("Iniciando migración de base de datos...")

try:
    # Conectar a SQLite
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()
    
    # Leer el archivo SQL
    with open(sql_path, 'r', encoding='utf-8') as archivo_sql:
        script_sql = archivo_sql.read()
        
    # Ejecutar el script completo
    cursor.executescript(script_sql)
    conexion.commit()
    conexion.close()
    
    print("✅ Migración V2 aplicada con éxito. Las nuevas tablas ya existen en edugest.db")
    
except Exception as e:
    print(f"❌ Error al aplicar la migración: {e}")