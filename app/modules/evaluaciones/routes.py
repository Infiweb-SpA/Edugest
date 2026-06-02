from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import db
from app.models import (
    # Edugest
    EdugestAssessmentInstrument,
    EdugestAssessmentQuestion,
    EdugestCurriculumPlan,
    EdugestQuestionOption,
    EdugestStudentResponse,
    # Mineduc
    Organization,
    OrganizationPersonRole,
    Person,
    PersonIdentifier
)
from sqlalchemy.orm import joinedload

evaluaciones_bp = Blueprint('evaluaciones', __name__, url_prefix='/evaluaciones')

@evaluaciones_bp.route('/')
def index():
    """Panel general: lista las asignaturas para gestionar o ver evaluaciones"""
    asignaturas = Organization.query.filter_by(RefOrganizationTypeId=22).all()
    instrumentos = EdugestAssessmentInstrument.query.all()
    return render_template('evaluaciones/index.html', asignaturas=asignaturas, instrumentos=instrumentos)


@evaluaciones_bp.route('/asignatura/<int:org_id>/nuevo', methods=['GET', 'POST'])
def crear_instrumento(org_id):
    """Crea una nueva evaluación (cabecera) vinculada a una unidad de planificación"""
    asignatura = Organization.query.get_or_404(org_id)
    unidades = EdugestCurriculumPlan.query.filter_by(OrganizationId=org_id).all()
    
    if request.method == 'POST':
        titulo = request.form.get('title')
        plan_id = request.form.get('plan_id')
        is_digital = 'is_digital' in request.form
        
        nuevo_ins = EdugestAssessmentInstrument(
            Title=titulo,
            OrganizationId=org_id,
            PlanId=plan_id if plan_id else None,
            IsDigital=is_digital,
            IsVisible=False
        )
        db.session.add(nuevo_ins)
        db.session.commit()
        flash("Instrumento creado exitosamente.", "success")
        return redirect(url_for('evaluaciones.index'))
        
    return render_template('evaluaciones/crear_instrumento.html', asignatura=asignatura, unidades=unidades)


@evaluaciones_bp.route('/disenar_preguntas/<int:inst_id>', methods=['GET', 'POST'])
def disenar_preguntas(inst_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)

    if request.method == 'POST':
        # 1. Crear la pregunta
        nueva_pregunta = EdugestAssessmentQuestion(
            InstrumentId=inst_id,
            QuestionText=request.form.get('question_text'),
            QuestionType=request.form.get('question_type', 'Alternativa'),
            Points=int(request.form.get('points', 1))
        )
        db.session.add(nueva_pregunta)
        db.session.flush()  # Obtiene el QuestionId sin hacer commit definitivo

        # 2. Determinar cuál radio button fue marcado como correcto
        correcta_key = request.form.get('correcta')  # Ej: "opcion_2"

        # 3. Crear las 4 alternativas
        for i in range(1, 5):
            texto_opcion = request.form.get(f'opcion_{i}')
            
            # Saltar si el campo viene vacío (opcional, pero recomendado)
            if not texto_opcion:
                continue

            es_correcta = (correcta_key == f'opcion_{i}')

            opcion = EdugestQuestionOption(
                QuestionId=nueva_pregunta.QuestionId,
                OptionText=texto_opcion,
                IsCorrect=es_correcta
            )
            db.session.add(opcion)

        # 4. ✅ COMMIT DEFINITIVO (Esto es lo que faltaba)
        db.session.commit()

        flash('Pregunta y alternativas guardadas correctamente.', 'success')
        return redirect(url_for('evaluaciones.disenar_preguntas', inst_id=inst_id))

    # GET: cargar preguntas existentes para mostrarlas en el banco
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    
    # Pre-cargar opciones manualmente para evitar problemas de lazy loading
    for p in preguntas:
        p.opciones_list = EdugestQuestionOption.query.filter_by(QuestionId=p.QuestionId).all()

    return render_template(
        'evaluaciones/disenar_preguntas.html',
        instrumento=instrumento,
        preguntas=preguntas
    )

