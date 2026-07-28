from functools import wraps
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.database import db
from app.models.edugest import EdugestModule, EdugestRolePermission  # ← NUEVO al inicio

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

login_manager = LoginManager()


def init_login_manager(app):
    """Inicializa Flask-Login en la aplicacion."""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesion para acceder.'
    login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    from app.models.edugest import EdugestUser
    return EdugestUser.query.get(int(user_id))


# ============================================================================
# HELPERS DE SEGURIDAD
# ============================================================================
def _es_url_segura(url):
    """Verifica que la URL sea relativa (misma aplicacion). Evita open redirect."""
    if not url:
        return False
    parsed = urlparse(url)
    return not parsed.scheme and not parsed.netloc


def _redirect_por_rol(usuario):
    """Retorna la URL de redireccion segun el RoleId del usuario."""
    if usuario.RoleId == 1:
        return url_for('admin.dashboard')
    elif usuario.RoleId == 3:
        return url_for('libro_digital.listar_grados')
    else:
        return url_for('portada.bienvenida')


# ============================================================================
# DECORADOR DE PERMISOS POR MODULO
# ============================================================================
def permiso_requerido(module_name, nivel=1):
    """
    Decorador que verifica si el usuario tiene acceso a un modulo.
    nivel 1 = Lectura, nivel 2 = Escritura
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            # Admin (RoleId=1) tiene acceso total sin verificar permisos
            if current_user.RoleId == 1:
                return f(*args, **kwargs)

            # ← ELIMINADO: import inline (ya está al inicio del archivo)

            modulo = EdugestModule.query.filter_by(ModuleName=module_name).first()
            if not modulo:
                return render_template('auth/unauthorized.html',
                                       mensaje=f'El modulo "{module_name}" no existe.'), 403

            permiso = EdugestRolePermission.query.filter_by(
                RoleId=current_user.RoleId,
                ModuleId=modulo.ModuleId
            ).first()

            if not permiso or permiso.PermissionLevel < nivel:
                return render_template('auth/unauthorized.html',
                                       mensaje=f'No tienes permisos para acceder a "{module_name}".'), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def verificar_escritura(module_name):
    """
    Funcion helper para verificar permisos de escritura (nivel 2).
    Usar dentro de rutas mixtas GET/POST cuando solo el POST requiere nivel 2.
    Lanza 403 si el usuario no tiene permiso.
    """
    if current_user.RoleId == 1:
        return  # Admin tiene acceso total

    # ← ELIMINADO: import inline (ya está al inicio del archivo)

    modulo = EdugestModule.query.filter_by(ModuleName=module_name).first()
    if not modulo:
        abort(403)

    permiso = EdugestRolePermission.query.filter_by(
        RoleId=current_user.RoleId,
        ModuleId=modulo.ModuleId
    ).first()

    if not permiso or permiso.PermissionLevel < 2:
        abort(403)


# ============================================================================
# RUTAS DE AUTENTICACION (sin cambios)
# ============================================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_redirect_por_rol(current_user))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Debes ingresar RUT y contrasena.', 'error')
            return render_template('auth/login.html')

        from app.models.edugest import EdugestUser

        usuario = EdugestUser.query.filter_by(Username=username, IsActive=True).first()

        if not usuario or not check_password_hash(usuario.PasswordHash, password):
            flash('RUT o contrasena incorrectos.', 'error')
            return render_template('auth/login.html')

        remember = True if request.form.get('remember') else False
        login_user(usuario, remember=remember)

        next_page = request.args.get('next')
        if next_page and _es_url_segura(next_page):
            return redirect(next_page)

        return redirect(_redirect_por_rol(usuario))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesion cerrada correctamente.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/usuarios')
@login_required
def listar_usuarios():
    if current_user.RoleId != 1:
        flash('No tienes permisos para acceder a esta seccion.', 'error')
        return redirect(url_for('portada.bienvenida'))

    from app.models.edugest import EdugestUser
    from app.models.mineduc import Person
    from sqlalchemy.orm import joinedload

    usuarios = EdugestUser.query.options(
        joinedload(EdugestUser.person)
    ).all()

    usuarios_data = []
    for u in usuarios:
        usuarios_data.append({
            'usuario': u,
            'persona': u.person
        })

    return render_template('auth/usuarios.html', usuarios=usuarios_data)