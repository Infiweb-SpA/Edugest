from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from app.database import db
from app.models.mineduc import (
    Person, Organization, OrganizationPersonRole, PersonRelationship,
    PersonTelephone, PersonEmailAddress, PersonAddress, PersonIdentifier,
    OrganizationRelationship
)
from app.models.edugest import (
    EdugestAnnouncement, EdugestStudentHealth, EdugestStudentEnrollment,
    EdugestEmergencyContact, EdugestPersonRelationshipDetail,
    EdugestChatMessage, EdugestUser, obtener_hora_chile          # ← NUEVO
)
from app.modules.auth.routes import permiso_requerido
from sqlalchemy import or_

comunicacion_bp = Blueprint('comunicacion', __name__, url_prefix='/comunicacion')


# =============================================================================
# HELPERS
# =============================================================================

def obtener_apoderado_estudiante(person_id):
    """Obtiene el apoderado principal del estudiante con datos enriquecidos."""
    relacion = PersonRelationship.query.filter_by(
        PersonId=person_id, RefPersonRelationshipId=31
    ).first()

    if not relacion:
        return None

    apoderado = db.session.get(Person, relacion.RelatedPersonId)
    if not apoderado:
        return None

    # Obtener datos adicionales
    telefono = PersonTelephone.query.filter_by(PersonId=apoderado.PersonId).first()
    email = PersonEmailAddress.query.filter_by(PersonId=apoderado.PersonId).first()
    direccion = PersonAddress.query.filter_by(PersonId=apoderado.PersonId).first()

    # Obtener detalles de la relación (nuevos campos)
    detalle = EdugestPersonRelationshipDetail.query.filter_by(
        PersonRelationshipId=relacion.PersonRelationshipId
    ).first()

    return {
        'persona': apoderado,
        'telefono': telefono.TelephoneNumber if telefono else None,
        'email': email.EmailAddress if email else None,
        'direccion': direccion.StreetNumberAndName if direccion else None,
        'detalle': detalle
    }


def obtener_contactos_emergencia(person_id):
    """Obtiene los contactos de emergencia del estudiante."""
    contactos = EdugestEmergencyContact.query.filter_by(
        PersonId=person_id
    ).order_by(EdugestEmergencyContact.Orden).all()
    return contactos


def obtener_info_medica(person_id):
    """Obtiene la información médica del estudiante."""
    health = EdugestStudentHealth.query.filter_by(PersonId=person_id).first()
    enrollment = EdugestStudentEnrollment.query.filter_by(PersonId=person_id).first()
    return health, enrollment


def generar_wa_link(telefono):
    """Genera enlace de WhatsApp a partir de un número de teléfono."""
    if not telefono:
        return None
    num_limpio = ''.join(c for c in telefono if c.isdigit())
    if not num_limpio:
        return None

    # Normalizar número chileno
    if num_limpio.startswith('569') and len(num_limpio) == 11:
        num_limpio = '56' + num_limpio[3:]
    elif num_limpio.startswith('9') and len(num_limpio) == 9:
        num_limpio = '56' + num_limpio
    elif num_limpio.startswith('56') and len(num_limpio) == 11:
        pass  # Ya está correcto
    elif num_limpio.startswith('56') and len(num_limpio) == 12:
        pass  # Ya está correcto

    return f"https://wa.me/{num_limpio}"


def enriquecer_cursos(cursos):
    """Agrega nombre de grado padre a cada curso."""
    for c in cursos:
        rel = OrganizationRelationship.query.filter_by(OrganizationId=c.OrganizationId).first()
        c.grado_nombre = ''
        if rel:
            grado = db.session.get(Organization, rel.ParentOrganizationId)
            if grado:
                c.grado_nombre = grado.Name
    return cursos


# =============================================================================
# VISTA UNIFICADA: ANUNCIOS + CONTACTOS
# =============================================================================

