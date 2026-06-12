from flask import Flask, redirect, url_for
from app.config import Config
from app.database import db, init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar la extensión db vinculándola a la app
    init_db(app)

    # Forzar la creación de tablas dentro del contexto de Flask si no existen
    with app.app_context():
        from app import models
        db.create_all()

        # SEMILLA AUTOMÁTICA: Si la tabla de módulos está vacía, creamos los registros iniciales
        from app.models.edugest import EdugestModule
        if not EdugestModule.query.first():
            modulos_iniciales = [
                EdugestModule(ModuleName="Libro Digital", IsEnabled=True),
                EdugestModule(ModuleName="Evaluaciones", IsEnabled=True),
                EdugestModule(ModuleName="Biblioteca CRA", IsEnabled=True),
                EdugestModule(ModuleName="Comunicaciones", IsEnabled=True)
            ]
            db.session.add_all(modulos_iniciales)
            db.session.commit()

    # ==========================================
    # REGISTRO ÚNICO DE BLUEPRINTS
    # ==========================================
    
    # 1. Módulo de Administración
    from app.modules.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    # 2. Módulo de Libro Digital
    from app.modules.libro_digital.routes import libro_digital_bp
    app.register_blueprint(libro_digital_bp)

    # 3. Módulo de Evaluaciones (Agregado)
    from app.modules.evaluaciones.routes import evaluaciones_bp
    app.register_blueprint(evaluaciones_bp)

    # 4. Módulo de Matrícula
    from app.modules.matricula.routes import matricula_bp
    app.register_blueprint(matricula_bp)

    # 5. Módulo de Biblioteca (CRA)
    from app.modules.biblioteca import biblioteca_bp
    app.register_blueprint(biblioteca_bp)
    
    # 6. Módulo de Comunicaciones
    from app.modules.comunicacion.routes import comunicacion_bp
    app.register_blueprint(comunicacion_bp)

    # 7. Módulo de Reportes
    from app.modules.reportes.routes import reportes_bp
    app.register_blueprint(reportes_bp)

    # Redirección de la raíz al panel de administración por defecto
    @app.route('/')
    def index():
        return redirect(url_for('admin.dashboard'))

    # Filtro Jinja para transformar índices (0, 1, 2, 3) en letras (A, B, C, D)
    @app.template_filter('tochar')
    def tochar(number):
        return chr(65 + number) # 65 es el código ASCII para la letra 'A'
    return app