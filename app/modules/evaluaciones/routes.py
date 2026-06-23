import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.database import db
from datetime import datetime
from app.models import (
    EdugestAssessmentInstrument,
    EdugestAssessmentQuestion,
    EdugestCurriculumPlan,
    EdugestQuestionOption,
    EdugestStudentResponse,
    EdugestManualGrade,
    Organization,
    OrganizationPersonRole,
    OrganizationRelationship,
    Person,
    PersonIdentifier
)
from app.modules.auth.routes import permiso_requerido, verificar_escritura

evaluaciones_bp = Blueprint('evaluaciones', __name__, url_prefix='/evaluaciones')


# ============================================================================
# HELPER: Determinar si el usuario actual tiene nivel 2 en Evaluaciones
# ============================================================================
def _es_nivel_2_evaluaciones():
    """Retorna True si el usuario actual tiene permiso nivel 2 en Evaluaciones o es admin."""
    if current_user.RoleId == 1:
        return True
    from app.models.edugest import EdugestModule, EdugestRolePermission
    modulo = EdugestModule.query.filter_by(ModuleName='Evaluaciones').first()
    if modulo:
        perm = EdugestRolePermission.query.filter_by(
            RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
        ).first()
        if perm and perm.PermissionLevel >= 2:
            return True
    return False


# ============================================================================
# PASO 1: LISTAR GRADOS
# ============================================================================
@evaluaciones_bp.route('/grados')
@login_required
@permiso_requerido('Evaluaciones', 1)
def listar_grados():
    from app.models.edugest import EdugestOrganizationConfig

    grados_base = Organization.query.filter_by(RefOrganizationTypeId=46).all()
    grados_data = []

    for g in grados_base:
        config = EdugestOrganizationConfig.query.filter_by(OrganizationId=g.OrganizationId).first()
        activo = config.IsActive if config else True

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
@login_required
def asignaturas_por_grado(grado_id):
    grado = Organization.query.get_or_404(grado_id)

    asignaturas = Organization.query.join(
        OrganizationRelationship,
        Organization.OrganizationId == OrganizationRelationship.OrganizationId
    ).filter(
        Organization.RefOrganizationTypeId == 22,
        OrganizationRelationship.ParentOrganizationId == grado_id
    ).all()

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
@login_required
def unidades_asignatura(org_id):
    asignatura = Organization.query.get_or_404(org_id)

    relacion_grado = OrganizationRelationship.query.filter_by(OrganizationId=org_id).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    planes = EdugestCurriculumPlan.query.filter_by(OrganizationId=org_id).order_by(
        EdugestCurriculumPlan.CreatedAt
    ).all()

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
            unidades_agrupadas[plan.UnitTitle] = {'clases': [], 'plan_id': plan.PlanId}

        if plan.Contenido or plan.Objetivo or plan.DetallesActividad:
            # Nivel 2 ve todas las evaluaciones, nivel 1 solo las visibles
            if nivel_permiso >= 2:
                evals = EdugestAssessmentInstrument.query.filter_by(PlanId=plan.PlanId).all()
            else:
                evals = EdugestAssessmentInstrument.query.filter_by(
                    PlanId=plan.PlanId, IsVisible=True
                ).all()

            unidades_agrupadas[plan.UnitTitle]['clases'].append({
                'plan': plan,
                'evaluaciones': evals
            })

    return render_template('evaluaciones/unidades.html',
                           asignatura=asignatura,
                           grado_id=grado_id,
                           unidades_agrupadas=unidades_agrupadas,
                           nivel_permiso=nivel_permiso)


