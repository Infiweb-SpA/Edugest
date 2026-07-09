from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationPersonRole, PersonRelationship
)
from app.models.edugest import EdugestRole
from app.models.EdugestCalendar import EdugestCalendarEvent  # ← NUEVO
from datetime import date  # ← NUEVO

portada_bp = Blueprint('portada', __name__, url_prefix='/portada')


@portada_bp.route('/bienvenida')
@login_required
def bienvenida():
    # Datos de la persona vinculada al usuario
    persona = Person.query.get(current_user.PersonId)
    ident = PersonIdentifier.query.filter_by(
        PersonId=current_user.PersonId, RefPersonIdentificationSystemId=51
    ).first()

    # Nombre del rol
    rol = EdugestRole.query.get(current_user.RoleId)
    rol_nombre = rol.RoleName if rol else 'Usuario'

    # Datos del estudiante (solo si roleId=6)
    curso_info = None
    asignaturas_data = []
    hijos_data = []  # ← NUEVO: lista de hijos para apoderado

    # ================================================================
    # CASO A: Estudiante (RoleId=6)
    # ================================================================
    if current_user.RoleId == 6:
        # Buscar matrícula activa en un curso (tipo 21)
        matriculas = OrganizationPersonRole.query.filter_by(
            PersonId=current_user.PersonId,
            RoleId=6,
            ExitDate=None
        ).all()

        for mat in matriculas:
            org = Organization.query.get(mat.OrganizationId)
            if org and org.RefOrganizationTypeId == 21:
                # Encontró el curso
                curso_info = {
                    'nombre': org.Name,
                    'letra': org.ShortName or ''
                }

                # Buscar el grado padre (tipo 46)
                relacion = OrganizationRelationship.query.filter_by(
                    OrganizationId=org.OrganizationId
                ).first()

                grado = None
                if relacion:
                    grado = Organization.query.get(relacion.ParentOrganizationId)

                if grado:
                    curso_info['grado'] = grado.Name

                    # Buscar asignaturas del grado (tipo 22)
                    asignaturas = Organization.query.join(
                        OrganizationRelationship,
                        Organization.OrganizationId == OrganizationRelationship.OrganizationId
                    ).filter(
                        OrganizationRelationship.ParentOrganizationId == grado.OrganizationId,
                        Organization.RefOrganizationTypeId == 22
                    ).order_by(Organization.Name).all()

                    for asig in asignaturas:
                        asignaturas_data.append({
                            'org_id': asig.OrganizationId,
                            'nombre': asig.Name
                        })

                break  # Solo el primer curso activo

    # ================================================================
    # CASO B: Apoderado/Tutor — buscar hijos vinculados
    # ================================================================
    else:
        # PersonRelationship: PersonId = estudiante, RelatedPersonId = apoderado
        relaciones = PersonRelationship.query.filter_by(
            RelatedPersonId=current_user.PersonId
        ).all()

        for rel in relaciones:
            # Verificar que el vinculado sea un alumno con matrícula activa
            rol_hijo = OrganizationPersonRole.query.filter_by(
                PersonId=rel.PersonId,
                RoleId=6,
                ExitDate=None
            ).first()

            if not rol_hijo:
                continue

            persona_hijo = Person.query.get(rel.PersonId)
            if not persona_hijo:
                continue

            # Obtener RUT del hijo
            ident_hijo = PersonIdentifier.query.filter_by(
                PersonId=persona_hijo.PersonId,
                RefPersonIdentificationSystemId=51
            ).first()

            # Obtener información del curso y grado
            curso = Organization.query.get(rol_hijo.OrganizationId)
            relacion_curso = OrganizationRelationship.query.filter_by(
                OrganizationId=rol_hijo.OrganizationId
            ).first()
            grado = Organization.query.get(
                relacion_curso.ParentOrganizationId
            ) if relacion_curso else None

            # Obtener asignaturas del grado del hijo
            asignaturas_hijo = []
            if grado:
                asignaturas_org = Organization.query.join(
                    OrganizationRelationship,
                    Organization.OrganizationId == OrganizationRelationship.OrganizationId
                ).filter(
                    OrganizationRelationship.ParentOrganizationId == grado.OrganizationId,
                    Organization.RefOrganizationTypeId == 22
                ).order_by(Organization.Name).all()

                for asig in asignaturas_org:
                    asignaturas_hijo.append({
                        'org_id': asig.OrganizationId,
                        'nombre': asig.Name
                    })

            hijos_data.append({
                'person_id': persona_hijo.PersonId,
                'nombre': (
                    f"{persona_hijo.FirstName} "
                    f"{persona_hijo.LastName or ''} "
                    f"{persona_hijo.SecondLastName or ''}"
                ).strip(),
                'rut': ident_hijo.Identifier if ident_hijo else 'Sin RUT',
                'curso_id': rol_hijo.OrganizationId,
                'curso_nombre': (
                    f"{grado.Name if grado else ''} "
                    f"{curso.Name if curso else ''}"
                ).strip(),
                'letra': (curso.ShortName if curso else '') or '',
                'grado_nombre': grado.Name if grado else '',
                'asignaturas': asignaturas_hijo
            })

        # ← NUEVO: Próximos eventos globales del calendario
    hoy = date.today()
    proximos_eventos = EdugestCalendarEvent.query.filter(
        EdugestCalendarEvent.EventDate >= hoy,
        EdugestCalendarEvent.TargetOrganizationId.is_(None)
    ).order_by(EdugestCalendarEvent.EventDate).limit(5).all()

    return render_template('portada/bienvenida.html',
                           persona=persona,
                           rut=ident.Identifier if ident else 'Sin RUT',
                           rol_nombre=rol_nombre,
                           curso_info=curso_info,
                           asignaturas=asignaturas_data,
                           hijos=hijos_data,
                           proximos_eventos=proximos_eventos)  # ← NUEVO