@comunicacion_bp.route('/anuncios')
@login_required
@permiso_requerido('Comunicaciones', nivel=1)
def anuncios():
    # --- BLOQUE ANUNCIOS ---
    curso_id_anuncio = request.args.get('curso_id_anuncio', type=int)

    query = EdugestAnnouncement.query.order_by(EdugestAnnouncement.CreatedAt.desc())

    if curso_id_anuncio:
        query = query.filter(
            or_(
                EdugestAnnouncement.TargetOrganizationId == curso_id_anuncio,
                EdugestAnnouncement.TargetOrganizationId == None
            )
        )

    anuncios_list = query.all()

    for a in anuncios_list:
        a.sender = db.session.get(Person, a.SenderPersonId) if a.SenderPersonId else None
        a.curso = db.session.get(Organization, a.TargetOrganizationId) if a.TargetOrganizationId else None

    # --- BLOQUE CONTACTOS ---
    curso_id_contacto = request.args.get('curso_id_contacto', type=int)

    # Cursos disponibles (tipo 21 = Course / letra)
    cursos = db.session.query(Organization).join(
        OrganizationPersonRole, Organization.OrganizationId == OrganizationPersonRole.OrganizationId
    ).filter(
        OrganizationPersonRole.RoleId == 6,
        OrganizationPersonRole.ExitDate == None,
        Organization.RefOrganizationTypeId == 21
    ).distinct().order_by(Organization.Name).all()

    cursos = enriquecer_cursos(cursos)

    contactos_data = []
    if curso_id_contacto:
        estudiantes_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=curso_id_contacto, RoleId=6, ExitDate=None
        ).join(Person).order_by(Person.LastName, Person.FirstName).all()

        for er in estudiantes_roles:
            estudiante = er.person
            apoderado_data = obtener_apoderado_estudiante(estudiante.PersonId)

            contactos_data.append({
                'estudiante': estudiante,
                'apoderado': apoderado_data['persona'] if apoderado_data else None,
                'telefono_apoderado': apoderado_data['telefono'] if apoderado_data else None,
                'rol_id': er.OrganizationPersonRoleId
            })

    return render_template('comunicacion/anuncios.html',
                         anuncios=anuncios_list,
                         cursos=cursos,
                         curso_id_anuncio=curso_id_anuncio,
                         curso_id_contacto=curso_id_contacto,
                         contactos=contactos_data)


@comunicacion_bp.route('/anuncios/nuevo', methods=['POST'])
@login_required
@permiso_requerido('Comunicaciones', nivel=2)
def nuevo_anuncio():
    # Los apoderados (RoleId=6) no pueden publicar anuncios
    if current_user.RoleId == 6:
        flash('Los apoderados no pueden publicar anuncios.', 'error')
        return redirect(url_for('comunicacion.anuncios'))

    titulo = request.form.get('titulo', '').strip()
    contenido = request.form.get('contenido', '').strip()
    curso_id = request.form.get('curso_id', type=int)

    if not titulo or not contenido:
        flash('El título y contenido son obligatorios.', 'error')
        return redirect(url_for('comunicacion.anuncios'))

    sender = db.session.query(Person).join(
        OrganizationPersonRole, Person.PersonId == OrganizationPersonRole.PersonId
    ).filter(OrganizationPersonRole.RoleId.in_([1, 2])).first()

    from datetime import datetime
    import pytz

    chile_tz = pytz.timezone('America/Santiago')
    now_local = datetime.now(chile_tz)

    anuncio = EdugestAnnouncement(
        SenderPersonId=sender.PersonId if sender else 1,
        TargetOrganizationId=curso_id if curso_id else None,
        Title=titulo,
        Content=contenido,
        CreatedAt=now_local
    )
    db.session.add(anuncio)
    db.session.commit()
    flash('Anuncio publicado correctamente.', 'success')
    return redirect(url_for('comunicacion.anuncios'))


# =============================================================================
# C O N T A C T O S  /  A P O D E R A D O S
# =============================================================================

