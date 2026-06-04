from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import db
from app.models import (
    EdugestAssessmentInstrument,
    EdugestAssessmentQuestion,
    EdugestCurriculumPlan,
    EdugestQuestionOption,
    EdugestStudentResponse,
    Organization,
    OrganizationPersonRole,
    OrganizationRelationship,
    Person,
    PersonIdentifier
)

evaluaciones_bp = Blueprint('evaluaciones', __name__, url_prefix='/evaluaciones')


# ============================================================================
# PASO 1: LISTAR GRADOS (igual que Libro Digital)
# ============================================================================
@evaluaciones_bp.route('/grados')
def listar_grados():
    """Muestra grados habilitados para filtrar evaluaciones"""
    from app.models.edugest import EdugestOrganizationConfig
    
    grados_base = Organization.query.filter_by(RefOrganizationTypeId=46).all()
    grados_data = []
    
    for g in grados_base:
        config = EdugestOrganizationConfig.query.filter_by(OrganizationId=g.OrganizationId).first()
        activo = config.IsActive if config else True
        
        # Contar asignaturas con evaluaciones
        total_evals = EdugestAssessmentInstrument.query.join(
            Organization, 
            EdugestAssessmentInstrument.OrganizationId == Organization.OrganizationId
        ).join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            OrganizationRelationship.ParentOrganizationId == g.OrganizationId
        ).count()
        
        grados_data.append({
            'id': g.OrganizationId,
            'nombre': g.Name,
            'activo': activo,
            'evaluaciones': total_evals
        })
    
    return render_template('evaluaciones/grados.html', grados=grados_data)


# ============================================================================
# PASO 2: ASIGNATURAS DEL GRADO
# ============================================================================
@evaluaciones_bp.route('/grado/<int:grado_id>/asignaturas')
def asignaturas_por_grado(grado_id):
    grado = Organization.query.get_or_404(grado_id)
    
    # Asignaturas vinculadas a este grado
    asignaturas = Organization.query.join(
        OrganizationRelationship,
        Organization.OrganizationId == OrganizationRelationship.OrganizationId
    ).filter(
        Organization.RefOrganizationTypeId == 22,
        OrganizationRelationship.ParentOrganizationId == grado_id
    ).all()
    
    # Para cada asignatura, contar evaluaciones existentes
    asignaturas_data = []
    for asig in asignaturas:
        total_evals = EdugestAssessmentInstrument.query.filter_by(
            OrganizationId=asig.OrganizationId
        ).count()
        
        asignaturas_data.append({
            'asignatura': asig,
            'evaluaciones': total_evals
        })
    
    return render_template('evaluaciones/asignaturas.html', 
                           grado=grado, 
                           asignaturas_data=asignaturas_data)


# ============================================================================
# PASO 3: UNIDADES Y CLASES DE LA ASIGNATURA
# ============================================================================
@evaluaciones_bp.route('/asignatura/<int:org_id>/unidades')
def unidades_asignatura(org_id):
    asignatura = Organization.query.get_or_404(org_id)
    
    # Obtener grado para breadcrumb
    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None
    
    # Unidades (planes) de esta asignatura
    planes = EdugestCurriculumPlan.query.filter_by(OrganizationId=org_id).order_by(
        EdugestCurriculumPlan.CreatedAt
    ).all()
    
    # Agrupar por unidad
    unidades_agrupadas = {}
    for plan in planes:
        if plan.UnitTitle not in unidades_agrupadas:
            unidades_agrupadas[plan.UnitTitle] = {'clases': [], 'plan_id': plan.PlanId}
        
        if plan.Contenido or plan.Objetivo or plan.DetallesActividad:
            # Buscar evaluaciones vinculadas a esta clase
            evals = EdugestAssessmentInstrument.query.filter_by(PlanId=plan.PlanId).all()
            unidades_agrupadas[plan.UnitTitle]['clases'].append({
                'plan': plan,
                'evaluaciones': evals
            })
    
    return render_template('evaluaciones/unidades.html',
                           asignatura=asignatura,
                           grado_id=grado_id,
                           unidades_agrupadas=unidades_agrupadas)


