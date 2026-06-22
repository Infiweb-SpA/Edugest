import csv
from io import StringIO, BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app.database import db
from sqlalchemy import func
from app.models.mineduc import (
    Organization, OrganizationPersonRole, OrganizationCalendarSession,
    RoleAttendanceEvent, PersonIdentifier, Person, OrganizationRelationship
)
from app.models.edugest import (
    EdugestOrganizationConfig, EdugestCurriculumPlan, EdugestSessionAttendance, EdugestAssessmentInstrument
)
from app.models.edugest import EdugestStudentObservation, obtener_hora_chile
from app.modules.auth.routes import permiso_requerido, verificar_escritura

libro_digital_bp = Blueprint('libro_digital', __name__, url_prefix='/libro-digital')

# ============================================================================
# 1. CRUD DE GRADOS (Habilitar / Deshabilitar)
# ============================================================================
@libro_digital_bp.route('/grados', methods=['GET'])
@login_required
@permiso_requerido('Libro Digital', 1)
def listar_grados():

    # MINEDUC: RefOrganizationTypeId = 46 corresponde a "Grado"
    grados_base = Organization.query.filter_by(RefOrganizationTypeId=46).all()
    grados_data = []

    for g in grados_base:
        config = EdugestOrganizationConfig.query.filter_by(OrganizationId=g.OrganizationId).first()
        activo = config.IsActive if config else True

        total_estudiantes = db.session.query(func.count(OrganizationPersonRole.OrganizationPersonRoleId))\
            .join(Organization, OrganizationPersonRole.OrganizationId == Organization.OrganizationId)\
            .join(OrganizationRelationship, Organization.OrganizationId == OrganizationRelationship.OrganizationId)\
            .filter(
                OrganizationRelationship.ParentOrganizationId == g.OrganizationId,
                Organization.RefOrganizationTypeId == 21,
                OrganizationPersonRole.RoleId == 6,
                OrganizationPersonRole.ExitDate == None,
            ).scalar() or 0

        grados_data.append({
            'id': g.OrganizationId,
            'nombre': g.Name,
            'estudiantes': total_estudiantes,
            'activo': activo
        })

    return render_template('libro_digital/grados.html', grados=grados_data)


@libro_digital_bp.route('/grados/actualizar', methods=['POST'])
@login_required
@permiso_requerido('Libro Digital', 2)
def actualizar_grado():
    org_id = request.form.get('organization_id')
    is_active = request.form.get('is_active') == '1'

    config = EdugestOrganizationConfig.query.filter_by(OrganizationId=org_id).first()
    if not config:
        config = EdugestOrganizationConfig(OrganizationId=org_id, IsActive=is_active)
        db.session.add(config)
    else:
        config.IsActive = is_active

    db.session.commit()
    flash('Estado del grado actualizado.', 'success')
    return redirect(url_for('libro_digital.listar_grados'))


# ============================================================================
# 2. CRUD DE CURSOS / ASIGNATURAS (Vista Tarjetas)
# ============================================================================
@libro_digital_bp.route('/grados/<int:grado_id>/asignaturas')
@login_required
@permiso_requerido('Libro Digital', 1)
def asignaturas_por_grado(grado_id):
    grado = Organization.query.get_or_404(grado_id)

    asignaturas = Organization.query.filter(
        Organization.RefOrganizationTypeId == 22,
        Organization.OrganizationId.in_(
            db.session.query(OrganizationRelationship.OrganizationId)
            .filter(OrganizationRelationship.ParentOrganizationId == grado_id)
        )
    ).all()

    return render_template('libro_digital/asignaturas.html', asignaturas=asignaturas, grado=grado)


# ============================================================================
# 3. CRUD DE UNIDADES CURRICULARES
# ============================================================================
@libro_digital_bp.route('/asignatura/<int:org_id>/unidades', methods=['GET'])
@login_required
@permiso_requerido('Libro Digital', 1)
def ver_unidades(org_id):
    asignatura = Organization.query.get_or_404(org_id)

    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    planes = EdugestCurriculumPlan.query.filter_by(OrganizationId=org_id)\
                                        .order_by(EdugestCurriculumPlan.CreatedAt).all()

    # Determinar nivel de permisos del usuario actual
    nivel_permiso = 0
    if current_user.RoleId == 1:
        nivel_permiso = 2
    else:
        from app.models.edugest import EdugestModule, EdugestRolePermission
        modulo_eval = EdugestModule.query.filter_by(ModuleName='Evaluaciones').first()
        if modulo_eval:
            perm = EdugestRolePermission.query.filter_by(
                RoleId=current_user.RoleId, ModuleId=modulo_eval.ModuleId
            ).first()
            if perm:
                nivel_permiso = perm.PermissionLevel

    unidades_agrupadas = {}
    for plan in planes:
        if plan.UnitTitle not in unidades_agrupadas:
            unidades_agrupadas[plan.UnitTitle] = []

        if plan.Contenido or plan.Objetivo or plan.DetallesActividad:
            # Cargar evaluaciones: nivel 2 ve todas, nivel 1 solo las visibles
            if nivel_permiso >= 2:
                evaluaciones = EdugestAssessmentInstrument.query.filter_by(PlanId=plan.PlanId).all()
            else:
                evaluaciones = EdugestAssessmentInstrument.query.filter_by(
                    PlanId=plan.PlanId, IsVisible=True
                ).all()

            unidades_agrupadas[plan.UnitTitle].append({
                'plan': plan,
                'evaluaciones': evaluaciones
            })

    return render_template('libro_digital/unidades.html',
                           asignatura=asignatura,
                           unidades_agrupadas=unidades_agrupadas,
                           grado_id=grado_id)


