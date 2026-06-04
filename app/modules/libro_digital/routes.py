import csv
from io import StringIO, BytesIO
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from app.database import db
from app.models.mineduc import (
    Organization, OrganizationPersonRole, OrganizationCalendarSession,
    RoleAttendanceEvent, PersonIdentifier, Person, OrganizationRelationship
)
from app.models.edugest import (
    EdugestOrganizationConfig, EdugestCurriculumPlan, EdugestSessionAttendance
)

libro_digital_bp = Blueprint('libro_digital', __name__, url_prefix='/libro-digital')

# ============================================================================
# 1. CRUD DE GRADOS (Habilitar / Deshabilitar)
# ============================================================================
@libro_digital_bp.route('/grados', methods=['GET', 'POST'])
def listar_grados():
    if request.method == 'POST':
        org_id = request.form.get('organization_id')
        is_active = request.form.get('is_active') == '1'
        
        # Buscar configuración existente o crear una nueva
        config = EdugestOrganizationConfig.query.filter_by(OrganizationId=org_id).first()
        if not config:
            config = EdugestOrganizationConfig(OrganizationId=org_id, IsActive=is_active)
            db.session.add(config)
        else:
            config.IsActive = is_active
            
        db.session.commit()
        flash('Estado del grado actualizado.', 'success')
        return redirect(url_for('libro_digital.listar_grados'))

    # MINEDUC: RefOrganizationTypeId = 46 corresponde a "Grado"
    grados_base = Organization.query.filter_by(RefOrganizationTypeId=46).all()
    grados_data = []
    
    for g in grados_base:
        config = EdugestOrganizationConfig.query.filter_by(OrganizationId=g.OrganizationId).first()
        activo = config.IsActive if config else True
        
        # Contar estudiantes (Rol 6 = Estudiante) 
        # En una consulta real más profunda, cruzaríamos OrganizationRelationship. Por ahora es un count directo.
        total_estudiantes = db.session.query(OrganizationPersonRole).filter_by(RoleId=6, OrganizationId=g.OrganizationId).count()
        
        grados_data.append({
            'id': g.OrganizationId,
            'nombre': g.Name,
            'estudiantes': total_estudiantes,
            'activo': activo
        })

    return render_template('libro_digital/grados.html', grados=grados_data)


# ============================================================================
# 2. CRUD DE CURSOS / ASIGNATURAS (Vista Tarjetas)
# ============================================================================
@libro_digital_bp.route('/grados/<int:grado_id>/asignaturas')
def asignaturas_por_grado(grado_id):
    grado = Organization.query.get_or_404(grado_id)
    
    # BUSCAMOS DIRECTAMENTE LAS ASIGNATURAS QUE TIENEN COMO PADRE AL GRADO
    # Esto es más eficiente que el filtrado multinivel que tenías antes
    asignaturas = Organization.query.filter(
        Organization.RefOrganizationTypeId == 22,
        Organization.OrganizationId.in_(
            db.session.query(OrganizationRelationship.OrganizationId)
            .filter(OrganizationRelationship.ParentOrganizationId == grado_id)
        )
    ).all()
    
    # DEBUG: Si ves esto en tu consola, sabrás si la BD está vacía o el filtro falla
    print(f"DEBUG: Buscando asignaturas para grado {grado_id}. Encontradas: {len(asignaturas)}")

    return render_template('libro_digital/asignaturas.html', asignaturas=asignaturas, grado=grado)


# ============================================================================
# 3. CRUD DE UNIDADES CURRICULARES
# ============================================================================
@libro_digital_bp.route('/asignatura/<int:org_id>/unidades', methods=['GET', 'POST'])
def crud_unidades(org_id):
    asignatura = Organization.query.get_or_404(org_id)
     # ── FIX: obtener el grado al que pertenece esta asignatura ──
    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None
    # ────────────────────────────────────────────────────────────
    if request.method == 'POST':
        action = request.form.get('action')
        
        # 1. Crear el contenedor (La Unidad)
        if action == 'crear_unidad':
            titulo_unidad = request.form.get('titulo_unidad')
            if titulo_unidad:
                nueva_unidad = EdugestCurriculumPlan(
                    OrganizationId=org_id,
                    UnitTitle=titulo_unidad
                )
                db.session.add(nueva_unidad)
                db.session.commit()
                flash(f'Unidad "{titulo_unidad}" creada con éxito.', 'success')
                
        # 2. Crear el contenido (La Clase dentro de la Unidad)
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
            
        return redirect(url_for('libro_digital.crud_unidades', org_id=org_id))

    # --- LÓGICA GET ---
    # Obtenemos todos los planes ordenados por fecha de creación
    planes = EdugestCurriculumPlan.query.filter_by(OrganizationId=org_id).order_by(EdugestCurriculumPlan.CreatedAt).all()
    
    # Agrupamos las clases por el nombre de la Unidad
    unidades_agrupadas = {}
    for plan in planes:
        if plan.UnitTitle not in unidades_agrupadas:
            unidades_agrupadas[plan.UnitTitle] = [] # Inicializamos la unidad vacía
            
        # Si el registro tiene Contenido u Objetivo, es una "Clase" real, la agregamos a la lista
        if plan.Contenido or plan.Objetivo or plan.DetallesActividad:
            unidades_agrupadas[plan.UnitTitle].append(plan)

    return render_template('libro_digital/unidades.html', 
                           asignatura=asignatura, 
                           unidades_agrupadas=unidades_agrupadas,
                           grado_id=grado_id)


