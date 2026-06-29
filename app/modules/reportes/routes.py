import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, send_file, current_app, jsonify
from flask_login import current_user
from app.database import db
from sqlalchemy import func, extract
from app.models.mineduc import (
    Organization, OrganizationPersonRole, OrganizationCalendarSession,
    PersonIdentifier, Person, OrganizationRelationship, PersonRelationship
)

from app.models.edugest import (
    EdugestSessionAttendance, EdugestStudentObservation,
    EdugestManualGrade, EdugestAssessmentInstrument,
    EdugestRolePermission, EdugestModule
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os
from collections import defaultdict

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

# ============================================================
# CONSTANTES - Ajustar según el modelo real
# ============================================================
TIPO_SUMATIVA = 1       # AssessmentTypeId para evaluaciones Sumativas
TIPO_CALIFICATIVA = 2   # AssessmentTypeId para evaluaciones Calificativas

# ============================================================
# FUNCIÓN AUXILIAR - PERMISOS
# ============================================================
def get_permiso_modulo(module_name):
    """Obtiene el nivel de permiso del usuario actual para un módulo específico.
    Retorna: 0=Sin acceso, 1=Solo lectura, 2=Lectura y escritura"""
    modulo = EdugestModule.query.filter_by(ModuleName=module_name, IsEnabled=True).first()
    if not modulo:
        return 0
    permiso = EdugestRolePermission.query.filter_by(
        RoleId=current_user.RoleId,
        ModuleId=modulo.ModuleId
    ).first()
    return permiso.PermissionLevel if permiso else 0

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def calcular_rango_fechas(fecha_base, periodo):
    """Calcula el rango de fechas según el período seleccionado."""
    if periodo == 'mes':
        fecha_inicio = fecha_base.replace(day=1)
        if fecha_base.month == 12:
            fecha_fin = fecha_base.replace(year=fecha_base.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fecha_fin = fecha_base.replace(month=fecha_base.month + 1, day=1) - timedelta(days=1)
    elif periodo == 'semestre':
        if fecha_base.month <= 6:
            fecha_inicio = fecha_base.replace(month=1, day=1)
            fecha_fin = fecha_base.replace(month=6, day=30)
        else:
            fecha_inicio = fecha_base.replace(month=7, day=1)
            fecha_fin = fecha_base.replace(month=12, day=31)
    elif periodo == 'anio':
        fecha_inicio = fecha_base.replace(month=1, day=1)
        fecha_fin = fecha_base.replace(month=12, day=31)
    else:
        fecha_inicio = fecha_base.replace(day=1)
        fecha_fin = fecha_base
    return fecha_inicio, fecha_fin


# ============================================================
# RUTA: ÍNDICE DE REPORTES
# ============================================================
@reportes_bp.route('/')
def index():
    # ── Verificar nivel de permisos ──
    nivel = get_permiso_modulo('Reportes')

    if nivel == 0:
        # Sin acceso al modulo: redirigir a pagina de no autorizado
        return redirect(url_for('auth.unauthorized'))

    if nivel == 1:
        # Solo lectura: determinar si es Alumno o Apoderado/Tutor
        person_id = current_user.PersonId

        # ── Caso A: Es Alumno (RoleId=6) ──
        rol_estudiante = OrganizationPersonRole.query.filter_by(
            PersonId=person_id,
            RoleId=6,
            ExitDate=None
        ).first()

        if rol_estudiante:
            return redirect(url_for('reportes.reporte_curso', curso_id=rol_estudiante.OrganizationId))

        # ── Caso B: Es Apoderado/Tutor (RoleId=5) ──
        # Buscar hijos vinculados a este apoderado en PersonRelationship
        relaciones = PersonRelationship.query.filter_by(RelatedPersonId=person_id).all()
        hijos_info = []
        for rel in relaciones:
            # Verificar que el vinculado sea un alumno activo
            rol_hijo = OrganizationPersonRole.query.filter_by(
                PersonId=rel.PersonId,
                RoleId=6,
                ExitDate=None
            ).first()

            if rol_hijo:
                persona_hijo = Person.query.get(rel.PersonId)
                if not persona_hijo:
                    continue

                # Obtener RUT del hijo
                ident = PersonIdentifier.query.filter_by(
                    PersonId=persona_hijo.PersonId,
                    RefPersonIdentificationSystemId=51
                ).first()

                # Obtener nombre del curso
                curso = Organization.query.get(rol_hijo.OrganizationId)
                relacion_curso = OrganizationRelationship.query.filter_by(
                    OrganizationId=rol_hijo.OrganizationId
                ).first()
                grado = Organization.query.get(relacion_curso.ParentOrganizationId) if relacion_curso else None

                hijos_info.append({
                    'person_id': persona_hijo.PersonId,
                    'nombre': f"{persona_hijo.FirstName} {persona_hijo.LastName or ''} {persona_hijo.SecondLastName or ''}".strip(),
                    'rut': ident.Identifier if ident else 'Sin RUT',
                    'curso_id': rol_hijo.OrganizationId,
                    'curso_nombre': f"{grado.Name if grado else ''} {curso.Name if curso else ''}".strip(),
                    'letra': (curso.ShortName if curso else '') or ''
                })

        if len(hijos_info) == 0:
            flash('No se encontró un curso asignado.', 'error')
            return redirect(url_for('portada.bienvenida'))

        if len(hijos_info) == 1:
            # Un solo hijo: redirigir directo al reporte
            return redirect(url_for('reportes.reporte_curso', curso_id=hijos_info[0]['curso_id']))

        # Multiples hijos: mostrar seleccion
        return render_template('reportes/apoderado_hijos.html', hijos=hijos_info)

    # ── Nivel 2+: mostrar panel completo de seleccion de cursos ──
    grados = Organization.query.filter_by(RefOrganizationTypeId=46).order_by(Organization.Name).all()
    cursos_data = []
    for grado in grados:
        cursos = Organization.query.join(
            OrganizationRelationship, Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            OrganizationRelationship.ParentOrganizationId == grado.OrganizationId,
            Organization.RefOrganizationTypeId == 21
        ).order_by(Organization.ShortName).all()

        for curso in cursos:
            total_alumnos = OrganizationPersonRole.query.filter_by(
                OrganizationId=curso.OrganizationId, RoleId=6, ExitDate=None
            ).count()
            if total_alumnos > 0:
                asignaturas = Organization.query.join(
                    OrganizationRelationship,
                    Organization.OrganizationId == OrganizationRelationship.OrganizationId
                ).filter(
                    OrganizationRelationship.ParentOrganizationId == curso.OrganizationId,
                    Organization.RefOrganizationTypeId == 20
                ).order_by(Organization.Name).all()

                asignaturas_data = []
                for asig in asignaturas:
                    total_instrumentos = EdugestAssessmentInstrument.query.filter_by(
                        OrganizationId=asig.OrganizationId
                    ).count()
                    asignaturas_data.append({
                        'org_id': asig.OrganizationId,
                        'nombre': asig.Name,
                        'total_instrumentos': total_instrumentos
                    })

                cursos_data.append({
                    'grado_id': grado.OrganizationId,
                    'grado_nombre': grado.Name,
                    'curso_id': curso.OrganizationId,
                    'curso_nombre': curso.Name,
                    'letra': curso.ShortName or 'Sin letra',
                    'total_alumnos': total_alumnos,
                    'asignaturas': asignaturas_data
                })

    return render_template('reportes/index.html', cursos=cursos_data)


# ============================================================
# RUTA: REPORTE DE CURSO
# ============================================================
@reportes_bp.route('/curso/<int:curso_id>')
def reporte_curso(curso_id):
    curso = Organization.query.get_or_404(curso_id)
    relacion = OrganizationRelationship.query.filter_by(OrganizationId=curso_id).first()
    grado = Organization.query.get(relacion.ParentOrganizationId) if relacion else None
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)

    alumnos_roles = OrganizationPersonRole.query.filter_by(
        OrganizationId=curso_id, RoleId=6, ExitDate=None
    ).all()
    rol_ids = [r.OrganizationPersonRoleId for r in alumnos_roles]

    # ── Asistencias ──
    asistencias = db.session.query(
        EdugestSessionAttendance.OrganizationPersonRoleId,
        EdugestSessionAttendance.AttendanceStatusId,
        func.count(EdugestSessionAttendance.SessionAttendanceId).label('total')
    ).filter(
        EdugestSessionAttendance.OrganizationPersonRoleId.in_(rol_ids),
        EdugestSessionAttendance.FechaRegistro >= fecha_inicio,
        EdugestSessionAttendance.FechaRegistro <= fecha_fin
    ).group_by(
        EdugestSessionAttendance.OrganizationPersonRoleId,
        EdugestSessionAttendance.AttendanceStatusId
    ).all()

    # ── Notas (CON AssessmentTypeId y Seleccionada) ──
    notas_raw = db.session.query(
        EdugestManualGrade.OrganizationPersonRoleId, EdugestManualGrade.InstrumentId,
        EdugestManualGrade.Score, EdugestManualGrade.IsManual, EdugestManualGrade.CreatedAt,
        EdugestAssessmentInstrument.Title.label('instrument_title'),
        EdugestAssessmentInstrument.AssessmentTypeId,
        EdugestAssessmentInstrument.Seleccionada,
        Organization.OrganizationId.label('asignatura_id'),
        Organization.Name.label('asignatura_nombre')
    ).join(
        EdugestAssessmentInstrument,
        EdugestManualGrade.InstrumentId == EdugestAssessmentInstrument.InstrumentId
    ).join(
        Organization,
        EdugestAssessmentInstrument.OrganizationId == Organization.OrganizationId
    ).filter(EdugestManualGrade.OrganizationPersonRoleId.in_(rol_ids)).all()

    # ── Anotaciones ──
    anotaciones_raw = db.session.query(
        EdugestStudentObservation.OrganizationPersonRoleId, EdugestStudentObservation.Tipo,
        EdugestStudentObservation.Detalle, EdugestStudentObservation.FechaRegistro,
        EdugestStudentObservation.AsignaturaId, Organization.Name.label('asignatura_nombre')
    ).outerjoin(
        Organization, EdugestStudentObservation.AsignaturaId == Organization.OrganizationId
    ).filter(
        EdugestStudentObservation.OrganizationPersonRoleId.in_(rol_ids),
        EdugestStudentObservation.FechaRegistro >= fecha_inicio,
        EdugestStudentObservation.FechaRegistro <= fecha_fin
    ).order_by(EdugestStudentObservation.FechaRegistro.desc()).all()

    # ==================================================================
    # PROCESAMIENTO POR ALUMNO
    # ==================================================================
    alumnos_reporte = []
    total_presentes = total_ausentes = total_atrasados = 0

    for rol in alumnos_roles:
        persona = Person.query.get(rol.PersonId)
        if not persona:
            continue
        ident = PersonIdentifier.query.filter_by(
            PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
        ).first()

        # ── Asistencia del alumno ──
        asist_alumno = [a for a in asistencias if a.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        presentes = sum(a.total for a in asist_alumno if a.AttendanceStatusId == 1)
        ausentes = sum(a.total for a in asist_alumno if a.AttendanceStatusId == 2)
        atrasados = sum(a.total for a in asist_alumno if a.AttendanceStatusId == 3)
        total_asist = presentes + ausentes + atrasados
        total_presentes += presentes
        total_ausentes += ausentes
        total_atrasados += atrasados

        # ── Notas del alumno (SEPARADAS POR TIPO) ──
        notas_alumno = [n for n in notas_raw if n.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        notas_por_asignatura = {}

        for n in notas_alumno:
            asig_id = n.asignatura_id
            asig_nombre = n.asignatura_nombre or f'Asignatura #{asig_id}'
            if asig_id not in notas_por_asignatura:
                notas_por_asignatura[asig_id] = {
                    'nombre': asig_nombre,
                    'calificativas': [],
                    'sumativas': [],
                    'sum_sel_notas': [],
                    'evaluaciones': 0
                }

            nota_info = {
                'instrumento': n.instrument_title or f'Evaluación #{n.InstrumentId}',
                'nota': round(n.Score, 1),
                'tipo': 'Manual' if n.IsManual else 'Automática',
                'fecha': n.CreatedAt.strftime('%d/%m/%Y') if n.CreatedAt else 'N/A',
                'assessment_type': n.AssessmentTypeId,
                'seleccionada': bool(n.Seleccionada) if n.Seleccionada is not None else False
            }

            if n.AssessmentTypeId == TIPO_CALIFICATIVA:
                notas_por_asignatura[asig_id]['calificativas'].append(nota_info)
            elif n.AssessmentTypeId == TIPO_SUMATIVA:
                notas_por_asignatura[asig_id]['sumativas'].append(nota_info)
                if nota_info['seleccionada']:
                    notas_por_asignatura[asig_id]['sum_sel_notas'].append(nota_info['nota'])
            else:
                # Sin tipo definido: se trata como calificativa
                notas_por_asignatura[asig_id]['calificativas'].append(nota_info)

            notas_por_asignatura[asig_id]['evaluaciones'] += 1

        # Calcular promedio por asignatura
        for asig_id in notas_por_asignatura:
            data = notas_por_asignatura[asig_id]

            # Notas de calificativas puras
            calif_scores = [n['nota'] for n in data['calificativas']]

            # Promedio de sumativas seleccionadas (se convierte en una nota calificativa más)
            sum_sel = data['sum_sel_notas']
            promedio_sum_sel = round(sum(sum_sel) / len(sum_sel), 1) if sum_sel else None

            # Se agrega el promedio de sum. seleccionadas como una calificativa más
            todos_para_promedio = list(calif_scores)
            if promedio_sum_sel is not None:
                todos_para_promedio.append(promedio_sum_sel)

            data['promedio_sum_sel'] = promedio_sum_sel
            data['promedio'] = round(
                sum(todos_para_promedio) / len(todos_para_promedio), 1
            ) if todos_para_promedio else None

        promedios_asig = [
            notas_por_asignatura[a]['promedio']
            for a in notas_por_asignatura
            if notas_por_asignatura[a]['promedio'] is not None
        ]
        promedio_general_final = round(
            sum(promedios_asig) / len(promedios_asig), 1
        ) if promedios_asig else None
        total_evaluaciones = sum(
            notas_por_asignatura[a]['evaluaciones'] for a in notas_por_asignatura
        )

        # ── Anotaciones del alumno ──
        anot_alumno = [a for a in anotaciones_raw if a.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        anotaciones_list = []
        conteo_anotaciones = {'Positiva': 0, 'Negativa': 0, 'Otra': 0}
        for a in anot_alumno:
            anotaciones_list.append({
                'tipo': a.Tipo, 'detalle': a.Detalle,
                'asignatura': a.asignatura_nombre or 'General',
                'fecha': a.FechaRegistro.strftime('%d/%m/%Y') if a.FechaRegistro else 'N/A'
            })
            conteo_anotaciones[a.Tipo] = conteo_anotaciones.get(a.Tipo, 0) + 1

        alumnos_reporte.append({
            'rol_id': rol.OrganizationPersonRoleId,
            'rut': ident.Identifier if ident else 'Sin RUT',
            'nombres': persona.FirstName,
            'apellido_paterno': persona.LastName or '',
            'apellido_materno': persona.SecondLastName or '',
            'presentes': presentes, 'ausentes': ausentes, 'atrasados': atrasados, 'total': total_asist,
            'porcentaje_asistencia': round((presentes / total_asist * 100), 1) if total_asist > 0 else 0,
            'notas_por_asignatura': notas_por_asignatura,
            'promedio_general_final': promedio_general_final,
            'total_evaluaciones': total_evaluaciones,
            'total_asignaturas': len(notas_por_asignatura),
            'anotaciones': anotaciones_list,
            'conteo_anotaciones': conteo_anotaciones,
            'total_anotaciones': len(anotaciones_list)
        })

    alumnos_reporte.sort(key=lambda x: x['apellido_paterno'])
    chart_data = {'presentes': total_presentes, 'ausentes': total_ausentes, 'atrasados': total_atrasados}
    todos_promedios_finales = [a['promedio_general_final'] for a in alumnos_reporte
                               if a['promedio_general_final'] is not None]
    resumen_notas = {
        'total_evaluaciones': sum(a['total_evaluaciones'] for a in alumnos_reporte),
        'promedio_curso': round(sum(todos_promedios_finales) / len(todos_promedios_finales), 1) if todos_promedios_finales else None,
        'mejor_nota': round(max(todos_promedios_finales), 1) if todos_promedios_finales else None,
        'peor_nota': round(min(todos_promedios_finales), 1) if todos_promedios_finales else None
    }
    resumen_anotaciones = {
        'positivas': sum(a['conteo_anotaciones']['Positiva'] for a in alumnos_reporte),
        'negativas': sum(a['conteo_anotaciones']['Negativa'] for a in alumnos_reporte),
        'otras': sum(a['conteo_anotaciones']['Otra'] for a in alumnos_reporte)
    }

    # ── Asignaturas del curso (vinculadas al GRADO, no al curso) ──
    grado_id = grado.OrganizationId if grado else None

    asignaturas_data = []
    if grado_id:
        asignaturas_org = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            OrganizationRelationship.ParentOrganizationId == grado_id,
            Organization.RefOrganizationTypeId == 22
        ).order_by(Organization.Name).all()

        for asig in asignaturas_org:
            total_instrumentos = EdugestAssessmentInstrument.query.filter_by(
                OrganizationId=asig.OrganizationId
            ).count()
            asignaturas_data.append({
                'org_id': asig.OrganizationId,
                'nombre': asig.Name,
                'total_instrumentos': total_instrumentos
            })

        # ── Determinar si el usuario puede volver al panel de reportes ──
    nivel_permiso = get_permiso_modulo('Reportes')

    return render_template('reportes/curso.html', curso=curso, grado=grado,
                           alumnos=alumnos_reporte, asignaturas=asignaturas_data,
                           chart_data=chart_data, resumen_notas=resumen_notas,
                           resumen_anotaciones=resumen_anotaciones, periodo=periodo,
                           fecha_inicio=fecha_inicio.strftime('%Y-%m-%d'),
                           fecha_fin=fecha_fin.strftime('%Y-%m-%d'), fecha_ref=fecha_ref,
                           puede_volver_panel=(nivel_permiso >= 2))


# ============================================================
# RUTA: REPORTE DE GRADO (CONSOLIDADO)
# ============================================================
@reportes_bp.route('/grado/<int:grado_id>')
def reporte_grado(grado_id):
    grado = Organization.query.get_or_404(grado_id)
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)

    # Obtener cursos del grado
    cursos_org = Organization.query.join(
        OrganizationRelationship, Organization.OrganizationId == OrganizationRelationship.OrganizationId
    ).filter(
        OrganizationRelationship.ParentOrganizationId == grado_id,
        Organization.RefOrganizationTypeId == 21
    ).order_by(Organization.ShortName).all()

    cursos_data = []
    total_presentes = total_ausentes = total_atrasados = 0
    todos_los_promedios = []
    total_anot_pos = total_anot_neg = 0

    for c in cursos_org:
        alumnos_roles = OrganizationPersonRole.query.filter_by(
            OrganizationId=c.OrganizationId, RoleId=6, ExitDate=None
        ).all()
        rol_ids = [r.OrganizationPersonRoleId for r in alumnos_roles]
        total_alumnos = len(alumnos_roles)

        # Asistencia
        presentes = ausentes = atrasados = 0
        if rol_ids:
            asist = db.session.query(
                EdugestSessionAttendance.AttendanceStatusId,
                func.count(EdugestSessionAttendance.SessionAttendanceId)
            ).filter(
                EdugestSessionAttendance.OrganizationPersonRoleId.in_(rol_ids),
                EdugestSessionAttendance.FechaRegistro >= fecha_inicio,
                EdugestSessionAttendance.FechaRegistro <= fecha_fin
            ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()
            for status_id, count in asist:
                if status_id == 1:
                    presentes += count
                elif status_id == 2:
                    ausentes += count
                elif status_id == 3:
                    atrasados += count

        total_presentes += presentes
        total_ausentes += ausentes
        total_atrasados += atrasados

        # Notas
        total_evaluaciones = 0
        promedio_notas = None
        if rol_ids:
            notas_raw = db.session.query(
                EdugestManualGrade.OrganizationPersonRoleId,
                func.avg(EdugestManualGrade.Score).label('promedio')
            ).filter(
                EdugestManualGrade.OrganizationPersonRoleId.in_(rol_ids)
            ).group_by(EdugestManualGrade.OrganizationPersonRoleId).all()

            if notas_raw:
                promedios_alumnos = [round(n.promedio, 1) for n in notas_raw if n.promedio is not None]
                if promedios_alumnos:
                    promedio_notas = round(sum(promedios_alumnos) / len(promedios_alumnos), 1)
                    todos_los_promedios.extend(promedios_alumnos)

            total_evaluaciones = db.session.query(func.count(EdugestManualGrade.ManualGradeId)).filter(
                EdugestManualGrade.OrganizationPersonRoleId.in_(rol_ids)
            ).scalar() or 0

        # Anotaciones
        anot_pos = anot_neg = anot_otras = 0
        if rol_ids:
            anots = db.session.query(
                EdugestStudentObservation.Tipo,
                func.count(EdugestStudentObservation.ObservationId)
            ).filter(
                EdugestStudentObservation.OrganizationPersonRoleId.in_(rol_ids),
                EdugestStudentObservation.FechaRegistro >= fecha_inicio,
                EdugestStudentObservation.FechaRegistro <= fecha_fin
            ).group_by(EdugestStudentObservation.Tipo).all()
            for tipo, count in anots:
                if tipo == 'Positiva':
                    anot_pos += count
                elif tipo == 'Negativa':
                    anot_neg += count
                else:
                    anot_otras += count

        total_anot_pos += anot_pos
        total_anot_neg += anot_neg

        total_reg = presentes + ausentes + atrasados
        porcentaje = round((presentes / total_reg * 100), 1) if total_reg > 0 else 0
        total_anot = anot_pos + anot_neg + anot_otras

        cursos_data.append({
            'curso_id': c.OrganizationId, 'letra': c.ShortName or 'N/A',
            'total_alumnos': total_alumnos,
            'presentes': presentes, 'ausentes': ausentes, 'atrasados': atrasados,
            'total_registros': total_reg, 'porcentaje_asistencia': porcentaje,
            'total_evaluaciones': total_evaluaciones, 'promedio_notas': promedio_notas,
            'anotaciones_positivas': anot_pos, 'anotaciones_negativas': anot_neg,
            'anotaciones_otras': anot_otras, 'total_anotaciones': total_anot
        })

    chart_data = {'presentes': total_presentes, 'ausentes': total_ausentes, 'atrasados': total_atrasados}
    resumen_grado = {
        'promedio_general': round(sum(todos_los_promedios) / len(todos_los_promedios), 1) if todos_los_promedios else None,
        'total_anotaciones_positivas': total_anot_pos,
        'total_anotaciones_negativas': total_anot_neg
    }

    return render_template('reportes/grado.html', grado=grado, cursos=cursos_data,
                           chart_data=chart_data, resumen_grado=resumen_grado,
                           periodo=periodo, fecha_inicio=fecha_inicio.strftime('%Y-%m-%d'),
                           fecha_fin=fecha_fin.strftime('%Y-%m-%d'), fecha_ref=fecha_ref)


# ============================================================
# RUTA: REPORTE DE NOTAS SUMATIVAS POR ASIGNATURA (MODIFICADA)
# ============================================================
@reportes_bp.route('/asignatura/<int:org_id>')
def reporte_notas_sumativas(org_id):
    """
    Muestra las calificaciones por asignatura con:
    - Columnas individuales para cada evaluación Sumativa (con checkbox de selección)
    - Columna de Promedio de Sumativas Seleccionadas (se convierte en nota calificativa)
    - Columnas individuales para cada evaluación Calificativa
    - Columna de Promedio Calificativas (incluye el derivado de sumativas seleccionadas)
    - Columna de Nota Final
    """
    asignatura = Organization.query.get_or_404(org_id)

    # Obtener todos los instrumentos de evaluación de esta asignatura
    instrumentos = EdugestAssessmentInstrument.query.filter_by(OrganizationId=org_id).all()

    # Separar en Sumativas y Calificativas según AssessmentTypeId
    todas_sumativas = []
    calificativas = []
    for inst in instrumentos:
        if inst.AssessmentTypeId == TIPO_SUMATIVA:
            todas_sumativas.append(inst)
        elif inst.AssessmentTypeId == TIPO_CALIFICATIVA:
            calificativas.append(inst)
        else:
            # Sin tipo definido: se trata como calificativa por defecto
            calificativas.append(inst)

    # Sumativas separadas por estado de selección (persistido en BD)
    sumativas_seleccionadas = [s for s in todas_sumativas if s.Seleccionada]
    sumativas_no_seleccionadas = [s for s in todas_sumativas if not s.Seleccionada]

    # Obtener todos los IDs de instrumentos de esta asignatura
    instrument_ids = [inst.InstrumentId for inst in instrumentos]

    if not instrument_ids:
        return render_template('reportes/notas_sumativas.html',
                               asignatura=asignatura, estudiantes=[],
                               todas_sumativas=todas_sumativas, calificativas=calificativas,
                               sumativas_seleccionadas=sumativas_seleccionadas,
                               sumativas_no_seleccionadas=sumativas_no_seleccionadas)

    # Obtener todas las notas de estudiantes para estos instrumentos
    notas_raw = db.session.query(
        EdugestManualGrade.OrganizationPersonRoleId,
        EdugestManualGrade.InstrumentId,
        EdugestManualGrade.Score,
        EdugestManualGrade.CreatedAt
    ).filter(
        EdugestManualGrade.InstrumentId.in_(instrument_ids)
    ).all()

    # Agrupar notas por estudiante y por instrumento
    notas_por_estudiante = defaultdict(lambda: defaultdict(list))
    for nota in notas_raw:
        notas_por_estudiante[nota.OrganizationPersonRoleId][nota.InstrumentId].append(
            round(nota.Score, 1)
        )

    # Construir datos de cada estudiante
    rol_ids = list(notas_por_estudiante.keys())
    estudiantes = []

    for rol_id in rol_ids:
        rol = OrganizationPersonRole.query.get(rol_id)
        if not rol:
            continue
        persona = Person.query.get(rol.PersonId)
        if not persona:
            continue

        ident = PersonIdentifier.query.filter_by(
            PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
        ).first()

        # ── Notas Sumativas del estudiante (todas, para visualización) ──
        notas_sumativas_est = {}
        for s in todas_sumativas:
            if s.InstrumentId in notas_por_estudiante[rol_id]:
                scores = notas_por_estudiante[rol_id][s.InstrumentId]
                notas_sumativas_est[s.InstrumentId] = round(sum(scores) / len(scores), 1)
            else:
                notas_sumativas_est[s.InstrumentId] = None

        # ── Notas Calificativas del estudiante ──
        notas_calificativas_est = {}
        for c in calificativas:
            if c.InstrumentId in notas_por_estudiante[rol_id]:
                scores = notas_por_estudiante[rol_id][c.InstrumentId]
                notas_calificativas_est[c.InstrumentId] = round(sum(scores) / len(scores), 1)
            else:
                notas_calificativas_est[c.InstrumentId] = None

        # ── Promedio de sumativas SELECCIONADAS (se convierte en calificativa) ──
        sum_sel_scores = [
            notas_sumativas_est[s.InstrumentId]
            for s in sumativas_seleccionadas
            if notas_sumativas_est.get(s.InstrumentId) is not None
        ]
        promedio_sum_sel = round(sum(sum_sel_scores) / len(sum_sel_scores), 1) if sum_sel_scores else None

        # ── Promedio de calificativas puras ──
        calif_validas = [v for v in notas_calificativas_est.values() if v is not None]
        promedio_calificativas = round(sum(calif_validas) / len(calif_validas), 1) if calif_validas else None

        # ── NOTA FINAL: promedio de (calificativas individuales + promedio sum. seleccionadas) ──
        todos_para_promedio = list(calif_validas)
        if promedio_sum_sel is not None:
            todos_para_promedio.append(promedio_sum_sel)

        nota_final = round(
            sum(todos_para_promedio) / len(todos_para_promedio), 1
        ) if todos_para_promedio else None

        # Obtener curso del estudiante para el enlace del PDF
        curso_rel = OrganizationRelationship.query.filter_by(OrganizationId=rol.OrganizationId).first()
        grado_id = curso_rel.ParentOrganizationId if curso_rel else rol.OrganizationId

        estudiantes.append({
            'opr_id': rol_id,
            'alumno': persona,
            'rut': ident.Identifier if ident else 'Sin RUT',
            'notas_sumativas': notas_sumativas_est,
            'notas_calificativas': notas_calificativas_est,
            'promedio_sum_sel': promedio_sum_sel,
            'promedio_calificativas': promedio_calificativas,
            'nota_final': nota_final,
            'cant_sum_sel': len(sum_sel_scores),
            'cant_calif': len(calif_validas),
            'grado_id': grado_id
        })

    estudiantes.sort(key=lambda x: (x['alumno'].LastName or '', x['alumno'].FirstName or ''))

        # ── Determinar si el usuario puede configurar sumativas ──
    nivel_permiso = get_permiso_modulo('Reportes')

    return render_template('reportes/notas_sumativas.html',
                           asignatura=asignatura,
                           estudiantes=estudiantes,
                           todas_sumativas=todas_sumativas,
                           calificativas=calificativas,
                           sumativas_seleccionadas=sumativas_seleccionadas,
                           sumativas_no_seleccionadas=sumativas_no_seleccionadas,
                           puede_configurar=(nivel_permiso >= 2))

# ============================================================
# RUTA: CONFIGURAR SUMATIVAS (EXISTENTE)
# ============================================================
@reportes_bp.route('/asignatura/<int:org_id>/configurar-sumativas', methods=['GET', 'POST'])
def configurar_sumativas(org_id):
    # ── Solo nivel 2 (lectura + escritura) puede configurar ──
    nivel = get_permiso_modulo('Reportes')
    if nivel < 2:
        flash('No tiene permisos para realizar esta acción.', 'error')
        return redirect(url_for('reportes.index'))

    asignatura = Organization.query.get_or_404(org_id)

    # Obtener solo instrumentos de tipo Sumativa
    instrumentos_sumativos = EdugestAssessmentInstrument.query.filter_by(
        OrganizationId=org_id, AssessmentTypeId=TIPO_SUMATIVA
    ).all()

    if request.method == 'POST':
        for inst in instrumentos_sumativos:
            key = f'seleccionada_{inst.InstrumentId}'
            inst.Seleccionada = (key in request.form)
        db.session.commit()
        flash('Configuración de evaluaciones Sumativas guardada exitosamente.', 'success')
        return redirect(url_for('reportes.reporte_notas_sumativas', org_id=org_id))

    # Construir datos para el template
    sumativas_data = []
    for inst in instrumentos_sumativos:
        sumativas_data.append({
            'instrumento': inst,
            'seleccionada': getattr(inst, 'Seleccionada', True)
        })

    return render_template('reportes/configurar_sumativas.html',
                           asignatura=asignatura,
                           sumativas_data=sumativas_data)


# ============================================================
# RUTA: API AJAX PARA GUARDAR SELECCIÓN DE SUMATIVA
# ============================================================
@reportes_bp.route('/api/guardar-sumativa/<int:instrument_id>', methods=['POST'])
def guardar_sumativa_ajax(instrument_id):
    """Guarda el estado de selección de una evaluación Sumativa vía AJAX."""
    # ── Solo nivel 2 puede modificar selección ──
    nivel = get_permiso_modulo('Reportes')
    if nivel < 2:
        return jsonify({'success': False, 'message': 'Sin permisos para esta acción'}), 403

    data = request.get_json()
    if not data or 'seleccionada' not in data:
        return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

    instrumento = EdugestAssessmentInstrument.query.get(instrument_id)
    if not instrumento:
        return jsonify({'success': False, 'message': 'Instrumento no encontrado'}), 404

    instrumento.Seleccionada = bool(data['seleccionada'])
    db.session.commit()

    return jsonify({
        'success': True,
        'instrument_id': instrument_id,
        'seleccionada': instrumento.Seleccionada
    })


# ============================================================
# RUTA: GRÁFICO DE ASISTENCIA DEL CURSO
# ============================================================
@reportes_bp.route('/curso/<int:curso_id>/grafico_asistencia')
def grafico_asistencia(curso_id):
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)

    rol_ids = [r.OrganizationPersonRoleId for r in
               OrganizationPersonRole.query.filter_by(OrganizationId=curso_id, RoleId=6, ExitDate=None).all()]

    presentes = ausentes = atrasados = 0
    if rol_ids:
        asist = db.session.query(
            EdugestSessionAttendance.AttendanceStatusId,
            func.count(EdugestSessionAttendance.SessionAttendanceId)
        ).filter(
            EdugestSessionAttendance.OrganizationPersonRoleId.in_(rol_ids),
            EdugestSessionAttendance.FechaRegistro >= fecha_inicio,
            EdugestSessionAttendance.FechaRegistro <= fecha_fin
        ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()
        for sid, cnt in asist:
            if sid == 1:
                presentes = cnt
            elif sid == 2:
                ausentes = cnt
            elif sid == 3:
                atrasados = cnt

    fig, ax = plt.subplots(figsize=(4, 4))
    labels = ['Presentes', 'Ausentes', 'Atrasados']
    sizes = [presentes, ausentes, atrasados]
    chart_colors = ['#10b981', '#f43f5e', '#f59e0b']
    if sum(sizes) > 0:
        ax.pie(sizes, labels=labels, colors=chart_colors, autopct='%1.1f%%', startangle=90)
    else:
        ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=14)
    ax.set_title('Distribución de Asistencia')
    plt.tight_layout()

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)

    return send_file(img_buffer, mimetype='image/png', download_name='grafico_asistencia.png')


# ============================================================
# RUTA: EXPORTAR ASISTENCIA A CSV
# ============================================================
@reportes_bp.route('/curso/<int:curso_id>/exportar_asistencia')
def exportar_asistencia(curso_id):
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)

    curso = Organization.query.get_or_404(curso_id)
    alumnos_roles = OrganizationPersonRole.query.filter_by(
        OrganizationId=curso_id, RoleId=6, ExitDate=None
    ).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Estudiante', 'RUT', 'Presentes', 'Ausentes', 'Atrasados', 'Total', '% Asistencia'])

    for rol in alumnos_roles:
        persona = Person.query.get(rol.PersonId)
        if not persona:
            continue
        ident = PersonIdentifier.query.filter_by(
            PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
        ).first()

        asist = db.session.query(
            EdugestSessionAttendance.AttendanceStatusId,
            func.count(EdugestSessionAttendance.SessionAttendanceId)
        ).filter(
            EdugestSessionAttendance.OrganizationPersonRoleId == rol.OrganizationPersonRoleId,
            EdugestSessionAttendance.FechaRegistro >= fecha_inicio,
            EdugestSessionAttendance.FechaRegistro <= fecha_fin
        ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()

        p = a = t = 0
        for sid, cnt in asist:
            if sid == 1:
                p = cnt
            elif sid == 2:
                a = cnt
            elif sid == 3:
                t = cnt
        total = p + a + t
        porcentaje = round((p / total * 100), 1) if total > 0 else 0

        nombre = f"{persona.LastName or ''} {persona.SecondLastName or ''}, {persona.FirstName}".strip()
        writer.writerow([nombre, ident.Identifier if ident else '', p, a, t, total, porcentaje])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=asistencia_{curso.ShortName}_{periodo}.csv'}
    )