@libro_digital_bp.route('/asignatura/<int:org_id>/unidades', methods=['POST'])
@login_required
@permiso_requerido('Libro Digital', 2)
def crud_unidades_post(org_id):
    asignatura = Organization.query.get_or_404(org_id)
    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    action = request.form.get('action')

    if action == 'crear_unidad':
        titulo_unidad = request.form.get('titulo_unidad')
        if titulo_unidad:
            nueva_unidad = EdugestCurriculumPlan(
                OrganizationId=org_id,
                UnitTitle=titulo_unidad
            )
            db.session.add(nueva_unidad)
            db.session.commit()
            flash(f'Unidad "{titulo_unidad}" creada con exito.', 'success')

    elif action == 'crear_clase':
        titulo_unidad = request.form.get('unit_title')
        nueva_clase = EdugestCurriculumPlan(
            OrganizationId=org_id,
            UnitTitle=titulo_unidad,
            Contenido=request.form.get('contenido'),
            Actividad=request.form.get('actividad'),
            DetallesActividad=request.form.get('detalles_actividad'),
            Objetivo=request.form.get('objetivo')
        )
        db.session.add(nueva_clase)
        db.session.commit()
        flash('Clase registrada correctamente en la unidad.', 'success')

    return redirect(url_for('libro_digital.ver_unidades', org_id=org_id))


# ============================================================================
# 4. LISTADO DE ESTUDIANTES Y REGISTRO DE CLASE (Firma)
# ============================================================================
@libro_digital_bp.route('/asignatura/<int:org_id>/clase', methods=['GET'])
@login_required
@permiso_requerido('Libro Digital', 1)
def registrar_clase_get(org_id):
    asignatura = Organization.query.get_or_404(org_id)

    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    letra = request.args.get('letra', 'A')

    curso = None
    if grado_id and letra:
        curso = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            Organization.ShortName == letra,
            OrganizationRelationship.ParentOrganizationId == grado_id
        ).first()

    lista_estudiantes = []
    if curso:
        alumnos_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=curso.OrganizationId, RoleId=6, ExitDate=None
        ).all()
        for rol in alumnos_roles:
            persona = Person.query.get(rol.PersonId)
            if persona:
                ident = PersonIdentifier.query.filter_by(
                    PersonId=persona.PersonId,
                    RefPersonIdentificationSystemId=51
                ).first()
                lista_estudiantes.append({
                    'rol_id': rol.OrganizationPersonRoleId,
                    'rut': ident.Identifier if ident else "Sin RUT",
                    'nombre': persona.FirstName,
                    'apellido_paterno': persona.LastName or '',
                    'apellido_materno': persona.SecondLastName or ''
                })

    letras_disponibles = []
    if grado_id:
        cursos = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            OrganizationRelationship.ParentOrganizationId == grado_id
        ).order_by(Organization.ShortName).all()
        letras_disponibles = [c.ShortName for c in cursos if c.ShortName]

    return render_template('libro_digital/lista_curso.html',
                           asignatura=asignatura,
                           estudiantes=lista_estudiantes,
                           grado_id=grado_id,
                           letra_actual=letra,
                           letras_disponibles=letras_disponibles)