# ============================================================================
# PASO 4: CREAR EVALUACION VINCULADA A UNA CLASE
# ============================================================================
@evaluaciones_bp.route('/clase/<int:plan_id>/nueva-evaluacion', methods=['GET'])
@login_required
@permiso_requerido('Evaluaciones', 1)
def crear_evaluacion_clase(plan_id):
    plan = EdugestCurriculumPlan.query.get_or_404(plan_id)
    asignatura = Organization.query.get_or_404(plan.OrganizationId)

    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=asignatura.OrganizationId
    ).first()
    grado_id = relacion_grado.ParentOrganizationId if relacion_grado else None

    unidades = EdugestCurriculumPlan.query.filter_by(
        OrganizationId=asignatura.OrganizationId
    ).order_by(EdugestCurriculumPlan.CreatedAt).all()

    clases = EdugestCurriculumPlan.query.filter_by(
        OrganizationId=asignatura.OrganizationId,
        UnitTitle=plan.UnitTitle
    ).filter(
        EdugestCurriculumPlan.Contenido.isnot(None) |
        EdugestCurriculumPlan.Objetivo.isnot(None)
    ).all()

    return render_template('evaluaciones/crear_evaluacion.html',
                           plan=plan,
                           asignatura=asignatura,
                           grado_id=grado_id,
                           unidades=unidades,
                           clases=clases)


@evaluaciones_bp.route('/clase/<int:plan_id>/nueva-evaluacion', methods=['POST'])
@login_required
@permiso_requerido('Evaluaciones', 2)
def crear_evaluacion_clase_post(plan_id):
    plan = EdugestCurriculumPlan.query.get_or_404(plan_id)
    asignatura = Organization.query.get_or_404(plan.OrganizationId)

    titulo = request.form.get('title')
    plan_id_selected = request.form.get('plan_id')
    is_digital = 'is_digital' in request.form

    evaluation_type = request.form.get('evaluation_type', 'Calificativa')

    tipo_map = {
        'Sumativa': 1,
        'Calificativa': 2,
        'Formativa': 2,
        'Diagnostica': 2,
        'Otra': 2
    }
    assessment_type_id = tipo_map.get(evaluation_type, 2)

    nuevo_ins = EdugestAssessmentInstrument(
        Title=titulo,
        OrganizationId=asignatura.OrganizationId,
        PlanId=plan_id_selected if plan_id_selected else plan_id,
        IsDigital=is_digital,
        IsVisible=False,
        AssessmentTypeId=assessment_type_id,
        Seleccionada=(assessment_type_id == 1)
    )
    db.session.add(nuevo_ins)
    db.session.commit()

    flash("Evaluacion creada y vinculada a la clase.", "success")
    return redirect(url_for('evaluaciones.unidades_asignatura', org_id=asignatura.OrganizationId))


# ============================================================================
# RUTAS EXISTENTES
# ============================================================================

@evaluaciones_bp.route('/')
@login_required
def index():
    return redirect(url_for('evaluaciones.listar_grados'))


@evaluaciones_bp.route('/asignatura/<int:org_id>/nuevo', methods=['GET', 'POST'])
@login_required
@permiso_requerido('Evaluaciones', 1)
def crear_instrumento(org_id):
    return redirect(url_for('evaluaciones.asignaturas_por_grado', grado_id=1))


UPLOAD_FOLDER = 'app/static/uploads/preguntas'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@evaluaciones_bp.route('/disenar_preguntas/<int:inst_id>', methods=['GET'])
@login_required
@permiso_requerido('Evaluaciones', 1)
def disenar_preguntas(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)

    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    for p in preguntas:
        p.opciones_list = EdugestQuestionOption.query.filter_by(
            QuestionId=p.QuestionId
        ).order_by(EdugestQuestionOption.OrderIndex).all()

    return render_template('evaluaciones/disenar_preguntas.html',
                           instrumento=instrumento,
                           preguntas=preguntas)