# ============================================================================
# PASO 4: CREAR EVALUACIÓN VINCULADA A UNA CLASE
# ============================================================================
@evaluaciones_bp.route('/clase/<int:plan_id>/nueva-evaluacion', methods=['GET', 'POST'])
def crear_evaluacion_clase(plan_id):
    """Crea evaluación vinculada a una clase específica (PlanId)"""
    plan = EdugestCurriculumPlan.query.get_or_404(plan_id)
    asignatura = Organization.query.get_or_404(plan.OrganizationId)
    
    # Obtener grado
    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=asignatura.OrganizationId
    ).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None
    
    # Obtener unidades de esta asignatura para el select
    unidades = EdugestCurriculumPlan.query.filter_by(
        OrganizationId=asignatura.OrganizationId
    ).order_by(EdugestCurriculumPlan.CreatedAt).all()
    
    # Obtener clases de la unidad actual para el select
    clases = EdugestCurriculumPlan.query.filter_by(
        OrganizationId=asignatura.OrganizationId,
        UnitTitle=plan.UnitTitle
    ).filter(
        EdugestCurriculumPlan.Contenido.isnot(None) | 
        EdugestCurriculumPlan.Objetivo.isnot(None)
    ).all()
    
    if request.method == 'POST':
        titulo = request.form.get('title')
        plan_id_selected = request.form.get('plan_id')  # Puede cambiar la clase
        is_digital = 'is_digital' in request.form
        
        nuevo_ins = EdugestAssessmentInstrument(
            Title=titulo,
            OrganizationId=asignatura.OrganizationId,
            PlanId=plan_id_selected if plan_id_selected else plan_id,
            IsDigital=is_digital,
            IsVisible=False
        )
        db.session.add(nuevo_ins)
        db.session.commit()
        
        flash("Evaluación creada y vinculada a la clase.", "success")
        return redirect(url_for('evaluaciones.unidades_asignatura', org_id=asignatura.OrganizationId))
    
    return render_template('evaluaciones/crear_evaluacion.html',
                           plan=plan,
                           asignatura=asignatura,
                           grado_id=grado_id,
                           unidades=unidades,
                           clases=clases)


# ============================================================================
# RUTAS EXISTENTES (mantenidas con ajustes mínimos)
# ============================================================================

@evaluaciones_bp.route('/')
def index():
    """Redirige al nuevo flujo de grados"""
    return redirect(url_for('evaluaciones.listar_grados'))


@evaluaciones_bp.route('/asignatura/<int:org_id>/nuevo', methods=['GET', 'POST'])
def crear_instrumento(org_id):
    """Legacy: mantiene compatibilidad, redirige al nuevo flujo"""
    return redirect(url_for('evaluaciones.asignaturas_por_grado', grado_id=1))


@evaluaciones_bp.route('/disenar_preguntas/<int:inst_id>', methods=['GET', 'POST'])
def disenar_preguntas(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)

    if request.method == 'POST':
        nueva_pregunta = EdugestAssessmentQuestion(
            InstrumentId=inst_id,
            QuestionText=request.form.get('question_text'),
            QuestionType=request.form.get('question_type', 'Alternativa'),
            Points=int(request.form.get('points', 1))
        )
        db.session.add(nueva_pregunta)
        db.session.flush()

        correcta_key = request.form.get('correcta')

        for i in range(1, 5):
            texto_opcion = request.form.get(f'opcion_{i}')
            if not texto_opcion:
                continue

            es_correcta = (correcta_key == f'opcion_{i}')
            opcion = EdugestQuestionOption(
                QuestionId=nueva_pregunta.QuestionId,
                OptionText=texto_opcion,
                IsCorrect=es_correcta
            )
            db.session.add(opcion)

        db.session.commit()
        flash('Pregunta y alternativas guardadas correctamente.', 'success')
        return redirect(url_for('evaluaciones.disenar_preguntas', inst_id=inst_id))

    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    for p in preguntas:
        p.opciones_list = EdugestQuestionOption.query.filter_by(QuestionId=p.QuestionId).all()

    return render_template('evaluaciones/disenar_preguntas.html',
                           instrumento=instrumento,
                           preguntas=preguntas)