@libro_digital_bp.route('/asignatura/<int:org_id>/clase', methods=['POST'])
@login_required
@permiso_requerido('Libro Digital', 2)
def registrar_clase_post(org_id):
    asignatura = Organization.query.get_or_404(org_id)

    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    letra = request.form.get('letra_curso', '')

    if not letra:
        flash('Debe seleccionar la letra del curso.', 'warning')
        return redirect(url_for('libro_digital.registrar_clase_get', org_id=org_id))

    curso = None
    if grado_id and letra:
        curso = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            Organization.ShortName == letra,
            OrganizationRelationship.ParentOrganizationId == grado_id
        ).first()

    lista_estudiantes = []
    if curso:
        alumnos_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=curso.OrganizationId, RoleId=6, ExitDate=None
        ).all()
        for rol in alumnos_roles:
            persona = Person.query.get(rol.PersonId)
            if persona:
                ident = PersonIdentifier.query.filter_by(
                    PersonId=persona.PersonId,
                    RefPersonIdentificationSystemId=51
                ).first()
                lista_estudiantes.append({
                    'rol_id': rol.OrganizationPersonRoleId,
                    'rut': ident.Identifier if ident else "Sin RUT",
                    'nombre': persona.FirstName,
                    'apellido_paterno': persona.LastName or '',
                    'apellido_materno': persona.SecondLastName or ''
                })

    hora_inicio = request.form.get('hora_inicio')
    hora_termino = request.form.get('hora_termino')
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    sesion = OrganizationCalendarSession(
        OrganizationId=org_id,
        BeginDate=fecha_hoy,
        EndDate=fecha_hoy,
        SessionStartTime=hora_inicio,
        SessionEndTime=hora_termino,
        Description=f"Clase registrada para Letra {letra}",
        MarkingTermIndicator=True,
        SchedulingTermIndicator=False
    )
    db.session.add(sesion)
    db.session.flush()

    for est in lista_estudiantes:
        estado = request.form.get(f"asistencia_{est['rol_id']}")
        if estado:
            db.session.add(EdugestSessionAttendance(
                OrganizationCalendarSessionId=sesion.OrganizationCalendarSessionId,
                OrganizationPersonRoleId=est['rol_id'],
                AttendanceStatusId=int(estado),
                HoraInicio=hora_inicio,
                HoraTermino=hora_termino
            ))

    db.session.commit()
    flash('Registro de clase y asistencia firmados exitosamente.', 'success')
    return redirect(url_for('libro_digital.asignaturas_por_grado', grado_id=grado_id))


# ============================================================================
# 5. EXPORTAR LISTA DE CURSO A EXCEL
# ============================================================================
@libro_digital_bp.route('/asignatura/<int:org_id>/exportar')
@login_required
@permiso_requerido('Libro Digital', 1)
def exportar_lista(org_id):
    asignatura = Organization.query.get_or_404(org_id)

    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    letra = request.args.get('letra', 'A')

    curso = None
    if grado_id and letra:
        curso = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            Organization.ShortName == letra,
            OrganizationRelationship.ParentOrganizationId == grado_id
        ).first()

    if not curso:
        flash(f'No existe el curso {letra} para este grado.', 'warning')
        return redirect(url_for('libro_digital.registrar_clase_get', org_id=org_id))

    alumnos_roles = OrganizationPersonRole.query.filter_by(
        OrganizationId=curso.OrganizationId, RoleId=6, ExitDate=None
    ).all()

    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    sesiones_hoy = OrganizationCalendarSession.query.filter(
        OrganizationCalendarSession.OrganizationId == org_id,
        OrganizationCalendarSession.BeginDate == fecha_hoy
    ).order_by(OrganizationCalendarSession.SessionStartTime).all()

    si = StringIO()
    writer = csv.writer(si, delimiter=';')

    writer.writerow([
        'Asignatura', 'Curso', 'Letra', 'Fecha Clase',
        'Hora Inicio', 'Hora Termino',
        'RUT', 'Apellido Paterno', 'Apellido Materno', 'Nombres',
        'Estado Asistencia'
    ])

    if not sesiones_hoy:
        for rol in alumnos_roles:
            persona = Person.query.get(rol.PersonId)
            if not persona:
                continue
            ident = PersonIdentifier.query.filter_by(
                PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
            ).first()
            rut = ident.Identifier if ident else "Sin RUT"

            writer.writerow([
                asignatura.Name, curso.Name, letra, fecha_hoy,
                'No registrada', 'No registrada',
                rut, persona.LastName, persona.SecondLastName or '',
                persona.FirstName, 'Sin registro'
            ])
    else:
        for sesion in sesiones_hoy:
            asistencias = EdugestSessionAttendance.query.filter_by(
                OrganizationCalendarSessionId=sesion.OrganizationCalendarSessionId
            ).all()
            asistencia_dict = {a.OrganizationPersonRoleId: a.AttendanceStatusId for a in asistencias}

            for rol in alumnos_roles:
                persona = Person.query.get(rol.PersonId)
                if not persona:
                    continue
                ident = PersonIdentifier.query.filter_by(
                    PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
                ).first()
                rut = ident.Identifier if ident else "Sin RUT"

                estado_id = asistencia_dict.get(rol.OrganizationPersonRoleId)
                estado_texto = {1: 'Presente', 2: 'Ausente', 3: 'Atrasado'}.get(estado_id, 'Sin registro')

                writer.writerow([
                    asignatura.Name, curso.Name, letra,
                    sesion.BeginDate,
                    sesion.SessionStartTime or 'No registrada',
                    sesion.SessionEndTime or 'No registrada',
                    rut, persona.LastName, persona.SecondLastName or '',
                    persona.FirstName, estado_texto
                ])

    output = BytesIO()
    output.write(si.getvalue().encode('utf-8-sig'))
    output.seek(0)

    nombre_archivo = f"Asistencia_{asignatura.Name.replace(' ', '_')}_{letra}_{fecha_hoy}.csv"

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={nombre_archivo}"}
    )


