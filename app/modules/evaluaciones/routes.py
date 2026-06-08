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


import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'app/static/uploads/preguntas'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@evaluaciones_bp.route('/disenar_preguntas/<int:inst_id>', methods=['GET', 'POST'])
def disenar_preguntas(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)

    if request.method == 'POST':
        tipo = request.form.get('question_type', 'Alternativa')
        puntos = int(request.form.get('points', 1))
        
        # Procesar imagen
        imagen_url = None
        if 'question_image' in request.files:
            file = request.files['question_image']
            if file and file.filename and allowed_file(file.filename):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename = secure_filename(f"{inst_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                imagen_url = f"/static/uploads/preguntas/{filename}"

        # Crear pregunta base
        nueva_pregunta = EdugestAssessmentQuestion(
            InstrumentId=inst_id,
            QuestionText=request.form.get('question_text'),
            QuestionType=tipo,
            Points=puntos,
            ImageUrl=imagen_url
        )
        db.session.add(nueva_pregunta)
        db.session.flush()

        # Crear opciones según tipo
        if tipo == 'Alternativa':
            correcta_key = request.form.get('correcta')
            for i in range(1, 5):
                texto = request.form.get(f'opcion_{i}')
                if texto:
                    db.session.add(EdugestQuestionOption(
                        QuestionId=nueva_pregunta.QuestionId,
                        OptionText=texto,
                        IsCorrect=(correcta_key == f'opcion_{i}')
                    ))
        
        elif tipo == 'VerdaderoFalso':
            vf = request.form.get('vf_correcta')
            db.session.add(EdugestQuestionOption(
                QuestionId=nueva_pregunta.QuestionId,
                OptionText='Verdadero',
                IsCorrect=(vf == 'Verdadero')
            ))
            db.session.add(EdugestQuestionOption(
                QuestionId=nueva_pregunta.QuestionId,
                OptionText='Falso',
                IsCorrect=(vf == 'Falso')
            ))
        
        elif tipo == 'Desarrollo':
            # Sin opciones, solo marca de tipo
            pass
        
        elif tipo == 'RelacionColumnas':
            for i in range(1, 4):
                izq = request.form.get(f'rel_izq_{i}')
                der = request.form.get(f'rel_der_{i}')
                if izq and der:
                    db.session.add(EdugestQuestionOption(
                        QuestionId=nueva_pregunta.QuestionId,
                        OptionText=izq,
                        MatchText=der,
                        IsCorrect=True,
                        OrderIndex=i
                    ))
        
        elif tipo == 'Completar':
            for i in range(1, 4):
                resp = request.form.get(f'comp_resp_{i}')
                if resp:
                    db.session.add(EdugestQuestionOption(
                        QuestionId=nueva_pregunta.QuestionId,
                        OptionText=resp,
                        IsCorrect=True,
                        OrderIndex=i
                    ))

        db.session.commit()
        flash('Pregunta guardada correctamente.', 'success')
        return redirect(url_for('evaluaciones.disenar_preguntas', inst_id=inst_id))

    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    for p in preguntas:
        p.opciones_list = EdugestQuestionOption.query.filter_by(QuestionId=p.QuestionId).order_by(EdugestQuestionOption.OrderIndex).all()

    return render_template('evaluaciones/disenar_preguntas.html',
                           instrumento=instrumento,
                           preguntas=preguntas)

# ============================================================================
#funcioneshelper
# ============================================================================
def _guardar_respuesta(matricula, pregunta, opcion_id, puntaje):
    """Guarda o actualiza respuesta para preguntas con opción"""
    respuesta = EdugestStudentResponse.query.filter_by(
        OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
        QuestionId=pregunta.QuestionId
    ).first()

    if respuesta:
        respuesta.SelectedOptionId = opcion_id
        respuesta.ScoreEarned = puntaje
    else:
        nueva = EdugestStudentResponse(
            OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
            QuestionId=pregunta.QuestionId,
            SelectedOptionId=opcion_id,
            ScoreEarned=puntaje
        )
        db.session.add(nueva)


def _guardar_respuesta_desarrollo(matricula, pregunta, texto):
    """Guarda respuesta de desarrollo (sin auto-corrección)"""
    respuesta = EdugestStudentResponse.query.filter_by(
        OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
        QuestionId=pregunta.QuestionId
    ).first()

    if respuesta:
        respuesta.TextResponse = texto
        respuesta.ScoreEarned = None
    else:
        nueva = EdugestStudentResponse(
            OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
            QuestionId=pregunta.QuestionId,
            TextResponse=texto,
            ScoreEarned=None
        )
        db.session.add(nueva)


@evaluaciones_bp.route('/rendir/<int:inst_id>/<int:alumno_id>', methods=['GET', 'POST'])
def rendir(inst_id, alumno_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    alumno = Person.query.get_or_404(alumno_id)

    # FIX: Buscar matrícula en el CURSO (Tipo 21), no en la asignatura
    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=instrumento.OrganizationId
    ).first()
    
    cursos = []
    if relacion_grado:
        cursos = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            OrganizationRelationship.ParentOrganizationId == relacion_grado.ParentOrganizationId
        ).all()
    
    matricula = None
    for curso in cursos:
        mat = OrganizationPersonRole.query.filter_by(
            PersonId=alumno_id,
            OrganizationId=curso.OrganizationId,
            RoleId=6,
            ExitDate=None
        ).first()
        if mat:
            matricula = mat
            break
    
    if not matricula:
        flash('El estudiante no está matriculado en ningún curso de esta asignatura.', 'danger')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    # Cargar preguntas del instrumento
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()

    # PREPARAR LISTA CON PREGUNTAS + OPCIONES
    preguntas_data = []
    for q in preguntas:
        opciones = EdugestQuestionOption.query.filter_by(QuestionId=q.QuestionId).order_by(EdugestQuestionOption.OrderIndex).all()
        preguntas_data.append({
            'pregunta': q,
            'opciones': opciones
        })

    if request.method == 'POST':
        for item in preguntas_data:
            q = item['pregunta']
            
            # --- ALTERNATIVA y V/F ---
            if q.QuestionType in ['Alternativa', 'VerdaderoFalso']:
                campo = f'pregunta_{q.QuestionId}'
                opcion_id_str = request.form.get(campo)
                if not opcion_id_str:
                    continue
                opcion_id = int(opcion_id_str)
                opcion = EdugestQuestionOption.query.get(opcion_id)
                puntaje = q.Points if (opcion and opcion.IsCorrect) else 0
                
                _guardar_respuesta(matricula, q, opcion_id, puntaje)
            
            # --- DESARROLLO ---
            elif q.QuestionType == 'Desarrollo':
                texto = request.form.get(f'pregunta_{q.QuestionId}', '')
                _guardar_respuesta_desarrollo(matricula, q, texto)
            
            # --- RELACIÓN DE COLUMNAS ---
            elif q.QuestionType == 'RelacionColumnas':
                puntaje = 0
                total = len(item['opciones'])
                for op in item['opciones']:
                    respuesta = request.form.get(f'relacion_{q.QuestionId}_{op.OrderIndex}')
                    if respuesta and int(respuesta) == op.OptionId:
                        puntaje += q.Points / total if total > 0 else 0
                
                _guardar_respuesta(matricula, q, None, round(puntaje, 2))
            
            # --- COMPLETAR ---
            elif q.QuestionType == 'Completar':
                respuestas_correctas = [op.OptionText.strip().lower() for op in sorted(item['opciones'], key=lambda x: x.OrderIndex or 0)]
                aciertos = 0
                for idx, correcta in enumerate(respuestas_correctas, 1):
                    resp = request.form.get(f'completar_{q.QuestionId}_{idx}', '').strip().lower()
                    if resp == correcta:
                        aciertos += 1
                
                puntaje = (aciertos / len(respuestas_correctas)) * q.Points if respuestas_correctas else 0
                _guardar_respuesta(matricula, q, None, round(puntaje, 2))

        db.session.commit()
        flash('Evaluación enviada y calificada automáticamente.', 'success')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    return render_template(
        'evaluaciones/rendir.html',
        instrumento=instrumento,
        alumno=alumno,
        preguntas_data=preguntas_data
    )


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
                RoleId=6,
                ExitDate=None
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


# ============================================================================
# VISTA IMPRIMIBLE / DESCARGABLE (SIN RESPUESTAS CORRECTAS)
# ============================================================================
@evaluaciones_bp.route('/instrumento/<int:inst_id>/imprimir')
def imprimir_evaluacion(inst_id):
    """
    Renderiza una versión limpia de la evaluación lista para imprimir o 
    exportar a PDF mediante Ctrl+P del navegador.
    """
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    asignatura = Organization.query.get_or_404(instrumento.OrganizationId)

    # Obtener grado para la cabecera
    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=asignatura.OrganizationId
    ).first()
    grado = None
    if relacion_grado:
        grado = Organization.query.get(relacion_grado.ParentOrganizationId)

    # Cargar preguntas y opciones (sin filtrar por correcta)
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    preguntas_data = []
    for q in preguntas:
        opciones = EdugestQuestionOption.query.filter_by(
            QuestionId=q.QuestionId
        ).order_by(EdugestQuestionOption.OrderIndex).all()
        preguntas_data.append({
            'pregunta': q,
            'opciones': opciones
        })

    return render_template('evaluaciones/imprimir.html',
                           instrumento=instrumento,
                           asignatura=asignatura,
                           grado=grado,
                           preguntas_data=preguntas_data)