@evaluaciones_bp.route('/rendir/<int:inst_id>/<int:alumno_id>', methods=['GET', 'POST'])
def rendir(inst_id, alumno_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    alumno = Person.query.get_or_404(alumno_id)

    # FIX: Buscar matrícula en el CURSO (Tipo 21), no en la asignatura
    # Primero obtenemos el grado de la asignatura
    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=instrumento.OrganizationId
    ).first()
    
    # Buscamos cursos hijos del grado
    cursos = []
    if relacion_grado:
        cursos = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            OrganizationRelationship.ParentOrganizationId == relacion_grado.ParentOrganizationId
        ).all()
    
    # Buscar matrícula en alguno de esos cursos
    matricula = None
    for curso in cursos:
        mat = OrganizationPersonRole.query.filter_by(
            PersonId=alumno_id,
            OrganizationId=curso.OrganizationId,
            RoleId=6
        ).first()
        if mat:
            matricula = mat
            break
    
    if not matricula:
        flash('El estudiante no está matriculado en ningún curso de esta asignatura.', 'danger')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    preguntas_data = []
    for q in preguntas:
        opciones = EdugestQuestionOption.query.filter_by(QuestionId=q.QuestionId).all()
        preguntas_data.append({'pregunta': q, 'opciones': opciones})

    if request.method == 'POST':
        for item in preguntas_data:
            q = item['pregunta']
            campo = f'pregunta_{q.QuestionId}'
            opcion_id_str = request.form.get(campo)
            if not opcion_id_str:
                continue

            opcion_id = int(opcion_id_str)
            opcion = EdugestQuestionOption.query.get(opcion_id)
            puntaje = q.Points if (opcion and opcion.IsCorrect) else 0

            respuesta = EdugestStudentResponse.query.filter_by(
                OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
                QuestionId=q.QuestionId
            ).first()

            if respuesta:
                respuesta.SelectedOptionId = opcion_id
                respuesta.ScoreEarned = puntaje
            else:
                nueva = EdugestStudentResponse(
                    OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
                    QuestionId=q.QuestionId,
                    SelectedOptionId=opcion_id,
                    ScoreEarned=puntaje
                )
                db.session.add(nueva)

        db.session.commit()
        flash('Evaluación enviada y calificada automáticamente.', 'success')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    return render_template('evaluaciones/rendir.html',
                           instrumento=instrumento,
                           alumno=alumno,
                           preguntas_data=preguntas_data)


@evaluaciones_bp.route('/instrumento/<int:inst_id>/resultados')
def resultados(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    puntaje_maximo = sum(p.Points for p in preguntas) or 1

    # FIX: Buscar estudiantes en los CURSOS del grado, no en la asignatura
    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=instrumento.OrganizationId
    ).first()
    
    matriculas = []
    if relacion_grado:
        cursos = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            OrganizationRelationship.ParentOrganizationId == relacion_grado.ParentOrganizationId
        ).all()
        
        for curso in cursos:
            mats = OrganizationPersonRole.query.filter_by(
                OrganizationId=curso.OrganizationId,
                RoleId=6
            ).all()
            matriculas.extend(mats)

    tabla_resultados = []
    vistos = set()

    for matricula in matriculas:
        if matricula.PersonId in vistos:
            continue
        vistos.add(matricula.PersonId)
        
        alumno = matricula.person

        identificador = PersonIdentifier.query.filter_by(
            PersonId=alumno.PersonId,
            RefPersonIdentificationSystemId=51
        ).first()
        rut = identificador.Identifier if identificador else 'Sin RUT'

        respuestas = (
            EdugestStudentResponse.query
            .filter_by(OrganizationPersonRoleId=matricula.OrganizationPersonRoleId)
            .join(EdugestAssessmentQuestion)
            .filter(EdugestAssessmentQuestion.InstrumentId == inst_id)
            .all()
        )

        puntaje_obtenido = sum(r.ScoreEarned or 0 for r in respuestas)

        if puntaje_maximo > 0:
            nota = round(1 + (puntaje_obtenido / puntaje_maximo) * 6, 1)
        else:
            nota = 1.0

        if not respuestas:
            estado = 'No Rendido'
        elif nota >= 4.0:
            estado = 'Aprobado'
        else:
            estado = 'Reprobado'

        tabla_resultados.append({
            'alumno': alumno,
            'rut': rut,
            'puntaje': puntaje_obtenido,
            'puntaje_maximo': puntaje_maximo,
            'nota': nota,
            'estado': estado
        })

    tabla_resultados.sort(key=lambda x: x['alumno'].LastName)

    return render_template('evaluaciones/resultados.html',
                           instrumento=instrumento,
                           tabla_resultados=tabla_resultados)


@evaluaciones_bp.route('/instrumento/<int:inst_id>/visibilidad', methods=['POST'])
def cambiar_visibilidad(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    instrumento.IsVisible = not instrumento.IsVisible
    db.session.commit()
    estado = "publicado" if instrumento.IsVisible else "ocultado"
    flash(f"El instrumento ha sido {estado} correctamente.", "success")
    return redirect(url_for('evaluaciones.unidades_asignatura', org_id=instrumento.OrganizationId))