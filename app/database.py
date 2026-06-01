import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import Engine
from sqlalchemy import event

# Instancia global del ORM
db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Gancho de SQLAlchemy que intercepta cada conexión a la base de datos.
    Fuerza a SQLite a respetar de forma estricta las restricciones FOREIGN KEY.
    """
    # Verificamos el tipo de conexión por si en el futuro migras a otro motor (ej: PostgreSQL)
    if dbapi_connection.__class__.__name__ == 'Connection' or 'sqlite' in str(type(dbapi_connection)).lower():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.close()

def init_db(app):
    """
    Inicializa la base de datos vinculándola a la app de Flask
    y asegura que exista la carpeta 'instance/' física.
    """
    # Flask-SQLAlchemy requiere que la carpeta 'instance' exista antes de conectarse
    os.makedirs(app.instance_path, exist_ok=True)
    
    db.init_app(app)