# ============================================================
# RUTA: INFORME DE NOTAS EN PDF (FORMATO ISETT)
# ============================================================
@reportes_bp.route('/curso/<int:curso_id>/informe_notas/<int:rol_id>')
def informe_notas_pdf(curso_id, rol_id):
    """Genera informe de calificaciones en PDF con formato ISETT."""
    rol = OrganizationPersonRole.query.get_or_404(rol_id)
    persona = Person.query.get_or_404(rol.PersonId)
    curso = Organization.query.get_or_404(curso_id)
    relacion = OrganizationRelationship.query.filter_by(OrganizationId=curso_id).first()
    grado = Organization.query.get(relacion.ParentOrganizationId) if relacion else None
    colegio = Organization.query.filter_by(RefOrganizationTypeId=1).first()
    nombre_colegio = colegio.Name if colegio else 'NombreColegio'

    # ── Profesor(a) jefe del curso ──
    prof_jefe = db.session.query(Person).join(
        OrganizationPersonRole, Person.PersonId == OrganizationPersonRole.PersonId
    ).filter(
        OrganizationPersonRole.OrganizationId == curso_id,
        OrganizationPersonRole.RoleId == 3,
        OrganizationPersonRole.ExitDate == None
    ).first()
    nombre_prof_jefe = (
        f"{prof_jefe.FirstName} {prof_jefe.LastName or ''}".strip()
        if prof_jefe else 'No asignado'
    )

    # ── Director(a) del establecimiento (RoleId=1 en la org del colegio) ──
    director = None
    if colegio:
        director_rol = OrganizationPersonRole.query.filter_by(
            OrganizationId=colegio.OrganizationId,
            RoleId=1,
            ExitDate=None
        ).first()
        if director_rol:
            director = Person.query.get(director_rol.PersonId)
    nombre_director = (
        f"{director.FirstName} {director.LastName or ''} {director.SecondLastName or ''}".strip()
        if director else 'No asignado'
    )

    anio_actual = datetime.now().year
    mes_actual = datetime.now().month
    semestre = '1º Semestre' if mes_actual <= 6 else '2º Semestre'

    # ==================================================================
    # NOTAS DEL ALUMNO — AGRUPADAS POR ASIGNATURA Y TIPO
    # ==================================================================
    notas_raw = db.session.query(
        EdugestManualGrade.Score, EdugestManualGrade.CreatedAt,
        EdugestManualGrade.InstrumentId,
        Organization.Name.label('asignatura_nombre'),
        EdugestAssessmentInstrument.AssessmentTypeId,
        EdugestAssessmentInstrument.Seleccionada
    ).join(
        EdugestAssessmentInstrument,
        EdugestManualGrade.InstrumentId == EdugestAssessmentInstrument.InstrumentId
    ).join(
        Organization,
        EdugestAssessmentInstrument.OrganizationId == Organization.OrganizationId
    ).filter(
        EdugestManualGrade.OrganizationPersonRoleId == rol_id
    ).all()

    # Paso 1: Promediar múltiples intentos por instrumento
    scores_por_instrumento = defaultdict(list)
    meta_instrumento = {}
    for n in notas_raw:
        scores_por_instrumento[n.InstrumentId].append(round(n.Score, 1))
        meta_instrumento[n.InstrumentId] = {
            'asignatura': n.asignatura_nombre,
            'assessment_type': n.AssessmentTypeId,
            'seleccionada': bool(n.Seleccionada) if n.Seleccionada is not None else False
        }

    # Paso 2: Agrupar por asignatura separando tipos
    notas_por_asignatura = defaultdict(
        lambda: {'calificativas': [], 'sum_sel_scores': []}
    )
    for inst_id, scores in scores_por_instrumento.items():
        meta = meta_instrumento[inst_id]
        promedio_inst = round(sum(scores) / len(scores), 1)
        asig = meta['asignatura']
        if meta['assessment_type'] == TIPO_SUMATIVA:
            if meta['seleccionada']:
                notas_por_asignatura[asig]['sum_sel_scores'].append(promedio_inst)
        else:
            notas_por_asignatura[asig]['calificativas'].append(promedio_inst)

    # Paso 3: Construir filas y determinar máximo de columnas dinámicas
    filas_asignaturas = []
    max_notas = 0
    suma_promedios = 0
    count_promedios = 0

    for asignatura in sorted(notas_por_asignatura.keys()):
        data = notas_por_asignatura[asignatura]
        calif = data['calificativas']
        sum_sel = data['sum_sel_scores']
        prom_sum_sel = round(sum(sum_sel) / len(sum_sel), 1) if sum_sel else None

        notas_display = list(calif)
        if prom_sum_sel is not None:
            notas_display.append(prom_sum_sel)

        if len(notas_display) > max_notas:
            max_notas = len(notas_display)

        promedio = (
            round(sum(notas_display) / len(notas_display), 1)
            if notas_display else ''
        )

        filas_asignaturas.append({
            'nombre': asignatura,
            'notas': [round(n, 1) for n in notas_display],
            'promedio': promedio
        })

        if promedio != '':
            suma_promedios += promedio
            count_promedios += 1

    promedio_general = (
        round(suma_promedios / count_promedios, 1) if count_promedios > 0 else ''
    )
    if max_notas < 1:
        max_notas = 1

    # ==================================================================
    # ASISTENCIA DEL ALUMNO
    # ==================================================================
    asist_raw = db.session.query(
        EdugestSessionAttendance.AttendanceStatusId,
        func.count(EdugestSessionAttendance.SessionAttendanceId)
    ).filter(
        EdugestSessionAttendance.OrganizationPersonRoleId == rol_id
    ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()

    asist_presentes = asist_ausentes = asist_atrasos = 0
    for sid, cnt in asist_raw:
        if sid == 1:
            asist_presentes = cnt
        elif sid == 2:
            asist_ausentes = cnt
        elif sid == 3:
            asist_atrasos = cnt

    total_sesiones = OrganizationCalendarSession.query.filter_by(
        OrganizationId=curso_id
    ).count()

    total_registros = asist_presentes + asist_ausentes + asist_atrasos
    porcentaje_asistencia = round(
        ((asist_presentes + asist_atrasos) / total_registros * 100), 0
    ) if total_registros > 0 else 0
    porcentaje_atrasos = round(
        (asist_atrasos / total_sesiones * 100), 0
    ) if total_sesiones > 0 else 0

    # ==================================================================
    # GENERACIÓN DEL PDF
    # ==================================================================
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm
    )
    elements = []
    styles = getSampleStyleSheet()

    # ── Estilos ──
    style_center_bold = ParagraphStyle(
        'CenterBold', parent=styles['Normal'], fontSize=10,
        alignment=TA_CENTER, fontName='Helvetica-Bold', leading=14
    )
    style_center = ParagraphStyle(
        'Center', parent=styles['Normal'], fontSize=10,
        alignment=TA_CENTER, fontName='Helvetica', leading=14
    )
    style_left_bold = ParagraphStyle(
        'LeftBold', parent=styles['Normal'], fontSize=10,
        alignment=TA_LEFT, fontName='Helvetica-Bold', leading=14
    )
    style_left = ParagraphStyle(
        'Left', parent=styles['Normal'], fontSize=9.5,
        alignment=TA_LEFT, fontName='Helvetica', leading=13
    )
    style_title = ParagraphStyle(
        'Title', parent=styles['Normal'], fontSize=14,
        alignment=TA_CENTER, fontName='Helvetica-Bold', leading=18, spaceAfter=4
    )
    style_subtitle = ParagraphStyle(
        'Subtitle', parent=styles['Normal'], fontSize=11,
        alignment=TA_CENTER, fontName='Helvetica', leading=14, spaceAfter=4
    )
    style_celda_center = ParagraphStyle(
        'CeldaCenter', parent=styles['Normal'], fontSize=9,
        alignment=TA_CENTER, fontName='Helvetica', leading=12
    )
    style_celda_left = ParagraphStyle(
        'CeldaLeft', parent=styles['Normal'], fontSize=9,
        alignment=TA_LEFT, fontName='Helvetica', leading=12
    )
    style_celda_bold_center = ParagraphStyle(
        'CeldaBoldCenter', parent=styles['Normal'], fontSize=9,
        alignment=TA_CENTER, fontName='Helvetica-Bold', leading=12
    )
    style_celda_bold_left = ParagraphStyle(
        'CeldaBoldLeft', parent=styles['Normal'], fontSize=9,
        alignment=TA_LEFT, fontName='Helvetica-Bold', leading=12
    )

    # ── 1. LOGO ──
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
    if os.path.exists(logo_path):
        img = RLImage(logo_path, width=2 * cm, height=2 * cm)
        logo_table = Table([[img]], colWidths=[16.5 * cm])
        logo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER')
        ]))
        elements.append(logo_table)
        elements.append(Spacer(1, 0.2 * cm))

    # ── 2. ENCABEZADO DEL ESTABLECIMIENTO ──
    elements.append(Paragraph(nombre_colegio, style_center_bold))
    elements.append(Spacer(1, 0.1 * cm))
    elements.append(Paragraph("INFORME DE CALIFICACIONES", style_title))
    elements.append(Paragraph(semestre, style_subtitle))
    elements.append(Spacer(1, 0.3 * cm))

    # ── 3. DATOS DEL ESTUDIANTE (FORMATO NARRATIVO) ──
    parts_nombre = [
        persona.FirstName, persona.MiddleName,
        persona.LastName, persona.SecondLastName
    ]
    nombre_alumno = ' '.join(p for p in parts_nombre if p).strip()

    curso_texto = (
        f"{grado.Name if grado else 'N/A'} {curso.ShortName or ''}".strip()
    )
    ident = PersonIdentifier.query.filter_by(
        PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
    ).first()
    rut_alumno = ident.Identifier if ident else 'Sin RUT'
    fecha_actual_str = datetime.now().strftime('%d/%m/%Y')

    texto_info = (
        f'Se otorga el presente informe de calificaciones a '
        f'<b>{nombre_alumno}</b> RUN: <b>{rut_alumno}</b> '
        f'estudiante del Curso <b>{curso_texto}</b> '
        f'con fecha <b>{fecha_actual_str}</b>, de acuerdo al plan '
        f'y programas de estudios aprobados por decreto o resolución '
        f'exenta de educación N° 1358 de 2011 y reglamento de evaluación '
        f'y promoción escolar decreto exento N° 67 de 2018.'
    )
    elements.append(Paragraph(texto_info, style_left))
    elements.append(Spacer(1, 0.4 * cm))

    # ── 4. TABLA DE CALIFICACIONES (COLUMNAS DINÁMICAS) ──
    n_cols_eval = max_notas
    ancho_disponible = 16.5 * cm
    ancho_asignatura = 5.5 * cm
    ancho_promedio = 1.8 * cm
    ancho_restante = ancho_disponible - ancho_asignatura - ancho_promedio
    ancho_eval = ancho_restante / n_cols_eval if n_cols_eval > 0 else 2 * cm
    col_widths = (
        [ancho_asignatura] + [ancho_eval] * n_cols_eval + [ancho_promedio]
    )

    # Encabezado: Asignaturas | N1 | N2 | ... | Prom.
    header = [Paragraph("<b>Asignaturas</b>", style_celda_bold_center)]
    for i in range(n_cols_eval):
        header.append(Paragraph(f"<b>N{i + 1}</b>", style_celda_bold_center))
    header.append(Paragraph("<b>Prom.</b>", style_celda_bold_center))
    data_rows = [header]

    # Filas de asignaturas
    for fila in filas_asignaturas:
        row = [Paragraph(fila['nombre'], style_celda_left)]
        for i in range(n_cols_eval):
            if i < len(fila['notas']):
                row.append(
                    Paragraph(str(fila['notas'][i]), style_celda_center)
                )
            else:
                row.append(Paragraph('', style_celda_center))
        prom_text = str(fila['promedio']) if fila['promedio'] != '' else ''
        row.append(
            Paragraph(f"<b>{prom_text}</b>", style_celda_bold_center)
        )
        data_rows.append(row)

    # Fila de promedio general
    row_prom = [Paragraph("<b>Promedio general</b>", style_celda_bold_left)]
    for i in range(n_cols_eval):
        row_prom.append(Paragraph('', style_celda_center))
    row_prom.append(
        Paragraph(f"<b>{promedio_general}</b>", style_celda_bold_center)
    )
    data_rows.append(row_prom)

    tabla_notas = Table(data_rows, colWidths=col_widths)
    tabla_notas.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.92, 0.92, 0.92)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
    ]))
    elements.append(tabla_notas)
    elements.append(Spacer(1, 0.5 * cm))

    # ── 5. TABLA DE ASISTENCIA ──
    asist_col_widths = [5.5 * cm, 5.5 * cm, 5.5 * cm]
    asist_rows = [
        [
            Paragraph(
                f"Asistencia: <b>{int(porcentaje_asistencia)}%</b>",
                style_celda_center
            ),
            Paragraph(
                f"Inasistencias: <b>{asist_ausentes}</b>",
                style_celda_center
            ),
            Paragraph(
                f"{total_sesiones} días trabajados",
                style_celda_center
            ),
        ],
        [
            Paragraph(
                f"Número de atrasos: <b>{asist_atrasos}</b>",
                style_celda_center
            ),
            Paragraph(
                "Tiempo acumulado en atrasos: <b>0 minutos</b>",
                style_celda_center
            ),
            Paragraph(
                f"Porcentaje de atrasos: <b>{int(porcentaje_atrasos)}%</b>"
                f" ({total_sesiones} días considerados)",
                style_celda_center
            ),
        ],
    ]

    tabla_asistencia = Table(asist_rows, colWidths=asist_col_widths)
    tabla_asistencia.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(tabla_asistencia)
    elements.append(Spacer(1, 0.5 * cm))

    # ── 6. OBSERVACIONES ──
    elements.append(Paragraph("<b>Observación:</b>", style_left_bold))
    elements.append(Spacer(1, 1.5 * cm))

    # ── 7. FIRMAS ──
    firma_data = [
        [
            Paragraph(f"<b>{nombre_prof_jefe}</b>", style_center),
            Paragraph(f"<b>{nombre_director}</b>", style_center),
        ],
        [
            Paragraph("Profesor(a) jefe", style_center),
            Paragraph("Director(a)", style_center),
        ],
    ]
    tabla_firmas = Table(firma_data, colWidths=[8.25 * cm, 8.25 * cm])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(tabla_firmas)
    elements.append(Spacer(1, 1.5 * cm))

    # Líneas de firma
    lineas = [[
        Paragraph("_" * 35, style_center),
        Paragraph("_" * 35, style_center)
    ]]
    tabla_lineas = Table(lineas, colWidths=[8.25 * cm, 8.25 * cm])
    tabla_lineas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))
    elements.append(tabla_lineas)
    elements.append(Spacer(1, 0.5 * cm))

    # ── 8. PIE DE PÁGINA ──
    meses = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    elements.append(Paragraph(
        f"Temuco, {meses.get(mes_actual, 'junio')} {anio_actual}",
        style_center
    ))

    # ── Construir y retornar PDF ──
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer, mimetype='application/pdf',
        download_name=f'informe_notas_{persona.FirstName}_{persona.LastName}.pdf'
    )




