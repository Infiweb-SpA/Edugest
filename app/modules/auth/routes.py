from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.database import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

login_manager = LoginManager()


def init_login_manager(app):
    """Inicializa Flask-Login en la aplicación."""
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder.'
    login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    from app.models.edugest import EdugestUser
    return EdugestUser.query.get(int(user_id))


# ============================================================================
# DECORADOR DE PERMISOS POR MÓDULO
# ============================================================================
def permiso_requerido(module_name, nivel=1):
    """
    Decorador que verifica si el usuario tiene acceso a un módulo.
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

            from app.models.edugest import EdugestModule, EdugestRolePermission

            modulo = EdugestModule.query.filter_by(ModuleName=module_name).first()
            if not modulo:
                return render_template('auth/unauthorized.html',
                                       mensaje=f'El módulo "{module_name}" no existe.'), 403

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


# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Debes ingresar RUT y contraseña.', 'error')
            return render_template('auth/login.html')

        from app.models.edugest import EdugestUser

        usuario = EdugestUser.query.filter_by(Username=username, IsActive=True).first()

        if not usuario or not check_password_hash(usuario.PasswordHash, password):
            flash('RUT o contraseña incorrectos.', 'error')
            return render_template('auth/login.html')

        login_user(usuario, remember=True)

        # Redirigir según el rol
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if usuario.RoleId == 1:
            return redirect(url_for('admin.dashboard'))
        elif usuario.RoleId == 3:
            return redirect(url_for('libro_digital.listar_grados'))
        elif usuario.RoleId == 6:
            return redirect(url_for('reportes.index'))
        else:
            return redirect(url_for('admin.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('auth.login'))


# ============================================================================
# RUTA: GESTIÓN DE USUARIOS (solo admin)
# ============================================================================
@auth_bp.route('/usuarios')
@login_required
def listar_usuarios():
    if current_user.RoleId != 1:
        return render_template('auth/unauthorized.html',
                               mensaje='Solo los administradores pueden gestionar usuarios.'), 403

    from app.models.edugest import EdugestUser
    from app.models.mineduc import Person

    usuarios = EdugestUser.query.all()
    usuarios_data = []
    for u in usuarios:
        persona = Person.query.get(u.PersonId)
        usuarios_data.append({
            'usuario': u,
            'persona': persona
        })

    return render_template('auth/usuarios.html', usuarios=usuarios_data)