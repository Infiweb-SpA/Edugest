from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship, OrganizationPersonRole
)
from app.models.edugest import EdugestRole

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

    return render_template('portada/bienvenida.html',
                           persona=persona,
                           rut=ident.Identifier if ident else 'Sin RUT',
                           rol_nombre=rol_nombre,
                           curso_info=curso_info,
                           asignaturas=asignaturas_data)