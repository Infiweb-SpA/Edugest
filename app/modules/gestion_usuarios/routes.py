import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.database import db
from app.models.edugest import EdugestUser, EdugestRolePermission, EdugestModule
from app.models.mineduc import Person, PersonIdentifier, OrganizationPersonRole, Organization, OrganizationRelationship

gestion_usuarios_bp = Blueprint('gestion_usuarios', __name__, url_prefix='/gestion-usuarios')


def _admin_required():
    """Retorna True si el usuario actual es admin, False si no."""
    return current_user.is_authenticated and current_user.RoleId == 1


# ============================================================================
# LISTAR USUARIOS
# ============================================================================
@gestion_usuarios_bp.route('/')
@login_required
def listar():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    usuarios = EdugestUser.query.order_by(EdugestUser.CreatedAt.desc()).all()
    usuarios_data = []

    for u in usuarios:
        persona = Person.query.get(u.PersonId)
        ident = PersonIdentifier.query.filter_by(
            PersonId=u.PersonId, RefPersonIdentificationSystemId=51
        ).first()

        # Contar permisos activos
        permisos_count = EdugestRolePermission.query.filter_by(
            RoleId=u.RoleId
        ).filter(EdugestRolePermission.PermissionLevel > 0).count()

        usuarios_data.append({
            'usuario': u,
            'persona': persona,
            'rut_persona': ident.Identifier if ident else 'Sin RUT',
            'permisos_count': permisos_count
        })

    return render_template('gestion_usuarios/listar.html', usuarios=usuarios_data)


# ============================================================================
# CREAR USUARIO
# ============================================================================
@gestion_usuarios_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def crear():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Obtener todas las personas que NO tienen usuario asignado
    personas_con_usuario = db.session.query(EdugestUser.PersonId).subquery()
    personas_disponibles = Person.query.filter(
        ~Person.PersonId.in_(personas_con_usuario)
    ).order_by(Person.LastName, Person.FirstName).all()

    # Agregar RUT a cada persona para mostrar
    personas_data = []
    for p in personas_disponibles:
        ident = PersonIdentifier.query.filter_by(
            PersonId=p.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        personas_data.append({
            'persona': p,
            'rut': ident.Identifier if ident else 'Sin RUT'
        })

    if request.method == 'POST':
        person_id = request.form.get('person_id')
        password = request.form.get('password', '').strip()
        role_id = int(request.form.get('role_id', 6))
        is_active = 'is_active' in request.form

        # Validaciones
        if not person_id:
            flash('Debes seleccionar una persona.', 'error')
            return render_template('gestion_usuarios/formulario.html',
                                   personas=personas_data, modo='crear', usuario=None)

        if len(password) < 4:
            flash('La contraseña debe tener al menos 4 caracteres.', 'error')
            return render_template('gestion_usuarios/formulario.html',
                                   personas=personas_data, modo='crear', usuario=None)

        persona = Person.query.get(int(person_id))
        if not persona:
            flash('Persona no encontrada.', 'error')
            return redirect(url_for('gestion_usuarios.crear'))

        # Obtener RUT como username
        ident = PersonIdentifier.query.filter_by(
            PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        username = ident.Identifier if ident else f"user_{persona.PersonId}"

        # Verificar que no exista
        if EdugestUser.query.filter_by(Username=username).first():
            flash(f'Ya existe un usuario con RUT {username}.', 'error')
            return redirect(url_for('gestion_usuarios.crear'))

        nuevo = EdugestUser(
            PersonId=persona.PersonId,
            Username=username,
            PasswordHash=generate_password_hash(password),
            IsActive=is_active,
            RoleId=role_id
        )
        db.session.add(nuevo)
        db.session.commit()

        flash(f'Usuario creado: {username}', 'success')
        return redirect(url_for('gestion_usuarios.listar'))

    return render_template('gestion_usuarios/formulario.html',
                           personas=personas_data, modo='crear', usuario=None)


# ============================================================================
# EDITAR USUARIO
# ============================================================================
@gestion_usuarios_bp.route('/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(user_id):
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    usuario = EdugestUser.query.get_or_404(user_id)
    persona = Person.query.get(usuario.PersonId)
    ident = PersonIdentifier.query.filter_by(
        PersonId=usuario.PersonId, RefPersonIdentificationSystemId=51
    ).first()

    if request.method == 'POST':
        role_id = int(request.form.get('role_id', usuario.RoleId))
        is_active = 'is_active' in request.form
        nueva_password = request.form.get('new_password', '').strip()

        usuario.RoleId = role_id
        usuario.IsActive = is_active

        if nueva_password:
            if len(nueva_password) < 4:
                flash('La contraseña debe tener al menos 4 caracteres.', 'error')
                return render_template('gestion_usuarios/formulario.html',
                                       personas=[], modo='editar', usuario=usuario,
                                       persona=persona, rut_persona=ident.Identifier if ident else 'Sin RUT')
            usuario.PasswordHash = generate_password_hash(nueva_password)

        db.session.commit()
        flash(f'Usuario {usuario.Username} actualizado correctamente.', 'success')
        return redirect(url_for('gestion_usuarios.listar'))

    return render_template('gestion_usuarios/formulario.html',
                           personas=[], modo='editar', usuario=usuario,
                           persona=persona, rut_persona=ident.Identifier if ident else 'Sin RUT')


# ============================================================================
# RESETEAR CONTRASEÑA
# ============================================================================
@gestion_usuarios_bp.route('/<int:user_id>/resetear-password', methods=['POST'])
@login_required
def resetear_password(user_id):
    if not _admin_required():
        flash('No tienes permisos.', 'error')
        return redirect(url_for('admin.dashboard'))

    usuario = EdugestUser.query.get_or_404(user_id)

    # Generar contraseña temporal aleatoria
    nueva_pass = secrets.token_hex(4)  # 8 caracteres hex
    usuario.PasswordHash = generate_password_hash(nueva_pass)
    db.session.commit()

    flash(f'Contraseña de {usuario.Username} reseteada. Nueva contraseña temporal: {nueva_pass}', 'success')
    return redirect(url_for('gestion_usuarios.editar', user_id=user_id))


# ============================================================================
# TOGGLE ACTIVO/INACTIVO
# ============================================================================
@gestion_usuarios_bp.route('/<int:user_id>/toggle-activo', methods=['POST'])
@login_required
def toggle_activo(user_id):
    if not _admin_required():
        flash('No tienes permisos.', 'error')
        return redirect(url_for('admin.dashboard'))

    usuario = EdugestUser.query.get_or_404(user_id)
    usuario.IsActive = not usuario.IsActive
    db.session.commit()

    estado = "activado" if usuario.IsActive else "desactivado"
    flash(f'Usuario {usuario.Username} {estado}.', 'success')
    return redirect(url_for('gestion_usuarios.listar'))