@comunicacion_bp.route('/contactos')
@login_required
@permiso_requerido('Comunicaciones', nivel=1)
def contactos():
    curso_id = request.args.get('curso_id', type=int)
    vista = request.args.get('vista', 'alumnos')  # 'alumnos' o 'funcionarios'

    # Cursos disponibles (tipo 21 = Course / letra)
    cursos = db.session.query(Organization).join(
        OrganizationPersonRole, Organization.OrganizationId == OrganizationPersonRole.OrganizationId
    ).filter(
        OrganizationPersonRole.RoleId == 6,
        OrganizationPersonRole.ExitDate == None,
        Organization.RefOrganizationTypeId == 21
    ).distinct().order_by(Organization.Name).all()

    cursos = enriquecer_cursos(cursos)

    contactos_data = []
    if vista == 'alumnos' and curso_id:
        estudiantes_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=curso_id, RoleId=6, ExitDate=None
        ).join(Person).order_by(Person.LastName, Person.FirstName).all()

        for er in estudiantes_roles:
            estudiante = er.person
            apoderado_data = obtener_apoderado_estudiante(estudiante.PersonId)

            contactos_data.append({
                'estudiante': estudiante,
                'apoderado': apoderado_data['persona'] if apoderado_data else None,
                'telefono_apoderado': apoderado_data['telefono'] if apoderado_data else None,
                'rol_id': er.OrganizationPersonRoleId
            })

    # --- FUNCIONARIOS DEL SISTEMA ---
    funcionarios_data = []
    if vista == 'funcionarios':
        rol_nombre_map = {1: 'Administrador', 2: 'Director', 3: 'Profesor', 4: 'Funcionario', 6: 'Apoderado'}

        # Obtener todos los usuarios activos que NO sean apoderados (RoleId != 6)
        usuarios_staff = EdugestUser.query.filter(
            EdugestUser.IsActive == True,
            EdugestUser.RoleId.in_([1, 2, 3, 4])
        ).all()

        for u in usuarios_staff:
            persona = db.session.get(Person, u.PersonId)
            if not persona:
                continue

            # Si se filtró por curso, verificar que este usuario pertenezca a ese curso
            if curso_id:
                asignacion = OrganizationPersonRole.query.filter(
                    OrganizationPersonRole.PersonId == u.PersonId,
                    OrganizationPersonRole.OrganizationId == curso_id,
                    OrganizationPersonRole.ExitDate == None
                ).first()
                if not asignacion:
                    continue

            telefono = PersonTelephone.query.filter_by(PersonId=u.PersonId).first()
            email = PersonEmailAddress.query.filter_by(PersonId=u.PersonId).first()

            # Cursos asignados a este funcionario (RoleId 3 = Profesor)
            cursos_asignados = OrganizationPersonRole.query.filter(
                OrganizationPersonRole.PersonId == u.PersonId,
                OrganizationPersonRole.RoleId == 3,
                OrganizationPersonRole.ExitDate == None
            ).all()
            cursos_nombres = []
            for ca in cursos_asignados:
                org = db.session.get(Organization, ca.OrganizationId)
                if org:
                    rel = OrganizationRelationship.query.filter_by(
                        OrganizationId=org.OrganizationId
                    ).first()
                    grado_nombre = ''
                    if rel:
                        grado = db.session.get(Organization, rel.ParentOrganizationId)
                        grado_nombre = grado.Name if grado else ''
                    cursos_nombres.append(f"{grado_nombre} {org.Name}".strip())

            funcionarios_data.append({
                'persona': persona,
                'rol': rol_nombre_map.get(u.RoleId, 'Funcionario'),
                'telefono': telefono.TelephoneNumber if telefono else None,
                'email': email.EmailAddress if email else None,
                'cursos': ', '.join(cursos_nombres) if cursos_nombres else 'Sin cursos asignados'
            })

        funcionarios_data.sort(
            key=lambda x: (x['persona'].LastName or '', x['persona'].FirstName or '')
        )

    return render_template('comunicacion/contactos.html',
                         cursos=cursos, contactos=contactos_data,
                         funcionarios=funcionarios_data,
                         curso_id=curso_id, vista=vista)