@evaluaciones_bp.route('/rendir/<int:inst_id>/<int:alumno_id>', methods=['GET', 'POST'])
def rendir(inst_id, alumno_id):
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    alumno = Person.query.get_or_404(alumno_id)

    # Validar matrícula
    matricula = OrganizationPersonRole.query.filter_by(
        PersonId=alumno_id,
        OrganizationId=instrumento.OrganizationId,
        RoleId=6
    ).first()

    if not matricula:
        flash('El estudiante no está matriculado en esta asignatura.', 'danger')
        return redirect(url_for('evaluaciones.resultados', inst_id=inst_id))

    # Cargar preguntas del instrumento
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()

    # ✅ PREPARAR LISTA CON PREGUNTAS + OPCIONES MANUALMENTE
    preguntas_data = []
    for q in preguntas:
        opciones = EdugestQuestionOption.query.filter_by(QuestionId=q.QuestionId).all()
        preguntas_data.append({
            'pregunta': q,
            'opciones': opciones
        })

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

    return render_template(
        'evaluaciones/rendir.html',
        instrumento=instrumento,
        alumno=alumno,
        preguntas_data=preguntas_data  # ✅ Enviamos la lista preparada
    )

@evaluaciones_bp.route('/instrumento/<int:inst_id>/resultados')
def resultados(inst_id):
    # 1. Traemos el instrumento y su asignatura
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    
    # 2. Traemos TODAS las preguntas para calcular puntaje máximo
    preguntas = EdugestAssessmentQuestion.query.filter_by(InstrumentId=inst_id).all()
    puntaje_maximo = sum(p.Points for p in preguntas) or 1  # evitar división por cero

    # 3. Buscamos estudiantes matriculados en esta asignatura con Rol = 6
    matriculas = OrganizationPersonRole.query.filter_by(
        OrganizationId=instrumento.OrganizationId,
        RoleId=6
    ).all()

    tabla_resultados = []

    for matricula in matriculas:
        alumno = matricula.person  # backref definido en mineduc.py

        # --- RUT del estudiante (RefPersonIdentificationSystemId = 51) ---
        identificador = PersonIdentifier.query.filter_by(
            PersonId=alumno.PersonId,
            RefPersonIdentificationSystemId=51
        ).first()
        rut = identificador.Identifier if identificador else 'Sin RUT'

        # --- Respuestas de este estudiante para ESTE instrumento ---
        # Join para asegurar que solo contamos respuestas a preguntas de este test
        respuestas = (
            EdugestStudentResponse.query
            .filter_by(OrganizationPersonRoleId=matricula.OrganizationPersonRoleId)
            .join(EdugestAssessmentQuestion)
            .filter(EdugestAssessmentQuestion.InstrumentId == inst_id)
            .all()
        )

        puntaje_obtenido = sum(r.ScoreEarned or 0 for r in respuestas)

        # --- Cálculo nota Chile (escala 1.0 a 7.0) ---
        if puntaje_maximo > 0:
            nota = round(1 + (puntaje_obtenido / puntaje_maximo) * 6, 1)
        else:
            nota = 1.0

        # --- Estado ---
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

    # Ordenar alfabéticamente por apellido
    tabla_resultados.sort(key=lambda x: x['alumno'].LastName)

    return render_template(
        'evaluaciones/resultados.html',
        instrumento=instrumento,
        tabla_resultados=tabla_resultados
    )

@evaluaciones_bp.route('/instrumento/<int:inst_id>/visibilidad', methods=['POST'])
def cambiar_visibilidad(inst_id):
    """Publica u oculta un instrumento de evaluación"""
    instrumento = EdugestAssessmentInstrument.query.get_or_404(inst_id)
    instrumento.IsVisible = not instrumento.IsVisible
    db.session.commit()
    estado = "publicado" if instrumento.IsVisible else "ocultado"
    flash(f"El instrumento ha sido {estado} correctamente.", "success")
    return redirect(url_for('evaluaciones.index'))