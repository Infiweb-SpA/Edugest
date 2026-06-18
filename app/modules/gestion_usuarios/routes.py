import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.database import db
from app.models.edugest import EdugestUser, EdugestRolePermission, EdugestModule
from app.models.mineduc import Person, PersonIdentifier, PersonTelephone, PersonEmailAddress

gestion_usuarios_bp = Blueprint('gestion_usuarios', __name__, url_prefix='/gestion-usuarios')


def _admin_required():
    return current_user.is_authenticated and current_user.RoleId == 1


def _normalizar_rut(rut):
    """Limpia y normaliza un RUT chileno."""
    rut = rut.strip().replace('.', '').replace(' ', '').upper()
    return rut


def _persona_ya_tiene_usuario(person_id):
    """Verifica si una PersonId ya tiene cuenta de usuario."""
    return EdugestUser.query.filter_by(PersonId=person_id).first() is not None


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
# CREAR USUARIO (con dos modos: existente o nueva persona)
# ============================================================================
@gestion_usuarios_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def crear():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    # Personas existentes sin usuario
    personas_con_usuario = db.session.query(EdugestUser.PersonId).subquery()
    personas_disponibles = Person.query.filter(
        ~Person.PersonId.in_(personas_con_usuario)
    ).order_by(Person.LastName, Person.FirstName).all()

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
        modo = request.form.get('modo', 'existente')
        password = request.form.get('password', '').strip()
        role_id = int(request.form.get('role_id', 6))
        is_active = 'is_active' in request.form

        # Validar contraseña
        if len(password) < 4:
            flash('La contraseña debe tener al menos 4 caracteres.', 'error')
            return render_template('gestion_usuarios/formulario.html',
                                   personas=personas_data, modo_form='crear',
                                   usuario=None, datos_form=request.form)

        # ── MODO 1: Seleccionar persona existente ──
        if modo == 'existente':
            person_id = request.form.get('person_id')

            if not person_id:
                flash('Debes seleccionar una persona.', 'error')
                return render_template('gestion_usuarios/formulario.html',
                                       personas=personas_data, modo_form='crear',
                                       usuario=None, datos_form=request.form)

            persona = Person.query.get(int(person_id))
            if not persona:
                flash('Persona no encontrada.', 'error')
                return redirect(url_for('gestion_usuarios.crear'))

            ident = PersonIdentifier.query.filter_by(
                PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
            ).first()
            username = ident.Identifier if ident else f"user_{persona.PersonId}"

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

        # ── MODO 2: Crear nueva persona (funcionario) ──
        elif modo == 'nueva':
            nombres = request.form.get('nombres', '').strip()
            apellido_p = request.form.get('apellido_p', '').strip()
            apellido_m = request.form.get('apellido_m', '').strip()
            rut = _normalizar_rut(request.form.get('rut', ''))
            email = request.form.get('email', '').strip()
            telefono = request.form.get('telefono', '').strip()

            # Validaciones
            if not nombres or not apellido_p or not rut:
                flash('Nombre, apellido paterno y RUT son obligatorios.', 'error')
                return render_template('gestion_usuarios/formulario.html',
                                       personas=personas_data, modo_form='crear',
                                       usuario=None, datos_form=request.form)

            # Verificar que el RUT no esté repetido en PersonIdentifier
            ident_existente = PersonIdentifier.query.filter_by(
                Identifier=rut, RefPersonIdentificationSystemId=51
            ).first()

            if ident_existente:
                # La persona ya existe, verificar si tiene usuario
                if _persona_ya_tiene_usuario(ident_existente.PersonId):
                    flash(f'El RUT {rut} ya tiene una cuenta de usuario.', 'error')
                    return render_template('gestion_usuarios/formulario.html',
                                           personas=personas_data, modo_form='crear',
                                           usuario=None, datos_form=request.form)
                else:
                    # La persona existe pero sin usuario, usarla
                    persona = Person.query.get(ident_existente.PersonId)
            else:
                # Crear persona nueva
                persona = Person(
                    FirstName=nombres,
                    MiddleName='',
                    LastName=apellido_p,
                    SecondLastName=apellido_m if apellido_m else None
                )
                db.session.add(persona)
                db.session.flush()

                # RUT
                db.session.add(PersonIdentifier(
                    PersonId=persona.PersonId,
                    Identifier=rut,
                    RefPersonIdentificationSystemId=51
                ))

                # Email (opcional)
                if email:
                    db.session.add(PersonEmailAddress(
                        PersonId=persona.PersonId,
                        EmailAddress=email
                    ))

                # Teléfono (opcional)
                if telefono:
                    db.session.add(PersonTelephone(
                        PersonId=persona.PersonId,
                        TelephoneNumber=telefono
                    ))

                db.session.flush()

            # Crear usuario
            nuevo = EdugestUser(
                PersonId=persona.PersonId,
                Username=rut,
                PasswordHash=generate_password_hash(password),
                IsActive=is_active,
                RoleId=role_id
            )
            db.session.add(nuevo)
            db.session.commit()

            flash(f'Funcionario registrado y usuario creado: {rut}', 'success')
            return redirect(url_for('gestion_usuarios.listar'))

    return render_template('gestion_usuarios/formulario.html',
                           personas=personas_data, modo_form='crear',
                           usuario=None, datos_form={})


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
                                       personas=[], modo_form='editar',
                                       usuario=usuario, persona=persona,
                                       rut_persona=ident.Identifier if ident else 'Sin RUT',
                                       datos_form={})
            usuario.PasswordHash = generate_password_hash(nueva_password)

        db.session.commit()
        flash(f'Usuario {usuario.Username} actualizado correctamente.', 'success')
        return redirect(url_for('gestion_usuarios.listar'))

    return render_template('gestion_usuarios/formulario.html',
                           personas=[], modo_form='editar',
                           usuario=usuario, persona=persona,
                           rut_persona=ident.Identifier if ident else 'Sin RUT',
                           datos_form={})


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

    nueva_pass = secrets.token_hex(4)
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