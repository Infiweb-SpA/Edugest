from flask import Flask, redirect, url_for
from flask_wtf.csrf import CSRFProtect  # ← NUEVO
from app.config import Config
from app.database import db, init_db

csrf = CSRFProtect()  # ← NUEVO: Instancia global de CSRF


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ← NUEVO: Verificar que SECRET_KEY exista y no esté vacía
    if not app.config.get('SECRET_KEY'):
        import os
        app.config['SECRET_KEY'] = os.environ.get(
            'SECRET_KEY', 'cambiar-esta-clave-en-produccion'
        )

    # Inicializar db
    init_db(app)

    # ← NUEVO: Inicializar CSRF después de configurar la app
    csrf.init_app(app)

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
                EdugestModule(ModuleName="Comunicaciones", IsEnabled=True),
                EdugestModule(ModuleName="Calendario", IsEnabled=True),
                EdugestModule(ModuleName="Matrícula", IsEnabled=True),
                EdugestModule(ModuleName="Reportes", IsEnabled=True),
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

    # 0b. Gestión de Usuarios
    from app.modules.gestion_usuarios.routes import gestion_usuarios_bp
    app.register_blueprint(gestion_usuarios_bp)

    # 0c. Gestión de Roles
    from app.modules.gestion_roles.routes import gestion_roles_bp
    app.register_blueprint(gestion_roles_bp)

    # 0d. Portada / Bienvenida
    from app.modules.portada.routes import portada_bp
    app.register_blueprint(portada_bp)

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

    # 8. Calendario Académico
    from app.modules.calendario import calendario_bp
    app.register_blueprint(calendario_bp)

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

    # ==========================================
    # CONTEXTO GLOBAL: Permisos del usuario actual
    # ==========================================
    @app.context_processor
    def injectar_permisos():
        from flask_login import current_user
        from app.models.edugest import EdugestModule, EdugestRolePermission, EdugestRole

        permisos = {}
        rol_nombre = None

        if current_user.is_authenticated:
            # Obtener nombre del rol
            rol = EdugestRole.query.get(current_user.RoleId)
            rol_nombre = rol.RoleName if rol else 'Usuario'

            if current_user.RoleId == 1:
                modulos = EdugestModule.query.all()
                for m in modulos:
                    permisos[m.ModuleName] = 2
            else:
                registros = db.session.query(
                    EdugestModule.ModuleName,
                    EdugestRolePermission.PermissionLevel
                ).join(
                    EdugestRolePermission,
                    EdugestModule.ModuleId == EdugestRolePermission.ModuleId
                ).filter(
                    EdugestRolePermission.RoleId == current_user.RoleId
                ).all()

                for nombre, nivel in registros:
                    permisos[nombre] = nivel

        return dict(user_permisos=permisos, user_rol_nombre=rol_nombre)

    return app