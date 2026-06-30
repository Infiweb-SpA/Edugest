import secrets
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.database import db
from app.models.edugest import EdugestUser, EdugestRolePermission, EdugestModule, EdugestRole
from app.models.mineduc import (
    Person, PersonIdentifier, PersonTelephone, PersonEmailAddress,
    Organization, OrganizationRelationship, OrganizationPersonRole
)

gestion_usuarios_bp = Blueprint('gestion_usuarios', __name__, url_prefix='/gestion-usuarios')


# ============================================================================
# HELPERS
# ============================================================================

def _admin_required():
    return current_user.is_authenticated and current_user.RoleId == 1


def _normalizar_rut(rut):
    rut = rut.strip().replace('.', '').replace(' ', '').upper()
    return rut


def _persona_ya_tiene_usuario(person_id):
    return EdugestUser.query.filter_by(PersonId=person_id).first() is not None


def _obtener_roles_disponibles():
    """Obtiene todos los roles desde la tabla EdugestRole."""
    return EdugestRole.query.order_by(EdugestRole.RoleId).all()


def _es_profesor_rol(role_id):
    """Verifica si el RoleId corresponde a un rol de tipo Profesor."""
    rol = EdugestRole.query.get(role_id)
    return rol and rol.RoleName.lower() == 'profesor'


def _obtener_grados_con_cursos():
    """
    Retorna una lista de grados (RefOrganizationTypeId=46),
    cada uno con sus cursos hijos (RefOrganizationTypeId=21).
    Estructura: [{'grado': Organization, 'cursos': [Organization, ...]}, ...]
    """
    grados = Organization.query.filter_by(
        RefOrganizationTypeId=46
    ).order_by(Organization.Name).all()

    resultado = []
    for grado in grados:
        cursos = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            OrganizationRelationship.ParentOrganizationId == grado.OrganizationId
        ).order_by(Organization.ShortName).all()
        resultado.append({'grado': grado, 'cursos': cursos})
    return resultado


def _obtener_profesor_jefe(person_id):
    """
    Retorna el OrganizationPersonRole donde esta persona es Profesor Jefe activo.
    Retorna None si no tiene asignación.
    """
    return OrganizationPersonRole.query.filter_by(
        PersonId=person_id,
        EsProfesorJefe=True,
        ExitDate=None
    ).first()


def _obtener_info_jefe(person_id):
    """
    Retorna un diccionario con el nombre del curso y grado
    si la persona es profesor jefe, o None si no lo es.
    """
    jefe_asignacion = _obtener_profesor_jefe(person_id)
    if not jefe_asignacion:
        return None

    curso_org = Organization.query.get(jefe_asignacion.OrganizationId)
    if not curso_org:
        return None

    rel = OrganizationRelationship.query.filter_by(
        OrganizationId=curso_org.OrganizationId
    ).first()
    grado_org = Organization.query.get(rel.ParentOrganizationId) if rel else None

    return {
        'curso': curso_org.Name,
        'grado': grado_org.Name if grado_org else '',
        'curso_id': curso_org.OrganizationId,
        'grado_id': grado_org.OrganizationId if grado_org else None,
        'asignacion': jefe_asignacion
    }


def _crear_asignacion_profesor_jefe(person_id, curso_id, role_id):
    """
    Crea un nuevo OrganizationPersonRole marcando al profesor como jefe.
    Primero cierra cualquier asignación anterior activa.
    """
    # Cerrar asignación anterior si existe
    OrganizationPersonRole.query.filter_by(
        PersonId=person_id, EsProfesorJefe=True, ExitDate=None
    ).update({'ExitDate': date.today()})

    # Crear nueva asignación
    nueva_asignacion = OrganizationPersonRole(
        OrganizationId=int(curso_id),
        PersonId=person_id,
        RoleId=role_id,
        EntryDate=date.today(),
        EsProfesorJefe=True
    )
    db.session.add(nueva_asignacion)


def _quitar_asignacion_profesor_jefe(person_id):
    """
    Cierra la asignación activa de profesor jefe (marca ExitDate).
    """
    OrganizationPersonRole.query.filter_by(
        PersonId=person_id, EsProfesorJefe=True, ExitDate=None
    ).update({'ExitDate': date.today()})


