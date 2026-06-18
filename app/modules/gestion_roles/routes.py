from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.database import db
from app.models.edugest import EdugestRolePermission, EdugestModule, EdugestUser, EdugestRole

gestion_roles_bp = Blueprint('gestion_roles', __name__, url_prefix='/gestion-roles')


def _admin_required():
    return current_user.is_authenticated and current_user.RoleId == 1


def _obtener_nombre_rol(role_id):
    """Obtiene el nombre del rol desde la BD. Si no existe, devuelve texto genérico."""
    rol = EdugestRole.query.get(role_id)
    return rol.RoleName if rol else f'Rol {role_id}'


# ============================================================================
# LISTAR ROLES
# ============================================================================
@gestion_roles_bp.route('/')
@login_required
def listar():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Obtener todos los roles desde la BD
    todos_los_roles = EdugestRole.query.order_by(EdugestRole.RoleId).all()

    # También buscar RoleIds que existen en usuarios pero NO en EdugestRole
    roles_ids_usuarios = set(r[0] for r in db.session.query(EdugestUser.RoleId).distinct().all())
    roles_ids_bd = set(r.RoleId for r in todos_los_roles)
    roles_huerfanos = roles_ids_usuarios - roles_ids_bd

    roles_data = []
    for rol in todos_los_roles:
        total_usuarios = EdugestUser.query.filter_by(RoleId=rol.RoleId).count()
        permisos = EdugestRolePermission.query.filter_by(RoleId=rol.RoleId).all()
        permisos_activos = sum(1 for p in permisos if p.PermissionLevel > 0)
        total_modulos = EdugestModule.query.count()

        roles_data.append({
            'role_id': rol.RoleId,
            'nombre': rol.RoleName,
            'total_usuarios': total_usuarios,
            'permisos_activos': permisos_activos,
            'total_modulos': total_modulos
        })

    # Agregar roles huérfanos (existen en usuarios pero no en catálogo)
    for role_id in sorted(roles_huerfanos):
        total_usuarios = EdugestUser.query.filter_by(RoleId=role_id).count()
        permisos = EdugestRolePermission.query.filter_by(RoleId=role_id).all()
        permisos_activos = sum(1 for p in permisos if p.PermissionLevel > 0)
        total_modulos = EdugestModule.query.count()

        roles_data.append({
            'role_id': role_id,
            'nombre': f'Rol {role_id} (sin catálogo)',
            'total_usuarios': total_usuarios,
            'permisos_activos': permisos_activos,
            'total_modulos': total_modulos
        })

    return render_template('gestion_roles/listar.html', roles=roles_data)


# ============================================================================
# EDITAR PERMISOS DE UN ROL
# ============================================================================
@gestion_roles_bp.route('/<int:role_id>/permisos', methods=['GET', 'POST'])
@login_required
def editar_permisos(role_id):
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    rol_nombre = _obtener_nombre_rol(role_id)
    modulos = EdugestModule.query.order_by(EdugestModule.ModuleName).all()

    if request.method == 'POST':
        EdugestRolePermission.query.filter_by(RoleId=role_id).delete()

        for modulo in modulos:
            nivel = int(request.form.get(f'permiso_{modulo.ModuleId}', 0))
            db.session.add(EdugestRolePermission(
                RoleId=role_id,
                ModuleId=modulo.ModuleId,
                PermissionLevel=nivel
            ))

        db.session.commit()
        flash(f'Permisos del rol "{rol_nombre}" actualizados correctamente.', 'success')
        return redirect(url_for('gestion_roles.listar'))

    permisos_actuales = {}
    for p in EdugestRolePermission.query.filter_by(RoleId=role_id).all():
        permisos_actuales[p.ModuleId] = p.PermissionLevel

    modulos_data = []
    for m in modulos:
        modulos_data.append({
            'modulo': m,
            'nivel': permisos_actuales.get(m.ModuleId, 0)
        })

    total_usuarios = EdugestUser.query.filter_by(RoleId=role_id).count()

    return render_template('gestion_roles/editar_permisos.html',
                           role_id=role_id,
                           rol_nombre=rol_nombre,
                           modulos_data=modulos_data,
                           total_usuarios=total_usuarios)


# ============================================================================
# CREAR NUEVO ROL
# ============================================================================
@gestion_roles_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def crear_rol():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        role_id = request.form.get('role_id', type=int)
        nombre = request.form.get('nombre', '').strip()

        if not role_id or not nombre:
            flash('Debes indicar el ID numérico y el nombre del rol.', 'error')
            return render_template('gestion_roles/nuevo_rol.html')

        # Verificar que el ID no exista en el catálogo
        if EdugestRole.query.get(role_id):
            flash(f'Ya existe un rol con ID {role_id}. Elige otro.', 'error')
            return render_template('gestion_roles/nuevo_rol.html')

        # Crear el rol en el catálogo
        nuevo_rol = EdugestRole(
            RoleId=role_id,
            RoleName=nombre
        )
        db.session.add(nuevo_rol)

        # Crear permisos vacíos para todos los módulos
        modulos = EdugestModule.query.all()
        for m in modulos:
            db.session.add(EdugestRolePermission(
                RoleId=role_id,
                ModuleId=m.ModuleId,
                PermissionLevel=0
            ))
        db.session.commit()

        flash(f'Rol "{nombre}" (ID: {role_id}) creado. Ahora asigna sus permisos.', 'success')
        return redirect(url_for('gestion_roles.editar_permisos', role_id=role_id))

    return render_template('gestion_roles/nuevo_rol.html')