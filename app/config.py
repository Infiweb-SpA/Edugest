import os

# Obtiene la ruta absoluta de la raíz del proyecto (C:/TuProyectoEdugest/)
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    # Clave secreta para sesiones y tokens (usa variables de entorno en producción)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'edugest_secret_key_temuco_2026')
    
    # Configuración de la ruta física para la base de datos SQLite
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'edugest.db')}"
    
    # Desactiva el sistema de modificaciones de SQLAlchemy para ahorrar recursos
    SQLALCHEMY_TRACK_MODIFICATIONS = False