# ============================================================================
# API: CURSOS POR GRADO (para dropdown dependiente via AJAX)
# ============================================================================
@gestion_usuarios_bp.route('/api/cursos/<int:grado_id>')
@login_required
def api_cursos_por_grado(grado_id):
    """Retorna JSON con los cursos de un grado para carga dinámica."""
    if not _admin_required():
        return {'cursos': []}

    cursos = Organization.query.join(
        OrganizationRelationship,
        Organization.OrganizationId == OrganizationRelationship.OrganizationId
    ).filter(
        Organization.RefOrganizationTypeId == 21,
        OrganizationRelationship.ParentOrganizationId == grado_id
    ).order_by(Organization.ShortName).all()

    return {'cursos': [
        {'id': c.OrganizationId, 'nombre': c.Name, 'letra': c.ShortName or ''}
        for c in cursos
    ]}


# ============================================================================
# LISTAR USUARIOS
# ============================================================================
@gestion_usuarios_bp.route('/')
@login_required
def listar():
    if not _admin_required():
        flash('No tienes permisos para acceder a esta sección.', 'error')
        return redirect(url_for('admin.dashboard'))

    roles_dict = {r.RoleId: r.RoleName for r in EdugestRole.query.all()}

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

        # Buscar si es profesor jefe de algún curso
        jefe_info = None
        if _es_profesor_rol(u.RoleId):
            jefe_info = _obtener_info_jefe(u.PersonId)

        usuarios_data.append({
            'usuario': u,
            'persona': persona,
            'rut_persona': ident.Identifier if ident else 'Sin RUT',
            'permisos_count': permisos_count,
            'rol_nombre': roles_dict.get(u.RoleId, f'Rol {u.RoleId}'),
            'jefe_info': jefe_info
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

    roles_disponibles = _obtener_roles_disponibles()
    grados_con_cursos = _obtener_grados_con_cursos()

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

        # Campos de profesor jefe
        grado_id = request.form.get('grado_id')
        curso_id = request.form.get('curso_id')
        es_profesor_jefe = 'es_profesor_jefe' in request.form

        if len(password) < 4:
            flash('La contraseña debe tener al menos 4 caracteres.', 'error')
            return render_template('gestion_usuarios/formulario.html',
                                   personas=personas_data, modo_form='crear',
                                   usuario=None, datos_form=request.form,
                                   roles_disponibles=roles_disponibles,
                                   grados_con_cursos=grados_con_cursos)

        # ── MODO 1: Seleccionar persona existente ──
        if modo == 'existente':
            person_id = request.form.get('person_id')

            if not person_id:
                flash('Debes seleccionar una persona.', 'error')
                return render_template('gestion_usuarios/formulario.html',
                                       personas=personas_data, modo_form='crear',
                                       usuario=None, datos_form=request.form,
                                       roles_disponibles=roles_disponibles,
                                       grados_con_cursos=grados_con_cursos)

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
            db.session.flush()  # flush para que el usuario exista antes de crear asignación

            # Asignar profesor jefe si corresponde
            if _es_profesor_rol(role_id) and curso_id and es_profesor_jefe:
                _crear_asignacion_profesor_jefe(persona.PersonId, curso_id, role_id)

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

            if not nombres or not apellido_p or not rut:
                flash('Nombre, apellido paterno y RUT son obligatorios.', 'error')
                return render_template('gestion_usuarios/formulario.html',
                                       personas=personas_data, modo_form='crear',
                                       usuario=None, datos_form=request.form,
                                       roles_disponibles=roles_disponibles,
                                       grados_con_cursos=grados_con_cursos)

            ident_existente = PersonIdentifier.query.filter_by(
                Identifier=rut, RefPersonIdentificationSystemId=51
            ).first()

            if ident_existente:
                if _persona_ya_tiene_usuario(ident_existente.PersonId):
                    flash(f'El RUT {rut} ya tiene una cuenta de usuario.', 'error')
                    return render_template('gestion_usuarios/formulario.html',
                                           personas=personas_data, modo_form='crear',
                                           usuario=None, datos_form=request.form,
                                           roles_disponibles=roles_disponibles,
                                           grados_con_cursos=grados_con_cursos)
                else:
                    persona = Person.query.get(ident_existente.PersonId)
            else:
                persona = Person(
                    FirstName=nombres,
                    MiddleName='',
                    LastName=apellido_p,
                    SecondLastName=apellido_m if apellido_m else None
                )
                db.session.add(persona)
                db.session.flush()

                db.session.add(PersonIdentifier(
                    PersonId=persona.PersonId,
                    Identifier=rut,
                    RefPersonIdentificationSystemId=51
                ))

                if email:
                    db.session.add(PersonEmailAddress(
                        PersonId=persona.PersonId,
                        EmailAddress=email
                    ))

                if telefono:
                    db.session.add(PersonTelephone(
                        PersonId=persona.PersonId,
                        TelephoneNumber=telefono
                    ))

                db.session.flush()

            nuevo = EdugestUser(
                PersonId=persona.PersonId,
                Username=rut,
                PasswordHash=generate_password_hash(password),
                IsActive=is_active,
                RoleId=role_id
            )
            db.session.add(nuevo)
            db.session.flush()

            # Asignar profesor jefe si corresponde
            if _es_profesor_rol(role_id) and curso_id and es_profesor_jefe:
                _crear_asignacion_profesor_jefe(persona.PersonId, curso_id, role_id)

            db.session.commit()

            flash(f'Funcionario registrado y usuario creado: {rut}', 'success')
            return redirect(url_for('gestion_usuarios.listar'))

    return render_template('gestion_usuarios/formulario.html',
                           personas=personas_data, modo_form='crear',
                           usuario=None, datos_form={},
                           roles_disponibles=roles_disponibles,
                           grados_con_cursos=grados_con_cursos)


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
    roles_disponibles = _obtener_roles_disponibles()
    grados_con_cursos = _obtener_grados_con_cursos()

    if request.method == 'POST':
        role_id = int(request.form.get('role_id', usuario.RoleId))
        is_active = 'is_active' in request.form
        nueva_password = request.form.get('new_password', '').strip()

        usuario.RoleId = role_id
        usuario.IsActive = is_active

        if nueva_password:
            if len(nueva_password) < 4:
                flash('La contraseña debe tener al menos 4 caracteres.', 'error')
                jefe_info = _obtener_info_jefe(usuario.PersonId)
                return render_template('gestion_usuarios/formulario.html',
                                       personas=[], modo_form='editar',
                                       usuario=usuario, persona=persona,
                                       rut_persona=ident.Identifier if ident else 'Sin RUT',
                                       datos_form={},
                                       roles_disponibles=roles_disponibles,
                                       grados_con_cursos=grados_con_cursos,
                                       jefe_info=jefe_info)
            usuario.PasswordHash = generate_password_hash(nueva_password)

        # Gestionar asignación de profesor jefe
        grado_id = request.form.get('grado_id')
        curso_id = request.form.get('curso_id')
        es_profesor_jefe = 'es_profesor_jefe' in request.form

        if _es_profesor_rol(role_id) and es_profesor_jefe and grado_id and curso_id:
            _crear_asignacion_profesor_jefe(usuario.PersonId, curso_id, role_id)
        elif not es_profesor_jefe or not _es_profesor_rol(role_id):
            _quitar_asignacion_profesor_jefe(usuario.PersonId)

        db.session.commit()
        flash(f'Usuario {usuario.Username} actualizado correctamente.', 'success')
        return redirect(url_for('gestion_usuarios.listar'))

    # GET: cargar info actual del profesor jefe
    jefe_info = _obtener_info_jefe(usuario.PersonId)

    return render_template('gestion_usuarios/formulario.html',
                           personas=[], modo_form='editar',
                           usuario=usuario, persona=persona,
                           rut_persona=ident.Identifier if ident else 'Sin RUT',
                           datos_form={},
                           roles_disponibles=roles_disponibles,
                           grados_con_cursos=grados_con_cursos,
                           jefe_info=jefe_info)


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

def _es_profesor_rol(role_id):
    """Verifica si el RoleId corresponde a un rol de tipo Profesor."""
    rol = EdugestRole.query.get(role_id)
    return rol and rol.RoleName.lower() == 'profesor'


def _obtener_grados_con_cursos():
    """
    Retorna una lista de grados (RefOrganizationTypeId=46),
    cada uno con sus cursos hijos (RefOrganizationTypeId=21).
    Estructura: [{'grado': Organization, 'cursos': [Organization, ...]}, ...]
    """
    grados = Organization.query.filter_by(RefOrganizationTypeId=46).order_by(Organization.Name).all()
    resultado = []
    for grado in grados:
        cursos = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            OrganizationRelationship.ParentOrganizationId == grado.OrganizationId
        ).order_by(Organization.ShortName).all()
        resultado.append({'grado': grado, 'cursos': cursos})
    return resultado


def _obtener_profesor_jefe(person_id):
    """
    Retorna el OrganizationPersonRole donde esta persona es Profesor Jefe activo.
    Retorna None si no tiene asignación.
    """
    return OrganizationPersonRole.query.filter_by(
        PersonId=person_id,
        EsProfesorJefe=True,
        ExitDate=None
    ).first()