@comunicacion_bp.route('/contacto/<int:person_id>')
@login_required
@permiso_requerido('Comunicaciones', nivel=2)
def contacto_detalle(person_id):
    estudiante = db.session.get(Person, person_id)
    if not estudiante:
        abort(404)

    # Curso actual
    rol_estudiante = OrganizationPersonRole.query.filter_by(
        PersonId=person_id, RoleId=6, ExitDate=None
    ).first()
    curso = None
    if rol_estudiante:
        curso = db.session.get(Organization, rol_estudiante.OrganizationId)
        if curso:
            rel = OrganizationRelationship.query.filter_by(OrganizationId=curso.OrganizationId).first()
            if rel:
                grado = db.session.get(Organization, rel.ParentOrganizationId)
                curso.grado_nombre = grado.Name if grado else ''

    # Identificadores del estudiante
    run = PersonIdentifier.query.filter_by(
        PersonId=person_id, RefPersonIdentificationSystemId=51
    ).first()
    ipe = PersonIdentifier.query.filter_by(
        PersonId=person_id, RefPersonIdentificationSystemId=52
    ).first()

    # Contactos del estudiante
    tel_est = PersonTelephone.query.filter_by(PersonId=person_id).first()
    email_est = PersonEmailAddress.query.filter_by(PersonId=person_id).first()

    # Apoderado principal
    apoderado_data = obtener_apoderado_estudiante(person_id)

    apoderado = None
    tel_apod = None
    email_apod = None
    dir_apod = None
    wa_link = None
    detalle_apoderado = None

    if apoderado_data:
        apoderado = apoderado_data['persona']
        tel_apod = apoderado_data['telefono']
        email_apod = apoderado_data['email']
        dir_apod = apoderado_data['direccion']
        detalle_apoderado = apoderado_data['detalle']

        if tel_apod:
            wa_link = generar_wa_link(tel_apod)

    # Contactos de emergencia
    contactos_emergencia = obtener_contactos_emergencia(person_id)

    # Información médica
    health, enrollment = obtener_info_medica(person_id)

    return render_template('comunicacion/contacto_detalle.html',
                         estudiante=estudiante,
                         curso=curso,
                         run=run.Identifier if run else None,
                         ipe=ipe.Identifier if ipe else None,
                         telefono_estudiante=tel_est.TelephoneNumber if tel_est else None,
                         email_estudiante=email_est.EmailAddress if email_est else None,
                         apoderado=apoderado,
                         telefono_apoderado=tel_apod,
                         email_apoderado=email_apod,
                         direccion_apoderado=dir_apod,
                         detalle_apoderado=detalle_apoderado,
                         wa_link=wa_link,
                         contactos_emergencia=contactos_emergencia,
                         health=health,
                         enrollment=enrollment)

# =============================================================================
# C H A T   B I D I R E C C I O N A L   ( M E N S A J E R Í A )
# =============================================================================