# ============================================================================
# CREAR ASIGNATURA MANUALMENTE
# ============================================================================
@libro_digital_bp.route('/grados/<int:grado_id>/asignaturas/crear', methods=['POST'])
@login_required
@permiso_requerido('Libro Digital', 2)
def crear_asignatura_manual(grado_id):
    nombre = request.form.get('nombre_asignatura', '').strip()
    codigo = request.form.get('codigo_asignatura', '').strip()

    if not nombre:
        flash('Debe ingresar un nombre para la asignatura.', 'warning')
        return redirect(url_for('libro_digital.asignaturas_por_grado', grado_id=grado_id))

    if not codigo:
        codigo = nombre[:3].upper()

    existente = Organization.query.join(
        OrganizationRelationship,
        Organization.OrganizationId == OrganizationRelationship.OrganizationId
    ).filter(
        Organization.Name == nombre,
        Organization.RefOrganizationTypeId == 22,
        OrganizationRelationship.ParentOrganizationId == grado_id
    ).first()

    if existente:
        flash(f'La asignatura "{nombre}" ya existe en este grado.', 'warning')
        return redirect(url_for('libro_digital.asignaturas_por_grado', grado_id=grado_id))

    nueva_asignatura = Organization(
        Name=nombre,
        ShortName=codigo,
        RefOrganizationTypeId=22
    )
    db.session.add(nueva_asignatura)
    db.session.flush()

    db.session.add(OrganizationRelationship(
        OrganizationId=nueva_asignatura.OrganizationId,
        ParentOrganizationId=grado_id
    ))

    db.session.commit()
    flash(f'Asignatura "{nombre}" creada y vinculada al grado exitosamente.', 'success')

    return redirect(url_for('libro_digital.asignaturas_por_grado', grado_id=grado_id))


# ============================================================================
# REGISTRAR ANOTACION
# ============================================================================
@libro_digital_bp.route('/anotacion/<int:rol_id>/<int:asignatura_id>', methods=['GET'])
@login_required
@permiso_requerido('Libro Digital', 1)
def ver_anotacion(rol_id, asignatura_id):
    estudiante_data = db.session.query(
        Person.FirstName, Person.LastName, Person.SecondLastName
    ).join(
        OrganizationPersonRole, OrganizationPersonRole.PersonId == Person.PersonId
    ).filter(
        OrganizationPersonRole.OrganizationPersonRoleId == rol_id
    ).first()

    asignatura = Organization.query.get_or_404(asignatura_id)

    historial = EdugestStudentObservation.query.filter_by(
        OrganizationPersonRoleId=rol_id,
        AsignaturaId=asignatura_id
    ).order_by(EdugestStudentObservation.FechaRegistro.desc()).all()

    return render_template(
        'libro_digital/anotaciones.html',
        estudiante=estudiante_data,
        asignatura=asignatura,
        historial=historial,
        rol_id=rol_id
    )


@libro_digital_bp.route('/anotacion/<int:rol_id>/<int:asignatura_id>/crear', methods=['POST'])
@login_required
@permiso_requerido('Libro Digital', 2)
def registrar_anotacion_post(rol_id, asignatura_id):
    tipo = request.form.get('tipo')
    detalle = request.form.get('detalle')

    if not tipo or not detalle:
        flash('Todos los campos son obligatorios.', 'warning')
    else:
        nueva_observacion = EdugestStudentObservation(
            OrganizationPersonRoleId=rol_id,
            AsignaturaId=asignatura_id,
            Tipo=tipo,
            Detalle=detalle,
            FechaRegistro=obtener_hora_chile()
        )
        db.session.add(nueva_observacion)
        db.session.commit()
        flash('Anotacion registrada exitosamente.', 'success')

    return redirect(url_for('libro_digital.ver_anotacion', rol_id=rol_id, asignatura_id=asignatura_id))