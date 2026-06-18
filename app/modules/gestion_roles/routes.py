from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.database import db
from app.models.edugest import EdugestRolePermission, EdugestModule, EdugestUser

gestion_roles_bp = Blueprint('gestion_roles', __name__, url_prefix='/gestion-roles')

# Nombres amigables para los roles conocidos
ROLES_NOMBRES = {
    1: 'Administrador',
    3: 'Profesor',
    6: 'Apoderado / Tutor'
}


def _admin_required():
    return current_user.is_authenticated and current_user.RoleId == 1


# ============================================================================
# LISTAR ROLES
# ============================================================================
@gestion_roles_bp.route('/')
@login_required
def listar():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Obtener todos los RoleId únicos que existen en usuarios + permisos
    roles_ids_usuarios = db.session.query(EdugestUser.RoleId).distinct().all()
    roles_ids_permisos = db.session.query(EdugestRolePermission.RoleId).distinct().all()

    todos_los_role_ids = set()
    for r in roles_ids_usuarios:
        todos_los_role_ids.add(r[0])
    for r in roles_ids_permisos:
        todos_los_role_ids.add(r[0])

    # Si no hay ninguno, asegurar que existan los roles base
    if not todos_los_role_ids:
        todos_los_role_ids = {1, 3, 6}

    roles_data = []
    for role_id in sorted(todos_los_role_ids):
        # Contar usuarios con este rol
        total_usuarios = EdugestUser.query.filter_by(RoleId=role_id).count()

        # Contar permisos asignados
        permisos = EdugestRolePermission.query.filter_by(RoleId=role_id).all()
        permisos_activos = sum(1 for p in permisos if p.PermissionLevel > 0)
        total_modulos = EdugestModule.query.count()

        roles_data.append({
            'role_id': role_id,
            'nombre': ROLES_NOMBRES.get(role_id, f'Rol {role_id}'),
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

    rol_nombre = ROLES_NOMBRES.get(role_id, f'Rol {role_id}')
    modulos = EdugestModule.query.order_by(EdugestModule.ModuleName).all()

    if request.method == 'POST':
        # Limpiar permisos actuales de este rol
        EdugestRolePermission.query.filter_by(RoleId=role_id).delete()

        # Crear nuevos permisos desde el formulario
        for modulo in modulos:
            nivel = int(request.form.get(f'permiso_{modulo.ModuleId}', 0))
            nuevo_permiso = EdugestRolePermission(
                RoleId=role_id,
                ModuleId=modulo.ModuleId,
                PermissionLevel=nivel
            )
            db.session.add(nuevo_permiso)

        db.session.commit()
        flash(f'Permisos del rol "{rol_nombre}" actualizados correctamente.', 'success')
        return redirect(url_for('gestion_roles.listar'))

    # Cargar permisos actuales para pre-llenar el formulario
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

        if role_id in ROLES_NOMBRES:
            flash(f'El ID {role_id} ya está asignado al rol "{ROLES_NOMBRES[role_id]}". Elige otro.', 'error')
            return render_template('gestion_roles/nuevo_rol.html')

        # Verificar que no tenga permisos ya asignados
        if EdugestRolePermission.query.filter_by(RoleId=role_id).first():
            flash(f'El ID {role_id} ya tiene permisos asignados. Elige otro ID.', 'error')
            return render_template('gestion_roles/nuevo_rol.html')

        # Crear permisos vacíos (todos en 0) para todos los módulos
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