@evaluaciones_bp.route('/disenar_preguntas/<int:inst_id>/crear', methods=['POST'])
@login_required
@permiso_requerido('Evaluaciones', 2)
def disenar_preguntas_post(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)

    tipo = request.form.get('question_type', 'Alternativa')
    puntos = int(request.form.get('points', 1))

    imagen_url = None
    if 'question_image' in request.files:
        file = request.files['question_image']
        if file and file.filename and allowed_file(file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            filename = secure_filename(f"{inst_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            imagen_url = f"/static/uploads/preguntas/{filename}"

    nueva_pregunta = EdugestAssessmentQuestion(
        InstrumentId=inst_id,
        QuestionText=request.form.get('question_text'),
        QuestionType=tipo,
        Points=puntos,
        ImageUrl=imagen_url
    )
    db.session.add(nueva_pregunta)
    db.session.flush()

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


# ============================================================================
# FUNCIONES HELPER
# ============================================================================
def _guardar_respuesta(matricula, pregunta, opcion_id, puntaje):
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
@login_required
def rendir(inst_id, alumno_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    alumno = Person.query.get_or_404(alumno_id)

    # ── BLOQUEO: verificar visibilidad de la evaluacion ──
    if not instrumento.IsVisible:
        if current_user.RoleId != 1:
            from app.models.edugest import EdugestModule, EdugestRolePermission
            modulo = EdugestModule.query.filter_by(ModuleName='Evaluaciones').first()
            permiso = EdugestRolePermission.query.filter_by(
                RoleId=current_user.RoleId,
                ModuleId=modulo.ModuleId
            ).first() if modulo else None

            if not permiso or permiso.PermissionLevel < 2:
                flash('Esta evaluacion no esta disponible aun.', 'warning')
                return redirect(url_for('portada.bienvenida'))

    # ── BLOQUEO: verificar que sea digital ──
    if not instrumento.IsDigital:
        if not _es_nivel_2_evaluaciones():
            flash('Esta evaluacion es presencial y no se puede rendir en linea.', 'warning')
            return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    # ── BLOQUEO: solo el propio alumno puede rendir su examen ──
    if not _es_nivel_2_evaluaciones() and current_user.PersonId != alumno_id:
        flash('No tienes permiso para rendir esta evaluacion.', 'danger')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    # FIX: Buscar matricula en el CURSO (Tipo 21), no en la asignatura
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
        flash('El estudiante no esta matriculado en ningun curso de esta asignatura.', 'danger')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    # Cargar preguntas del instrumento
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()

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

            if q.QuestionType in ['Alternativa', 'VerdaderoFalso']:
                campo = f'pregunta_{q.QuestionId}'
                opcion_id_str = request.form.get(campo)
                if not opcion_id_str:
                    continue
                opcion_id = int(opcion_id_str)
                opcion = EdugestQuestionOption.query.get(opcion_id)
                puntaje = q.Points if (opcion and opcion.IsCorrect) else 0
                _guardar_respuesta(matricula, q, opcion_id, puntaje)

            elif q.QuestionType == 'Desarrollo':
                texto = request.form.get(f'pregunta_{q.QuestionId}', '')
                _guardar_respuesta_desarrollo(matricula, q, texto)

            elif q.QuestionType == 'RelacionColumnas':
                puntaje = 0
                total = len(item['opciones'])
                for op in item['opciones']:
                    respuesta = request.form.get(f'relacion_{q.QuestionId}_{op.OrderIndex}')
                    if respuesta and int(respuesta) == op.OptionId:
                        puntaje += q.Points / total if total > 0 else 0
                _guardar_respuesta(matricula, q, None, round(puntaje, 2))

            elif q.QuestionType == 'Completar':
                respuestas_correctas = [op.OptionText.strip().lower() for op in sorted(item['opciones'], key=lambda x: x.OrderIndex or 0)]
                aciertos = 0
                for idx, correcta in enumerate(respuestas_correctas, 1):
                    resp = request.form.get(f'completar_{q.QuestionId}_{idx}', '').strip().lower()
                    if resp == correcta:
                        aciertos += 1
                puntaje = (aciertos / len(respuestas_correctas)) * q.Points if respuestas_correctas else 0
                _guardar_respuesta(matricula, q, None, round(puntaje, 2))

        db.session.flush()

        puntaje_maximo = sum(p.Points for p in preguntas) or 1

        respuestas_guardadas = (
            EdugestStudentResponse.query
            .filter_by(OrganizationPersonRoleId=matricula.OrganizationPersonRoleId)
            .join(EdugestAssessmentQuestion)
            .filter(EdugestAssessmentQuestion.InstrumentId == inst_id)
            .all()
        )
        puntaje_obtenido = sum(r.ScoreEarned or 0 for r in respuestas_guardadas)
        nota_calculada = round(1 + (puntaje_obtenido / puntaje_maximo) * 6, 1)

        registro = EdugestManualGrade.query.filter_by(
            InstrumentId=inst_id,
            OrganizationPersonRoleId=matricula.OrganizationPersonRoleId
        ).first()

        if registro:
            if not registro.IsManual:
                registro.Score = nota_calculada
        else:
            nuevo = EdugestManualGrade(
                InstrumentId=inst_id,
                OrganizationPersonRoleId=matricula.OrganizationPersonRoleId,
                Score=nota_calculada,
                IsManual=False
            )
            db.session.add(nuevo)

        db.session.commit()
        flash('Evaluacion enviada y calificada automaticamente.', 'success')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    return render_template(
        'evaluaciones/rendir.html',
        instrumento=instrumento,
        alumno=alumno,
        preguntas_data=preguntas_data
    )


@evaluaciones_bp.route('/instrumento/<int:inst_id>/resultados')
@login_required
def resultados(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    puntaje_maximo = sum(p.Points for p in preguntas) or 1

    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=instrumento.OrganizationId
    ).first()

    # ── Determinar si el usuario actual tiene nivel 2 ──
    is_nivel_2 = _es_nivel_2_evaluaciones()

    matriculas = []
    curso_info = None

    if relacion_grado:
        if is_nivel_2:
            # ── NIVEL 2: mostrar todos los cursos del grado ──
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
        else:
            # ── NIVEL 1 (alumno): solo su propio curso ──
            mi_matricula = OrganizationPersonRole.query.filter_by(
                PersonId=current_user.PersonId,
                RoleId=6,
                ExitDate=None
            ).first()

            if mi_matricula:
                mi_curso = Organization.query.get(mi_matricula.OrganizationId)
                if mi_curso and mi_curso.RefOrganizationTypeId == 21:
                    curso_info = mi_curso.Name

                    # Buscar el grado padre para mostrar contexto
                    rel_curso = OrganizationRelationship.query.filter_by(
                        OrganizationId=mi_curso.OrganizationId
                    ).first()
                    if rel_curso:
                        grado = Organization.query.get(rel_curso.ParentOrganizationId)
                        if grado:
                            curso_info = f"{grado.Name} {mi_curso.Name}"

                    mats = OrganizationPersonRole.query.filter_by(
                        OrganizationId=mi_curso.OrganizationId,
                        RoleId=6,
                        ExitDate=None
                    ).all()
                    matriculas.extend(mats)

    calificaciones = EdugestManualGrade.query.filter_by(InstrumentId=inst_id).all()
    calificaciones_dict = {c.OrganizationPersonRoleId: c for c in calificaciones}

    tabla_resultados = []
    vistos = set()

    for matricula in matriculas:
        if matricula.PersonId in vistos:
            continue
        vistos.add(matricula.PersonId)

        alumno = matricula.person
        opr_id = matricula.OrganizationPersonRoleId

        identificador = PersonIdentifier.query.filter_by(
            PersonId=alumno.PersonId,
            RefPersonIdentificationSystemId=51
        ).first()
        rut = identificador.Identifier if identificador else 'Sin RUT'

        respuestas = (
            EdugestStudentResponse.query
            .filter_by(OrganizationPersonRoleId=opr_id)
            .join(EdugestAssessmentQuestion)
            .filter(EdugestAssessmentQuestion.InstrumentId == inst_id)
            .all()
        )
        puntaje_obtenido = sum(r.ScoreEarned or 0 for r in respuestas)

        if puntaje_maximo > 0:
            nota_auto = round(1 + (puntaje_obtenido / puntaje_maximo) * 6, 1)
        else:
            nota_auto = 1.0

        registro = calificaciones_dict.get(opr_id)

        if registro and registro.IsManual:
            nota = registro.Score
            es_manual = True
        elif registro and not registro.IsManual:
            nota = registro.Score
            es_manual = False
        elif not respuestas:
            nota = nota_auto
            es_manual = False
        else:
            nota = nota_auto
            es_manual = False

        if not respuestas and not registro:
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
            'nota_auto': nota_auto,
            'estado': estado,
            'es_manual': es_manual,
            'opr_id': opr_id
        })

    tabla_resultados.sort(key=lambda x: x['alumno'].LastName)

    return render_template('evaluaciones/resultados.html',
                           instrumento=instrumento,
                           tabla_resultados=tabla_resultados,
                           is_nivel_2=is_nivel_2,
                           curso_info=curso_info)


@evaluaciones_bp.route('/instrumento/<int:inst_id>/nota-manual', methods=['POST'])
@login_required
@permiso_requerido('Evaluaciones', 2)
def guardar_nota_manual(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    puntaje_maximo = sum(p.Points for p in preguntas) or 1

    for key, value in request.form.items():
        if key.startswith('eliminar_nota_') and value == '1':
            opr_id = int(key.replace('eliminar_nota_', ''))
            registro = EdugestManualGrade.query.filter_by(
                InstrumentId=inst_id,
                OrganizationPersonRoleId=opr_id
            ).first()

            if registro:
                respuestas = (
                    EdugestStudentResponse.query
                    .filter_by(OrganizationPersonRoleId=opr_id)
                    .join(EdugestAssessmentQuestion)
                    .filter(EdugestAssessmentQuestion.InstrumentId == inst_id)
                    .all()
                )
                puntaje_obtenido = sum(r.ScoreEarned or 0 for r in respuestas)
                nota_auto = round(1 + (puntaje_obtenido / puntaje_maximo) * 6, 1)

                registro.Score = nota_auto
                registro.IsManual = False

        if key.startswith('nota_manual_'):
            opr_id = int(key.replace('nota_manual_', ''))

            eliminar_key = f'eliminar_nota_{opr_id}'
            if request.form.get(eliminar_key) == '1':
                continue

            try:
                nota = float(value)
                if 1.0 <= nota <= 7.0:
                    registro = EdugestManualGrade.query.filter_by(
                        InstrumentId=inst_id,
                        OrganizationPersonRoleId=opr_id
                    ).first()

                    if registro:
                        registro.Score = nota
                        registro.IsManual = True
                    else:
                        nueva = EdugestManualGrade(
                            InstrumentId=inst_id,
                            OrganizationPersonRoleId=opr_id,
                            Score=nota,
                            IsManual=True
                        )
                        db.session.add(nueva)
            except (ValueError, TypeError):
                continue

    db.session.commit()
    flash('Notas guardadas correctamente.', 'success')
    return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))