def obtener_contactos_para_chat():
    """
    Retorna lista de dicts con las personas con las que el usuario
    actual puede iniciar o continuar un chat, según su rol.
    Cada dict contiene: {'persona': Person, 'rol': str, ...}
    """
    mi_person_id = current_user.PersonId
    mi_role_id = current_user.RoleId
    contactos = []
    seen = set()

    def agregar(person_id, rol_nombre, **kwargs):
        if person_id in seen or person_id == mi_person_id:
            return
        seen.add(person_id)
        p = db.session.get(Person, person_id)
        if p:
            entry = {'persona': p, 'rol': rol_nombre}
            entry.update(kwargs)
            contactos.append(entry)

    # ── Admin: todos los usuarios activos ──
    if mi_role_id == 1:
        rol_map = {1: 'Administrador', 3: 'Profesor', 6: 'Apoderado'}
        for u in EdugestUser.query.filter(
            EdugestUser.PersonId != mi_person_id,
            EdugestUser.IsActive == True
        ).all():
            agregar(u.PersonId, rol_map.get(u.RoleId, 'Usuario'))

    # ── Profesor: apoderados de los estudiantes de SUS cursos ──
    elif mi_role_id == 3:
        mis_cursos = OrganizationPersonRole.query.filter_by(
            PersonId=mi_person_id, RoleId=3, ExitDate=None
        ).all()
        for mc in mis_cursos:
            estudiantes = OrganizationPersonRole.query.filter_by(
                OrganizationId=mc.OrganizationId, RoleId=6, ExitDate=None
            ).all()
            for est in estudiantes:
                rel = PersonRelationship.query.filter_by(
                    PersonId=est.PersonId, RefPersonRelationshipId=31
                ).first()
                if rel and EdugestUser.query.filter_by(
                    PersonId=rel.RelatedPersonId, IsActive=True
                ).first():
                    estudiante = db.session.get(Person, est.PersonId)
                    nombre_est = f"{estudiante.FirstName} {estudiante.LastName}" if estudiante else ''
                    agregar(rel.RelatedPersonId, 'Apoderado', de_estudiante=nombre_est)

    # ── Apoderado: profesores de los cursos de SUS hijos ──
    # Apoderado: profesores y funcionarios del establecimiento de SUS hijos
    elif mi_role_id == 6:
        hijos_rel = PersonRelationship.query.filter_by(
            RelatedPersonId=mi_person_id, RefPersonRelationshipId=31
        ).all()

        for hr in hijos_rel:
            # 1. Profesores directamente asignados a los cursos del hijo
            cursos_hijo = OrganizationPersonRole.query.filter_by(
                PersonId=hr.PersonId, RoleId=6, ExitDate=None
            ).all()
            for ch in cursos_hijo:
                # Buscar profesores (RoleId=3) en este curso
                profesores = OrganizationPersonRole.query.filter_by(
                    OrganizationId=ch.OrganizationId, RoleId=3, ExitDate=None
                ).all()
                for prof in profesores:
                    if EdugestUser.query.filter_by(
                        PersonId=prof.PersonId, IsActive=True
                    ).first():
                        hijo = db.session.get(Person, hr.PersonId)
                        curso_obj = db.session.get(Organization, ch.OrganizationId)
                        agregar(prof.PersonId, 'Profesor',
                                de_estudiante=hijo.FirstName if hijo else '',
                                curso=curso_obj.Name if curso_obj else '')

                # 2. Funcionarios administrativos vinculados al curso
                funcionarios = OrganizationPersonRole.query.filter(
                    OrganizationPersonRole.OrganizationId == ch.OrganizationId,
                    OrganizationPersonRole.RoleId.in_([1, 2, 3, 4]),
                    OrganizationPersonRole.ExitDate == None
                ).all()
                for func in funcionarios:
                    u_func = EdugestUser.query.filter_by(
                        PersonId=func.PersonId, IsActive=True
                    ).first()
                    if u_func:
                        rol_nombre = {1: 'Administrador', 2: 'Director',
                                      3: 'Profesor', 4: 'Funcionario'}.get(u_func.RoleId, 'Funcionario')
                        hijo = db.session.get(Person, hr.PersonId)
                        curso_obj = db.session.get(Organization, ch.OrganizationId)
                        agregar(func.PersonId, rol_nombre,
                                de_estudiante=hijo.FirstName if hijo else '',
                                curso=curso_obj.Name if curso_obj else '')

            # 3. Buscar el establecimiento (colegio) del hijo y sus funcionarios
            curso_actual = OrganizationPersonRole.query.filter_by(
                PersonId=hr.PersonId, RoleId=6, ExitDate=None
            ).first()
            if curso_actual:
                # Encontrar el Organization padre (grado)
                rel_org = OrganizationRelationship.query.filter_by(
                    OrganizationId=curso_actual.OrganizationId
                ).first()
                if rel_org:
                    # Encontrar el Organization abuelo (establecimiento/colegio)
                    rel_colegio = OrganizationRelationship.query.filter_by(
                        OrganizationId=rel_org.ParentOrganizationId
                    ).first()
                    if rel_colegio:
                        colegio_id = rel_colegio.ParentOrganizationId
                        # Buscar todos los funcionarios activos del establecimiento
                        staff = OrganizationPersonRole.query.filter(
                            OrganizationPersonRole.OrganizationId == colegio_id,
                            OrganizationPersonRole.RoleId.in_([1, 2, 3, 4]),
                            OrganizationPersonRole.ExitDate == None
                        ).all()
                        for s in staff:
                            u_staff = EdugestUser.query.filter_by(
                                PersonId=s.PersonId, IsActive=True
                            ).first()
                            if u_staff and s.PersonId != mi_person_id:
                                rol_nombre = {1: 'Administrador', 2: 'Director',
                                              3: 'Profesor', 4: 'Funcionario'}.get(u_staff.RoleId, 'Funcionario')
                                agregar(s.PersonId, rol_nombre)

    return contactos


