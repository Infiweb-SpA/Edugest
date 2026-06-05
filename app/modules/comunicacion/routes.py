from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import db
from app.models.mineduc import (
    Person, Organization, OrganizationPersonRole, PersonRelationship,
    PersonTelephone, PersonEmailAddress, PersonAddress, PersonIdentifier,
    OrganizationRelationship
)
from app.models.edugest import EdugestAnnouncement
from sqlalchemy import or_

comunicacion_bp = Blueprint('comunicacion', __name__, url_prefix='/comunicacion')


# =============================================================================
# VISTA UNIFICADA: ANUNCIOS + CONTACTOS
# =============================================================================

@comunicacion_bp.route('/anuncios')
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
        Organization.RefOrganizationTypeId == 21
    ).distinct().order_by(Organization.Name).all()
    
    # Enriquecer cursos con nombre de grado padre
    for c in cursos:
        rel = OrganizationRelationship.query.filter_by(OrganizationId=c.OrganizationId).first()
        c.grado_nombre = ''
        if rel:
            grado = db.session.get(Organization, rel.ParentOrganizationId)
            if grado:
                c.grado_nombre = grado.Name
    
    contactos_data = []
    if curso_id_contacto:
        estudiantes_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=curso_id_contacto, RoleId=6
        ).join(Person).order_by(Person.LastName, Person.FirstName).all()
        
        for er in estudiantes_roles:
            estudiante = er.person
            
            # Apoderado principal (RefPersonRelationshipId = 31)
            relacion = PersonRelationship.query.filter_by(
                PersonId=estudiante.PersonId, RefPersonRelationshipId=31
            ).first()
            
            apoderado = None
            telefono_apoderado = None
            if relacion:
                apoderado = db.session.get(Person, relacion.RelatedPersonId)
                if apoderado:
                    pt = PersonTelephone.query.filter_by(PersonId=apoderado.PersonId).first()
                    telefono_apoderado = pt.TelephoneNumber if pt else None
            
            contactos_data.append({
                'estudiante': estudiante,
                'apoderado': apoderado,
                'telefono_apoderado': telefono_apoderado,
                'rol_id': er.OrganizationPersonRoleId
            })
    
    return render_template('comunicacion/anuncios.html',
                         anuncios=anuncios_list, 
                         cursos=cursos, 
                         curso_id_anuncio=curso_id_anuncio,
                         curso_id_contacto=curso_id_contacto,
                         contactos=contactos_data)


@comunicacion_bp.route('/anuncios/nuevo', methods=['POST'])
def nuevo_anuncio():
    titulo = request.form.get('titulo', '').strip()
    contenido = request.form.get('contenido', '').strip()
    curso_id = request.form.get('curso_id', type=int)
    
    if not titulo or not contenido:
        flash('El título y contenido son obligatorios.', 'error')
        return redirect(url_for('comunicacion.anuncios'))
    
    # Buscar un usuario administrador (RoleId 1 o 2) como sender
    sender = db.session.query(Person).join(
        OrganizationPersonRole, Person.PersonId == OrganizationPersonRole.PersonId
    ).filter(OrganizationPersonRole.RoleId.in_([1, 2])).first()
    
    # Usar hora local de Chile (UTC-4/UTC-3)
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
def contactos():
    curso_id = request.args.get('curso_id', type=int)
    
    # Cursos disponibles (tipo 21 = Course / letra)
    cursos = db.session.query(Organization).join(
        OrganizationPersonRole, Organization.OrganizationId == OrganizationPersonRole.OrganizationId
    ).filter(
        OrganizationPersonRole.RoleId == 6,
        Organization.RefOrganizationTypeId == 21
    ).distinct().order_by(Organization.Name).all()
    
    # Enriquecer cursos con nombre de grado padre si existe
    for c in cursos:
        rel = OrganizationRelationship.query.filter_by(OrganizationId=c.OrganizationId).first()
        c.grado_nombre = ''
        if rel:
            grado = db.session.get(Organization, rel.ParentOrganizationId)
            if grado:
                c.grado_nombre = grado.Name
    
    contactos_data = []
    if curso_id:
        estudiantes_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=curso_id, RoleId=6
        ).join(Person).order_by(Person.LastName, Person.FirstName).all()
        
        for er in estudiantes_roles:
            estudiante = er.person
            
            # Apoderado principal (RefPersonRelationshipId = 31 según mapeo MINEDUC)
            relacion = PersonRelationship.query.filter_by(
                PersonId=estudiante.PersonId, RefPersonRelationshipId=31
            ).first()
            
            apoderado = None
            telefono_apoderado = None
            if relacion:
                apoderado = db.session.get(Person, relacion.RelatedPersonId)
                if apoderado:
                    pt = PersonTelephone.query.filter_by(PersonId=apoderado.PersonId).first()
                    telefono_apoderado = pt.TelephoneNumber if pt else None
            
            contactos_data.append({
                'estudiante': estudiante,
                'apoderado': apoderado,
                'telefono_apoderado': telefono_apoderado,
                'rol_id': er.OrganizationPersonRoleId
            })
    
    return render_template('comunicacion/contactos.html',
                         cursos=cursos, contactos=contactos_data, curso_id=curso_id)


@comunicacion_bp.route('/contacto/<int:person_id>')
def contacto_detalle(person_id):
    estudiante = db.session.get(Person, person_id)
    if not estudiante:
        from flask import abort
        abort(404)
    
    # Curso actual
    rol_estudiante = OrganizationPersonRole.query.filter_by(
        PersonId=person_id, RoleId=6
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
    
    # Apoderado (RefPersonRelationshipId = 31)
    relacion = PersonRelationship.query.filter_by(
        PersonId=person_id, RefPersonRelationshipId=31
    ).first()
    
    apoderado = None
    tel_apod = None
    email_apod = None
    dir_apod = None
    wa_link = None
    
    if relacion:
        apoderado = db.session.get(Person, relacion.RelatedPersonId)
        if apoderado:
            pt = PersonTelephone.query.filter_by(PersonId=apoderado.PersonId).first()
            if pt:
                tel_apod = pt.TelephoneNumber
                # Generar enlace wa.me limpio
                num_limpio = ''.join(c for c in tel_apod if c.isdigit())
                if num_limpio:
                    # Normalizar número chileno
                    if num_limpio.startswith('569') and len(num_limpio) == 11:
                        num_limpio = '56' + num_limpio[3:]
                    elif num_limpio.startswith('9') and len(num_limpio) == 9:
                        num_limpio = '56' + num_limpio
                    elif num_limpio.startswith('56') and len(num_limpio) == 11:
                        pass  # Ya está correcto
                    wa_link = f"https://wa.me/{num_limpio}"
            
            em = PersonEmailAddress.query.filter_by(PersonId=apoderado.PersonId).first()
            email_apod = em.EmailAddress if em else None
            
            pa = PersonAddress.query.filter_by(PersonId=apoderado.PersonId).first()
            if pa:
                from app.models.mineduc import RefCounty
                comuna = db.session.get(RefCounty, pa.RefCountyId) if pa.RefCountyId else None
                dir_apod = {
                    'calle': pa.StreetNumberAndName,
                    'comuna': comuna.Description if comuna else ''
                }
    
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
                         wa_link=wa_link)