@reportes_bp.route('/grado/<int:grado_id>/grafico')
def grafico_grado(grado_id):
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)

    cursos = Organization.query.join(
        OrganizationRelationship, Organization.OrganizationId == OrganizationRelationship.OrganizationId
    ).filter(
        OrganizationRelationship.ParentOrganizationId == grado_id,
        Organization.RefOrganizationTypeId == 21
    ).all()

    total_p = total_a = total_t = 0
    for c in cursos:
        rol_ids = [r.OrganizationPersonRoleId for r in
                   OrganizationPersonRole.query.filter_by(OrganizationId=c.OrganizationId, RoleId=6, ExitDate=None).all()]
        if rol_ids:
            asist = db.session.query(
                EdugestSessionAttendance.AttendanceStatusId,
                func.count(EdugestSessionAttendance.SessionAttendanceId)
            ).filter(
                EdugestSessionAttendance.OrganizationPersonRoleId.in_(rol_ids),
                EdugestSessionAttendance.FechaRegistro >= fecha_inicio,
                EdugestSessionAttendance.FechaRegistro <= fecha_fin
            ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()
            for sid, cnt in asist:
                if sid == 1:
                    total_p += cnt
                elif sid == 2:
                    total_a += cnt
                elif sid == 3:
                    total_t += cnt

    fig, ax = plt.subplots(figsize=(4, 4))
    labels = ['Presentes', 'Ausentes', 'Atrasados']
    sizes = [total_p, total_a, total_t]
    chart_colors = ['#10b981', '#f43f5e', '#f59e0b']
    if sum(sizes) > 0:
        ax.pie(sizes, labels=labels, colors=chart_colors, autopct='%1.1f%%', startangle=90)
    else:
        ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=14)
    ax.set_title('Distribución de Asistencia')
    plt.tight_layout()

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)

    return send_file(img_buffer, mimetype='image/png', download_name='grafico_grado.png')