# ============================================================================
# 4. LISTADO DE ESTUDIANTES Y REGISTRO DE CLASE (Firma)
# ============================================================================
@libro_digital_bp.route('/asignatura/<int:org_id>/clase', methods=['GET', 'POST'])
def registrar_clase_dinamica(org_id):
    asignatura = Organization.query.get_or_404(org_id)

# ── OBTENER GRADO PADRE (Tipo 46) ──
    # Subimos un nivel: Asignatura(22) -> Grado(46)
    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None
    # ───────────────────────────────────

    # Listado de alumnos (Rol = 6) de esta asignatura
    alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=org_id, RoleId=6).all()
    
    # Obtener rut e información cruzando la tabla Person y PersonIdentifier
    lista_estudiantes = []
    for rol in alumnos_roles:
        persona = Person.query.get(rol.PersonId)
        identificador = PersonIdentifier.query.filter_by(PersonId=persona.PersonId, RefPersonIdentificationSystemId=51).first()
        rut = identificador.Identifier if identificador else "Sin RUT"
        
        lista_estudiantes.append({
            'rol_id': rol.OrganizationPersonRoleId,
            'rut': rut,
            'nombres': persona.FirstName,
            'apellidos': f"{persona.LastName} {persona.SecondLastName or ''}".strip()
        })
    
    if request.method == 'POST':
        hora_inicio = request.form.get('hora_inicio') # Ej: "08:00"
        hora_termino = request.form.get('hora_termino') # Ej: "10:00"
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        letra_curso = request.form.get('letra_curso') # Select de la letra (A, B, C...)
        
        # Crear la sesión de calendario (Bloque horario)
        sesion = OrganizationCalendarSession(
            OrganizationId=org_id,
            BeginDate=fecha_hoy,
            EndDate=fecha_hoy,
            SessionStartTime=hora_inicio,
            SessionEndTime=hora_termino,
            Description=f"Clase registrada para Letra {letra_curso}",
            MarkingTermIndicator=True,
            SchedulingTermIndicator=False
        )
        db.session.add(sesion)
        db.session.flush() # Flush para capturar el ID de la sesión antes del commit final
        
        # Registrar asistencia para cada estudiante en el bloque
        for est in lista_estudiantes:
            estado_asistencia = request.form.get(f"asistencia_{est['rol_id']}")
            if estado_asistencia:
                asistencia = EdugestSessionAttendance(
                    OrganizationCalendarSessionId=sesion.OrganizationCalendarSessionId,
                    OrganizationPersonRoleId=est['rol_id'],
                    RefAttendanceStatusId=int(estado_asistencia) # 1=Presente, 2=Ausente, 3=Atrasado
                )
                db.session.add(asistencia)
        
        db.session.commit()
        flash('Registro de clase y asistencia firmados exitosamente.', 'success')
        return redirect(url_for('libro_digital.asignaturas_por_grado'))

    return render_template('libro_digital/lista_curso.html', asignatura=asignatura, alumnos=lista_estudiantes, grado_id=grado_id)


# ============================================================================
# 5. EXPORTAR LISTA DE CURSO A EXCEL
# ============================================================================
@libro_digital_bp.route('/asignatura/<int:org_id>/exportar')
def exportar_lista(org_id):
    asignatura = Organization.query.get_or_404(org_id)
    alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=org_id, RoleId=6).all()
    
    # Preparamos el buffer en memoria
    si = StringIO()
    writer = csv.writer(si, delimiter=';')
    
    # Cabeceras del Excel
    writer.writerow(['RUT', 'Nombres', 'Apellido Paterno', 'Apellido Materno'])
    
    for rol in alumnos_roles:
        persona = Person.query.get(rol.PersonId)
        identificador = PersonIdentifier.query.filter_by(PersonId=persona.PersonId, RefPersonIdentificationSystemId=51).first()
        rut = identificador.Identifier if identificador else "Sin RUT"
        
        writer.writerow([
            rut, 
            persona.FirstName, 
            persona.LastName, 
            persona.SecondLastName or ''
        ])
        
    output = BytesIO()
    output.write(si.getvalue().encode('utf-8-sig')) # El BOM utf-8-sig obliga a Excel a reconocer tildes y ñ
    output.seek(0)
    
    nombre_archivo = f"Lista_{asignatura.Name.replace(' ', '_')}.csv"
    
    return Response(
        output, 
        mimetype="text/csv", 
        headers={"Content-Disposition": f"attachment;filename={nombre_archivo}"}
    )