@evaluaciones_bp.route('/instrumento/<int:inst_id>/eliminar-nota-manual/<int:opr_id>', methods=['POST'])
@login_required
@permiso_requerido('Evaluaciones', 2)
def eliminar_nota_manual(inst_id, opr_id):
    manual = EdugestManualGrade.query.filter_by(
        InstrumentId=inst_id,
        OrganizationPersonRoleId=opr_id
    ).first()
    if manual:
        db.session.delete(manual)
        db.session.commit()
        flash('Nota manual eliminada. Se usara la calificacion automatica.', 'info')
    return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))


@evaluaciones_bp.route('/instrumento/<int:inst_id>/visibilidad', methods=['POST'])
@login_required
@permiso_requerido('Evaluaciones', 2)
def cambiar_visibilidad(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    instrumento.IsVisible = not instrumento.IsVisible
    db.session.commit()
    estado = "publicado" if instrumento.IsVisible else "ocultado"
    flash(f"El instrumento ha sido {estado} correctamente.", "success")
    return redirect(url_for('evaluaciones.unidades_asignatura', org_id=instrumento.OrganizationId))


# ============================================================================
# VISTA IMPRIMIBLE / DESCARGABLE
# ============================================================================
@evaluaciones_bp.route('/instrumento/<int:inst_id>/imprimir')
@login_required
@permiso_requerido('Evaluaciones', 1)
def imprimir_evaluacion(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    asignatura = Organization.query.get_or_404(instrumento.OrganizationId)

    relacion_grado = OrganizationRelationship.query.filter_by(
        OrganizationId=asignatura.OrganizationId
    ).first()
    grado = None
    if relacion_grado:
        grado = Organization.query.get(relacion_grado.ParentOrganizationId)

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