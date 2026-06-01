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

    # REGISTRO DE BLUEPRINTS
    from app.modules.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    from app.modules.libro_digital.routes import libro_digital_bp
    app.register_blueprint(libro_digital_bp)

    # Redirección de conveniencia: Al entrar a '/' nos manda directo al módulo funcional
    @app.route('/')
    def health_check():
        return redirect(url_for('admin.dashboard'))

    return app