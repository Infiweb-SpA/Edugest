from flask import Flask, redirect, url_for
from app.config import Config
from app.database import db, init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializar db
    init_db(app)

    with app.app_context():
        from app import models
        db.create_all()

        # Semilla automática de módulos
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
    # INICIALIZAR FLASK-LOGIN
    # ==========================================
    from app.modules.auth.routes import init_login_manager
    init_login_manager(app)

    # ==========================================
    # REGISTRO DE BLUEPRINTS
    # ==========================================

    # 0. Autenticación (PRIMERO)
    from app.modules.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    # 1. Administración
    from app.modules.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    # 2. Libro Digital
    from app.modules.libro_digital.routes import libro_digital_bp
    app.register_blueprint(libro_digital_bp)

    # 3. Evaluaciones
    from app.modules.evaluaciones.routes import evaluaciones_bp
    app.register_blueprint(evaluaciones_bp)

    # 4. Matrícula
    from app.modules.matricula.routes import matricula_bp
    app.register_blueprint(matricula_bp)

    # 5. Biblioteca (CRA)
    from app.modules.biblioteca import biblioteca_bp
    app.register_blueprint(biblioteca_bp)

    # 6. Comunicaciones
    from app.modules.comunicacion.routes import comunicacion_bp
    app.register_blueprint(comunicacion_bp)

    # 7. Reportes
    from app.modules.reportes.routes import reportes_bp
    app.register_blueprint(reportes_bp)

    # ==========================================
    # RUTA RAÍZ → REDIRIGIR AL LOGIN
    # ==========================================
    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('auth.login'))

    # Filtro Jinja
    @app.template_filter('tochar')
    def tochar(number):
        return chr(65 + number)

    return app