# ── Vista: Lista de conversaciones (bandeja de entrada) ──
@comunicacion_bp.route('/chat')
@login_required
@permiso_requerido('Comunicaciones', nivel=1)
def chat_lista():
    mi_person_id = current_user.PersonId

    # Conversaciones existentes (agrupar mensajes por contacto)
    mensajes = EdugestChatMessage.query.filter(
        or_(
            EdugestChatMessage.SenderPersonId == mi_person_id,
            EdugestChatMessage.ReceiverPersonId == mi_person_id
        )
    ).order_by(EdugestChatMessage.SentAt.desc()).all()

    conversaciones = {}
    for msg in mensajes:
        otro_id = msg.ReceiverPersonId if msg.SenderPersonId == mi_person_id else msg.SenderPersonId
        if otro_id not in conversaciones:
            otro = db.session.get(Person, otro_id)
            conversaciones[otro_id] = {
                'persona': otro,
                'ultimo_mensaje': msg,
                'no_leidos': 0
            }
        if msg.SenderPersonId != mi_person_id and not msg.IsRead:
            conversaciones[otro_id]['no_leidos'] += 1

    # Contactos disponibles que aún NO tienen conversación
    todos = obtener_contactos_para_chat()
    disponibles = [c for c in todos if c['persona'].PersonId not in conversaciones]

    return render_template('comunicacion/chat_lista.html',
                           conversaciones=conversaciones.values(),
                           contactos_disponibles=disponibles)


# ── Vista: Conversación individual ──
@comunicacion_bp.route('/chat/<int:contacto_id>')
@login_required
@permiso_requerido('Comunicaciones', nivel=1)  # ← nivel=1, lectura
def chat_conversacion(contacto_id):
    mi_person_id = current_user.PersonId
    contacto = db.session.get(Person, contacto_id)
    if not contacto:
        abort(404)

    u_contacto = EdugestUser.query.filter_by(PersonId=contacto_id).first()
    rol_map = {1: 'Administrador', 3: 'Profesor', 6: 'Apoderado'}
    contacto_rol = rol_map.get(u_contacto.RoleId, 'Usuario') if u_contacto else 'Usuario'

    mensajes = EdugestChatMessage.query.filter(
        or_(
            db.and_(
                EdugestChatMessage.SenderPersonId == mi_person_id,
                EdugestChatMessage.ReceiverPersonId == contacto_id
            ),
            db.and_(
                EdugestChatMessage.SenderPersonId == contacto_id,
                EdugestChatMessage.ReceiverPersonId == mi_person_id
            )
        )
    ).order_by(EdugestChatMessage.SentAt.asc()).all()

    changed = False
    for msg in mensajes:
        if msg.SenderPersonId == contacto_id and not msg.IsRead:
            msg.IsRead = True
            changed = True
    if changed:
        db.session.commit()

    # Verificar si tiene permiso de escritura para mostrar/ocultar el formulario
    puede_escribir = True
    if current_user.RoleId != 1:
        from app.models.edugest import EdugestModule, EdugestRolePermission
        modulo = EdugestModule.query.filter_by(ModuleName='Comunicaciones').first()
        if modulo:
            permiso = EdugestRolePermission.query.filter_by(
                RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
            ).first()
            if not permiso or permiso.PermissionLevel < 2:
                puede_escribir = False

    return render_template('comunicacion/chat_conversacion.html',
                           contacto=contacto,
                           contacto_rol=contacto_rol,
                           mensajes=mensajes,
                           mi_person_id=mi_person_id,
                           puede_escribir=puede_escribir)


# ── Acción: Enviar mensaje ──
@comunicacion_bp.route('/chat/<int:contacto_id>/enviar', methods=['POST'])
@login_required
@permiso_requerido('Comunicaciones', nivel=1)  # ← nivel=1 base
def chat_enviar(contacto_id):
    # Verificación inline de escritura
    from app.models.edugest import EdugestModule, EdugestRolePermission
    if current_user.RoleId != 1:
        modulo = EdugestModule.query.filter_by(ModuleName='Comunicaciones').first()
        if modulo:
            permiso = EdugestRolePermission.query.filter_by(
                RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
            ).first()
            if not permiso or permiso.PermissionLevel < 2:
                flash('No tienes permisos para enviar mensajes.', 'error')
                return redirect(url_for('comunicacion.chat_conversacion', contacto_id=contacto_id))

    texto = request.form.get('mensaje', '').strip()

    if not texto:
        flash('El mensaje no puede estar vacío.', 'error')
        return redirect(url_for('comunicacion.chat_conversacion', contacto_id=contacto_id))

    if len(texto) > 5000:
        flash('El mensaje es demasiado largo (máximo 5000 caracteres).', 'error')
        return redirect(url_for('comunicacion.chat_conversacion', contacto_id=contacto_id))

    contacto = db.session.get(Person, contacto_id)
    if not contacto:
        abort(404)

    nuevo = EdugestChatMessage(
        SenderPersonId=current_user.PersonId,
        ReceiverPersonId=contacto_id,
        MessageText=texto,
        SentAt=obtener_hora_chile(),
        IsRead=False
    )
    db.session.add(nuevo)
    db.session.commit()

    return redirect(url_for('comunicacion.chat_conversacion', contacto_id=contacto_id))


# ── API: Polling de mensajes nuevos (AJAX) ──
@comunicacion_bp.route('/chat/<int:contacto_id>/mensajes-nuevos')
@login_required
@permiso_requerido('Comunicaciones', nivel=1)
def chat_mensajes_nuevos(contacto_id):
    """Devuelve JSON con mensajes posteriores a 'desde' (MessageId)."""
    desde_id = request.args.get('desde', 0, type=int)
    mi_person_id = current_user.PersonId

    mensajes = EdugestChatMessage.query.filter(
        EdugestChatMessage.MessageId > desde_id,
        or_(
            db.and_(
                EdugestChatMessage.SenderPersonId == mi_person_id,
                EdugestChatMessage.ReceiverPersonId == contacto_id
            ),
            db.and_(
                EdugestChatMessage.SenderPersonId == contacto_id,
                EdugestChatMessage.ReceiverPersonId == mi_person_id
            )
        )
    ).order_by(EdugestChatMessage.SentAt.asc()).all()

    for msg in mensajes:
        if msg.SenderPersonId == contacto_id and not msg.IsRead:
            msg.IsRead = True
    if mensajes:
        db.session.commit()

    return jsonify([{
        'id': m.MessageId,
        'texto': m.MessageText,
        'enviado': m.SenderPersonId == mi_person_id,
        'hora': m.SentAt.strftime('%d/%m %H:%M') if m.SentAt else ''
    } for m in mensajes])