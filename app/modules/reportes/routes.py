import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, send_file, current_app
from app.database import db
from sqlalchemy import func, extract
from app.models.mineduc import (
    Organization, OrganizationPersonRole, OrganizationCalendarSession,
    PersonIdentifier, Person, OrganizationRelationship
)
from app.models.edugest import (
    EdugestSessionAttendance, EdugestStudentObservation,
    EdugestManualGrade, EdugestAssessmentInstrument
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
import os
from collections import defaultdict

reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')


@reportes_bp.route('/')
def index():
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
                cursos_data.append({
                    'grado_id': grado.OrganizationId, 'grado_nombre': grado.Name,
                    'curso_id': curso.OrganizationId, 'curso_nombre': curso.Name,
                    'letra': curso.ShortName or 'Sin letra', 'total_alumnos': total_alumnos
                })
    return render_template('reportes/index.html', cursos=cursos_data)


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

    alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=curso_id, RoleId=6, ExitDate=None).all()
    rol_ids = [r.OrganizationPersonRoleId for r in alumnos_roles]

    asistencias = db.session.query(
        EdugestSessionAttendance.OrganizationPersonRoleId,
        EdugestSessionAttendance.AttendanceStatusId,
        func.count(EdugestSessionAttendance.SessionAttendanceId).label('total')
    ).filter(
        EdugestSessionAttendance.OrganizationPersonRoleId.in_(rol_ids),
        EdugestSessionAttendance.FechaRegistro >= fecha_inicio,
        EdugestSessionAttendance.FechaRegistro <= fecha_fin
    ).group_by(EdugestSessionAttendance.OrganizationPersonRoleId, EdugestSessionAttendance.AttendanceStatusId).all()

    notas_raw = db.session.query(
        EdugestManualGrade.OrganizationPersonRoleId, EdugestManualGrade.InstrumentId,
        EdugestManualGrade.Score, EdugestManualGrade.IsManual, EdugestManualGrade.CreatedAt,
        EdugestAssessmentInstrument.Title.label('instrument_title'),
        Organization.OrganizationId.label('asignatura_id'), Organization.Name.label('asignatura_nombre')
    ).join(EdugestAssessmentInstrument, EdugestManualGrade.InstrumentId == EdugestAssessmentInstrument.InstrumentId
    ).join(Organization, EdugestAssessmentInstrument.OrganizationId == Organization.OrganizationId
    ).filter(EdugestManualGrade.OrganizationPersonRoleId.in_(rol_ids)).all()

    anotaciones_raw = db.session.query(
        EdugestStudentObservation.OrganizationPersonRoleId, EdugestStudentObservation.Tipo,
        EdugestStudentObservation.Detalle, EdugestStudentObservation.FechaRegistro,
        EdugestStudentObservation.AsignaturaId, Organization.Name.label('asignatura_nombre')
    ).outerjoin(Organization, EdugestStudentObservation.AsignaturaId == Organization.OrganizationId
    ).filter(
        EdugestStudentObservation.OrganizationPersonRoleId.in_(rol_ids),
        EdugestStudentObservation.FechaRegistro >= fecha_inicio,
        EdugestStudentObservation.FechaRegistro <= fecha_fin
    ).order_by(EdugestStudentObservation.FechaRegistro.desc()).all()

    alumnos_reporte = []
    total_presentes = total_ausentes = total_atrasados = 0

    for rol in alumnos_roles:
        persona = Person.query.get(rol.PersonId)
        if not persona: continue
        ident = PersonIdentifier.query.filter_by(PersonId=persona.PersonId, RefPersonIdentificationSystemId=51).first()

        asist_alumno = [a for a in asistencias if a.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        presentes = sum(a.total for a in asist_alumno if a.AttendanceStatusId == 1)
        ausentes = sum(a.total for a in asist_alumno if a.AttendanceStatusId == 2)
        atrasados = sum(a.total for a in asist_alumno if a.AttendanceStatusId == 3)
        total_asist = presentes + ausentes + atrasados
        total_presentes += presentes; total_ausentes += ausentes; total_atrasados += atrasados

        notas_alumno = [n for n in notas_raw if n.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        notas_por_asignatura = {}
        for n in notas_alumno:
            asig_id = n.asignatura_id
            asig_nombre = n.asignatura_nombre or f'Asignatura #{asig_id}'
            if asig_id not in notas_por_asignatura:
                notas_por_asignatura[asig_id] = {'nombre': asig_nombre, 'notas': [], 'evaluaciones': 0}
            notas_por_asignatura[asig_id]['notas'].append({
                'instrumento': n.instrument_title or f'Evaluación #{n.InstrumentId}',
                'nota': round(n.Score, 1), 'tipo': 'Manual' if n.IsManual else 'Automática',
                'fecha': n.CreatedAt.strftime('%d/%m/%Y') if n.CreatedAt else 'N/A'
            })
            notas_por_asignatura[asig_id]['evaluaciones'] += 1

        for asig_id in notas_por_asignatura:
            notas_list = notas_por_asignatura[asig_id]['notas']
            suma = sum(n['nota'] for n in notas_list)
            notas_por_asignatura[asig_id]['promedio'] = round(suma / len(notas_list), 1) if notas_list else None

        promedios_asig = [notas_por_asignatura[a]['promedio'] for a in notas_por_asignatura if notas_por_asignatura[a]['promedio'] is not None]
        promedio_general_final = round(sum(promedios_asig) / len(promedios_asig), 1) if promedios_asig else None
        total_evaluaciones = sum(notas_por_asignatura[a]['evaluaciones'] for a in notas_por_asignatura)

        anot_alumno = [a for a in anotaciones_raw if a.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        anotaciones_list = []; conteo_anotaciones = {'Positiva': 0, 'Negativa': 0, 'Otra': 0}
        for a in anot_alumno:
            anotaciones_list.append({'tipo': a.Tipo, 'detalle': a.Detalle, 'asignatura': a.asignatura_nombre or 'General',
                'fecha': a.FechaRegistro.strftime('%d/%m/%Y') if a.FechaRegistro else 'N/A'})
            conteo_anotaciones[a.Tipo] = conteo_anotaciones.get(a.Tipo, 0) + 1

        alumnos_reporte.append({
            'rol_id': rol.OrganizationPersonRoleId, 'rut': ident.Identifier if ident else 'Sin RUT',
            'nombres': persona.FirstName, 'apellido_paterno': persona.LastName or '', 'apellido_materno': persona.SecondLastName or '',
            'presentes': presentes, 'ausentes': ausentes, 'atrasados': atrasados, 'total': total_asist,
            'porcentaje_asistencia': round((presentes / total_asist * 100), 1) if total_asist > 0 else 0,
            'notas_por_asignatura': notas_por_asignatura, 'promedio_general_final': promedio_general_final,
            'total_evaluaciones': total_evaluaciones, 'total_asignaturas': len(notas_por_asignatura),
            'anotaciones': anotaciones_list, 'conteo_anotaciones': conteo_anotaciones, 'total_anotaciones': len(anotaciones_list)
        })

    alumnos_reporte.sort(key=lambda x: x['apellido_paterno'])
    chart_data = {'presentes': total_presentes, 'ausentes': total_ausentes, 'atrasados': total_atrasados}
    todos_promedios_finales = [a['promedio_general_final'] for a in alumnos_reporte if a['promedio_general_final'] is not None]
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

    return render_template('reportes/curso.html', curso=curso, grado=grado, alumnos=alumnos_reporte,
                         chart_data=chart_data, resumen_notas=resumen_notas, resumen_anotaciones=resumen_anotaciones,
                         periodo=periodo, fecha_inicio=fecha_inicio.strftime('%Y-%m-%d'),
                         fecha_fin=fecha_fin.strftime('%Y-%m-%d'), fecha_ref=fecha_ref)


@reportes_bp.route('/curso/<int:curso_id>/informe_notas/<int:rol_id>')
def informe_notas_pdf(curso_id, rol_id):
    """Genera informe de notas parciales en PDF con formato oficial exacto."""
    rol = OrganizationPersonRole.query.get_or_404(rol_id)
    persona = Person.query.get_or_404(rol.PersonId)
    curso = Organization.query.get_or_404(curso_id)
    relacion = OrganizationRelationship.query.filter_by(OrganizationId=curso_id).first()
    grado = Organization.query.get(relacion.ParentOrganizationId) if relacion else None
    colegio = Organization.query.filter_by(RefOrganizationTypeId=1).first()
    nombre_colegio = colegio.Name if colegio else 'NombreColegio'

    prof_jefe = db.session.query(Person).join(OrganizationPersonRole, Person.PersonId == OrganizationPersonRole.PersonId).filter(
        OrganizationPersonRole.OrganizationId == curso_id, OrganizationPersonRole.RoleId == 3, OrganizationPersonRole.ExitDate == None
    ).first()
    nombre_prof_jefe = f"{prof_jefe.FirstName} {prof_jefe.LastName or ''}".strip() if prof_jefe else 'No asignado'

    anio_actual = datetime.now().year

    # Obtener notas del alumno agrupadas por asignatura
    notas_raw = db.session.query(EdugestManualGrade.Score, EdugestManualGrade.CreatedAt, Organization.Name.label('asignatura_nombre')
    ).join(EdugestAssessmentInstrument, EdugestManualGrade.InstrumentId == EdugestAssessmentInstrument.InstrumentId
    ).join(Organization, EdugestAssessmentInstrument.OrganizationId == Organization.OrganizationId
    ).filter(EdugestManualGrade.OrganizationPersonRoleId == rol_id).order_by(Organization.Name, EdugestManualGrade.CreatedAt).all()

    notas_por_asignatura = defaultdict(list)
    for n in notas_raw:
        notas_por_asignatura[n.asignatura_nombre].append({'nota': round(n.Score, 1), 'fecha': n.CreatedAt})

    # Obtener anotaciones del alumno
    anotaciones_raw = db.session.query(
        EdugestStudentObservation.Tipo, EdugestStudentObservation.Detalle,
        EdugestStudentObservation.FechaRegistro, Organization.Name.label('asignatura_nombre')
    ).outerjoin(Organization, EdugestStudentObservation.AsignaturaId == Organization.OrganizationId
    ).filter(EdugestStudentObservation.OrganizationPersonRoleId == rol_id
    ).order_by(EdugestStudentObservation.FechaRegistro.desc()).all()

    filas_asignaturas = []
    suma_promedios = 0; count_promedios = 0
    for asignatura in sorted(notas_por_asignatura.keys()):
        notas = sorted(notas_por_asignatura[asignatura], key=lambda x: x['fecha'] if x['fecha'] else datetime.min)
        n1 = str(notas[0]['nota']) if len(notas) > 0 else ''
        n2 = str(notas[1]['nota']) if len(notas) > 1 else ''
        n3 = str(notas[2]['nota']) if len(notas) > 2 else ''
        n4 = str(notas[3]['nota']) if len(notas) > 3 else ''
        vals = [n['nota'] for n in notas]
        promedio = round(sum(vals) / len(vals), 1) if vals else ''
        if promedio != '':
            suma_promedios += promedio; count_promedios += 1
        filas_asignaturas.append([asignatura, n1, n2, n3, n4, str(promedio)])

    promedio_general = round(suma_promedios / count_promedios, 1) if count_promedios > 0 else ''

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.2*cm, leftMargin=1.2*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
    elements = []
    styles = getSampleStyleSheet()

    style_center_bold = ParagraphStyle('CenterBold', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=14)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, fontName='Helvetica', leading=14)
    style_left_bold = ParagraphStyle('LeftBold', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, fontName='Helvetica-Bold', leading=14)
    style_left = ParagraphStyle('Left', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, fontName='Helvetica', leading=14)
    style_title = ParagraphStyle('Title', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=18, spaceAfter=4)
    style_subtitle = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=16, spaceAfter=8)
    style_celda_center = ParagraphStyle('CeldaCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, fontName='Helvetica', leading=12)
    style_celda_left = ParagraphStyle('CeldaLeft', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, fontName='Helvetica', leading=12)
    style_celda_bold_center = ParagraphStyle('CeldaBoldCenter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=12)
    style_celda_bold_left = ParagraphStyle('CeldaBoldLeft', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, fontName='Helvetica-Bold', leading=12)

    # Logo
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
    if os.path.exists(logo_path):
        from reportlab.platypus import Image as RLImage
        img = RLImage(logo_path, width=2*cm, height=2*cm)
        logo_table = Table([[img]], colWidths=[16*cm])
        logo_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        elements.append(logo_table)
        elements.append(Spacer(1, 0.2*cm))

    elements.append(Paragraph(f'Escuela Particular N°XXX "{nombre_colegio}"', style_center_bold))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("INFORME AVANCE DE NOTAS PARCIALES 1° SEMESTRE", style_title))
    elements.append(Paragraph(f"Año {anio_actual}", style_subtitle))
    elements.append(Spacer(1, 0.2*cm))

    nombre_alumno = f"{persona.FirstName} {persona.LastName or ''} {persona.SecondLastName or ''}".strip()
    curso_texto = f"{grado.Name if grado else 'N/A'} {curso.ShortName or ''}".strip()

    datos_data = [
        [Paragraph("<b>Alumno</b>", style_celda_bold_left), Paragraph(nombre_alumno, style_celda_left)],
        [Paragraph("<b>Curso</b>", style_celda_bold_left), Paragraph(curso_texto, style_celda_left)],
        [Paragraph("<b>Profesor (a) Jefe</b>", style_celda_bold_left), Paragraph(nombre_prof_jefe, style_celda_left)],
    ]
    tabla_datos = Table(datos_data, colWidths=[4*cm, 12.5*cm])
    tabla_datos.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(tabla_datos)
    elements.append(Spacer(1, 0.3*cm))

    # Tabla principal: 9 columnas
    col_widths = [6*cm, 1.3*cm, 1.3*cm, 1.3*cm, 1.3*cm, 1.3*cm, 1.3*cm, 1.3*cm, 2.5*cm]

    header_row1 = [
        Paragraph("<b>Asignaturas</b>", style_celda_bold_center),
        Paragraph("<b>Calificaciones</b>", style_celda_bold_center), '', '', '', '', '', '',
        Paragraph("<b>Promedio</b>", style_celda_bold_center)
    ]
    header_row2 = [
        '',
        Paragraph("<b>1</b>", style_celda_bold_center),
        Paragraph("<b>2</b>", style_celda_bold_center),
        Paragraph("<b>3</b>", style_celda_bold_center),
        Paragraph("<b>4</b>", style_celda_bold_center),
        '', '', '',
        Paragraph("<b>Promedio</b>", style_celda_bold_center)
    ]

    data_rows = []
    for fila in filas_asignaturas:
        data_rows.append([
            Paragraph(fila[0], style_celda_left),
            Paragraph(fila[1], style_celda_center) if fila[1] else Paragraph("", style_celda_center),
            Paragraph(fila[2], style_celda_center) if fila[2] else Paragraph("", style_celda_center),
            Paragraph(fila[3], style_celda_center) if fila[3] else Paragraph("", style_celda_center),
            Paragraph(fila[4], style_celda_center) if fila[4] else Paragraph("", style_celda_center),
            '', '', '',
            Paragraph(f"<b>{fila[5]}</b>" if fila[5] else "", style_celda_bold_center)
        ])

    if not data_rows:
        for i in range(5):
            data_rows.append([Paragraph(f'Asignatura {i+1}', style_celda_left), '', '', '', '', '', '', '', ''])

    promedio_row = ['', '', '', '', '', '', '', '', Paragraph("<b>Promedio General</b>", style_celda_bold_center)]
    promedio_val_row = ['', '', '', '', '', '', '', '', Paragraph(f"<b>{promedio_general}</b>" if promedio_general else "", style_celda_bold_center)]

    all_rows = [header_row1, header_row2] + data_rows + [promedio_row, promedio_val_row]
    tabla_notas = Table(all_rows, colWidths=col_widths, repeatRows=2)

    tabla_style = TableStyle([
        # Grid completo para toda la tabla
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),

        # Líneas horizontales entre cada fila de datos
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
        ('LINEBELOW', (0, 1), (-1, 1), 1, colors.black),

        # Líneas verticales principales
        ('LINEAFTER', (0, 0), (0, -1), 1, colors.black),
        ('LINEAFTER', (4, 1), (4, -1), 0.5, colors.black),
        ('LINEAFTER', (8, 0), (8, -1), 1, colors.black),

        # Columnas grises (5, 6, 7)
        ('BACKGROUND', (5, 1), (7, -3), colors.HexColor('#cccccc')),

        # Header backgrounds
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor('#f5f5f5')),
        ('BACKGROUND', (1, 0), (7, 0), colors.HexColor('#f5f5f5')),
        ('BACKGROUND', (8, 0), (8, 1), colors.HexColor('#f5f5f5')),
        ('BACKGROUND', (1, 1), (4, 1), colors.HexColor('#f5f5f5')),

        # Promedio General background
        ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor('#f5f5f5')),

        # Alineación
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (0, -1), 6),
        ('RIGHTPADDING', (0, 0), (0, -1), 6),
    ])

    # Líneas horizontales entre cada fila de asignaturas
    for i in range(2, 2 + len(data_rows)):
        tabla_style.add('LINEBELOW', (0, i), (-1, i), 0.5, colors.black)

    tabla_style.add('SPAN', (0, 0), (0, 1))
    tabla_style.add('SPAN', (1, 0), (7, 0))
    tabla_style.add('SPAN', (8, 0), (8, 1))
    tabla_style.add('SPAN', (0, -2), (7, -2))
    tabla_style.add('SPAN', (0, -1), (7, -1))
    tabla_notas.setStyle(tabla_style)
    elements.append(tabla_notas)
    elements.append(Spacer(1, 0.4*cm))

    # === OBSERVACIONES CON ANOTACIONES ===
    obs_text = "<b>Observaciones:</b>"

    # Agregar anotaciones diferenciadas
    anot_positivas = [a for a in anotaciones_raw if a.Tipo == 'Positiva']
    anot_negativas = [a for a in anotaciones_raw if a.Tipo == 'Negativa']
    anot_otras = [a for a in anotaciones_raw if a.Tipo not in ['Positiva', 'Negativa']]

    obs_lines = [obs_text]

    if anot_positivas:
        obs_lines.append("<b>Positivas:</b>")
        for a in anot_positivas:
            fecha = a.FechaRegistro.strftime('%d/%m/%Y') if a.FechaRegistro else ''
            asig = a.asignatura_nombre or 'General'
            obs_lines.append(f"• {asig}: {a.Detalle} ({fecha})")

    if anot_negativas:
        obs_lines.append("<b>Negativas:</b>")
        for a in anot_negativas:
            fecha = a.FechaRegistro.strftime('%d/%m/%Y') if a.FechaRegistro else ''
            asig = a.asignatura_nombre or 'General'
            obs_lines.append(f"• {asig}: {a.Detalle} ({fecha})")

    if anot_otras:
        obs_lines.append("<b>Otras:</b>")
        for a in anot_otras:
            fecha = a.FechaRegistro.strftime('%d/%m/%Y') if a.FechaRegistro else ''
            asig = a.asignatura_nombre or 'General'
            obs_lines.append(f"• {asig}: {a.Detalle} ({fecha})")

    if not anotaciones_raw:
        obs_lines.append("Sin observaciones registradas.")

    # Construir filas de observaciones
    obs_rows = [[Paragraph(line, style_celda_left)] for line in obs_lines]
    # Rellenar hasta 4 filas mínimo para mantener tamaño
    while len(obs_rows) < 4:
        obs_rows.append([Paragraph("", style_celda_left)])

    tabla_obs = Table(obs_rows, colWidths=[16.5*cm])
    tabla_obs.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(tabla_obs)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("• P: Pendiente", style_left))

    doc.build(elements)
    buffer.seek(0)
    apellido = persona.LastName or ''
    nombre_archivo = f"Informe_Notas_{apellido}_{persona.FirstName}_{anio_actual}.pdf"
    return Response(buffer, mimetype="application/pdf", headers={"Content-Disposition": f"attachment;filename={nombre_archivo}"})


@reportes_bp.route('/curso/<int:curso_id>/grafico')
def grafico_asistencia(curso_id):
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)

    alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=curso_id, RoleId=6, ExitDate=None).all()
    asistencias = db.session.query(EdugestSessionAttendance.AttendanceStatusId, func.count(EdugestSessionAttendance.SessionAttendanceId).label('total')).filter(
        EdugestSessionAttendance.OrganizationPersonRoleId.in_([r.OrganizationPersonRoleId for r in alumnos_roles]),
        EdugestSessionAttendance.FechaRegistro >= fecha_inicio, EdugestSessionAttendance.FechaRegistro <= fecha_fin
    ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()

    labels, sizes, colors_list, explode = [], [], [], []
    estados = {1: ('Presentes', '#10b981', 0.05), 2: ('Ausentes', '#f43f5e', 0.05), 3: ('Atrasados', '#f59e0b', 0.05)}
    for estado_id, total in asistencias:
        if estado_id in estados and total > 0:
            label, color, exp = estados[estado_id]
            labels.append(f'{label}\n({total})'); sizes.append(total); colors_list.append(color); explode.append(exp)
    if not sizes:
        labels, sizes, colors_list, explode = ['Sin registros'], [1], ['#e5e7eb'], [0]

    fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors_list,
        autopct='%1.1f%%', shadow=False, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
    for autotext in autotexts:
        autotext.set_color('white'); autotext.set_fontsize(12); autotext.set_fontweight('bold')
    ax.set_title(f'Distribución de Asistencia\n{fecha_inicio.strftime("%d/%m/%Y")} - {fecha_fin.strftime("%d/%m/%Y")}', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    img = BytesIO()
    plt.savefig(img, format='png', dpi=100, bbox_inches='tight', facecolor='white', edgecolor='none')
    img.seek(0); plt.close(fig)
    return send_file(img, mimetype='image/png')


@reportes_bp.route('/curso/<int:curso_id>/exportar')
def exportar_asistencia(curso_id):
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)
    curso = Organization.query.get_or_404(curso_id)
    relacion = OrganizationRelationship.query.filter_by(OrganizationId=curso_id).first()
    grado = Organization.query.get(relacion.ParentOrganizationId) if relacion else None
    alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=curso_id, RoleId=6, ExitDate=None).all()
    asistencias = EdugestSessionAttendance.query.filter(
        EdugestSessionAttendance.OrganizationPersonRoleId.in_([r.OrganizationPersonRoleId for r in alumnos_roles]),
        EdugestSessionAttendance.FechaRegistro >= fecha_inicio, EdugestSessionAttendance.FechaRegistro <= fecha_fin
    ).order_by(EdugestSessionAttendance.FechaRegistro).all()

    si = StringIO()
    writer = csv.writer(si, delimiter=';')
    writer.writerow(['Reporte de Asistencia', f'Grado: {grado.Name if grado else "N/A"}', f'Curso: {curso.Name}', f'Letra: {curso.ShortName or "N/A"}'])
    writer.writerow([f'Período: {periodo.upper()}', f'Desde: {fecha_inicio.strftime("%d/%m/%Y")}', f'Hasta: {fecha_fin.strftime("%d/%m/%Y")}', f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}'])
    writer.writerow([])
    writer.writerow(['RUT', 'Apellido Paterno', 'Apellido Materno', 'Nombres', 'Fecha Registro', 'Hora Inicio Clase', 'Hora Término Clase', 'Estado Asistencia', 'Total Presentes', 'Total Ausentes', 'Total Atrasados'])

    for rol in alumnos_roles:
        persona = Person.query.get(rol.PersonId)
        if not persona: continue
        ident = PersonIdentifier.query.filter_by(PersonId=persona.PersonId, RefPersonIdentificationSystemId=51).first()
        asist_alumno = [a for a in asistencias if a.OrganizationPersonRoleId == rol.OrganizationPersonRoleId]
        presentes = sum(1 for a in asist_alumno if a.AttendanceStatusId == 1)
        ausentes = sum(1 for a in asist_alumno if a.AttendanceStatusId == 2)
        atrasados = sum(1 for a in asist_alumno if a.AttendanceStatusId == 3)
        for asist in asist_alumno:
            estado_texto = {1: 'Presente', 2: 'Ausente', 3: 'Atrasado'}.get(asist.AttendanceStatusId, 'Desconocido')
            writer.writerow([ident.Identifier if ident else 'Sin RUT', persona.LastName or '', persona.SecondLastName or '', persona.FirstName,
                asist.FechaRegistro.strftime('%d/%m/%Y %H:%M') if asist.FechaRegistro else '', asist.HoraInicio or 'No registrada', asist.HoraTermino or 'No registrada',
                estado_texto, presentes, ausentes, atrasados])
        if not asist_alumno:
            writer.writerow([ident.Identifier if ident else 'Sin RUT', persona.LastName or '', persona.SecondLastName or '', persona.FirstName,
                'Sin registros', '', '', 'Sin registro', 0, 0, 0])

    output = BytesIO()
    output.write(si.getvalue().encode('utf-8-sig'))
    output.seek(0)
    nombre_archivo = f"Reporte_Asistencia_{grado.Name if grado else 'Curso'}_{curso.ShortName or 'X'}_{periodo}_{fecha_base.strftime('%Y%m')}.csv"
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={nombre_archivo}"})


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

    cursos = Organization.query.join(OrganizationRelationship, Organization.OrganizationId == OrganizationRelationship.OrganizationId).filter(
        OrganizationRelationship.ParentOrganizationId == grado_id, Organization.RefOrganizationTypeId == 21
    ).order_by(Organization.ShortName).all()

    cursos_reporte = []
    grado_presentes = grado_ausentes = grado_atrasados = 0

    for curso in cursos:
        alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=curso.OrganizationId, RoleId=6, ExitDate=None).all()
        if not alumnos_roles: continue
        rol_ids = [r.OrganizationPersonRoleId for r in alumnos_roles]

        asistencias = db.session.query(EdugestSessionAttendance.AttendanceStatusId, func.count(EdugestSessionAttendance.SessionAttendanceId).label('total')).filter(
            EdugestSessionAttendance.OrganizationPersonRoleId.in_(rol_ids),
            EdugestSessionAttendance.FechaRegistro >= fecha_inicio, EdugestSessionAttendance.FechaRegistro <= fecha_fin
        ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()
        presentes = sum(a.total for a in asistencias if a.AttendanceStatusId == 1)
        ausentes = sum(a.total for a in asistencias if a.AttendanceStatusId == 2)
        atrasados = sum(a.total for a in asistencias if a.AttendanceStatusId == 3)
        total_asist = presentes + ausentes + atrasados
        grado_presentes += presentes; grado_ausentes += ausentes; grado_atrasados += atrasados

        notas_curso = db.session.query(EdugestManualGrade.Score, EdugestManualGrade.OrganizationPersonRoleId).join(
            EdugestAssessmentInstrument, EdugestManualGrade.InstrumentId == EdugestAssessmentInstrument.InstrumentId
        ).filter(EdugestManualGrade.OrganizationPersonRoleId.in_(rol_ids)).all()
        notas_por_alumno = {}
        for n in notas_curso:
            if n.OrganizationPersonRoleId not in notas_por_alumno: notas_por_alumno[n.OrganizationPersonRoleId] = []
            notas_por_alumno[n.OrganizationPersonRoleId].append(n.Score)
        promedios_finales = [sum(scores)/len(scores) for scores in notas_por_alumno.values() if scores]
        promedio_notas = round(sum(promedios_finales)/len(promedios_finales), 1) if promedios_finales else None
        total_evaluaciones = len(notas_curso)

        anotaciones_curso = db.session.query(EdugestStudentObservation.Tipo, func.count(EdugestStudentObservation.ObservationId).label('total')).filter(
            EdugestStudentObservation.OrganizationPersonRoleId.in_(rol_ids),
            EdugestStudentObservation.FechaRegistro >= fecha_inicio, EdugestStudentObservation.FechaRegistro <= fecha_fin
        ).group_by(EdugestStudentObservation.Tipo).all()
        anot_dict = {'Positiva': 0, 'Negativa': 0, 'Otra': 0}
        for a in anotaciones_curso: anot_dict[a.Tipo] = a.total

        cursos_reporte.append({
            'curso_id': curso.OrganizationId, 'letra': curso.ShortName or 'Sin letra', 'total_alumnos': len(alumnos_roles),
            'presentes': presentes, 'ausentes': ausentes, 'atrasados': atrasados, 'total_registros': total_asist,
            'porcentaje_asistencia': round((presentes/total_asist*100), 1) if total_asist > 0 else 0,
            'promedio_notas': promedio_notas, 'total_evaluaciones': total_evaluaciones,
            'anotaciones_positivas': anot_dict['Positiva'], 'anotaciones_negativas': anot_dict['Negativa'],
            'anotaciones_otras': anot_dict['Otra'], 'total_anotaciones': sum(anot_dict.values())
        })

    chart_data = {'presentes': grado_presentes, 'ausentes': grado_ausentes, 'atrasados': grado_atrasados}
    notas_grado_vals = [c['promedio_notas'] for c in cursos_reporte if c['promedio_notas'] is not None]
    resumen_grado = {
        'promedio_general': round(sum(notas_grado_vals)/len(notas_grado_vals), 1) if notas_grado_vals else None,
        'total_anotaciones_positivas': sum(c['anotaciones_positivas'] for c in cursos_reporte),
        'total_anotaciones_negativas': sum(c['anotaciones_negativas'] for c in cursos_reporte),
        'total_anotaciones_otras': sum(c['anotaciones_otras'] for c in cursos_reporte)
    }
    return render_template('reportes/grado.html', grado=grado, cursos=cursos_reporte, chart_data=chart_data,
                         resumen_grado=resumen_grado, periodo=periodo,
                         fecha_inicio=fecha_inicio.strftime('%Y-%m-%d'), fecha_fin=fecha_fin.strftime('%Y-%m-%d'), fecha_ref=fecha_ref)


@reportes_bp.route('/grado/<int:grado_id>/grafico')
def grafico_grado(grado_id):
    periodo = request.args.get('periodo', 'mes')
    fecha_ref = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    try:
        fecha_base = datetime.strptime(fecha_ref, '%Y-%m-%d')
    except ValueError:
        fecha_base = datetime.now()
    fecha_inicio, fecha_fin = calcular_rango_fechas(fecha_base, periodo)
    cursos = Organization.query.join(OrganizationRelationship, Organization.OrganizationId == OrganizationRelationship.OrganizationId).filter(
        OrganizationRelationship.ParentOrganizationId == grado_id, Organization.RefOrganizationTypeId == 21
    ).all()
    totales = {1: 0, 2: 0, 3: 0}
    for curso in cursos:
        alumnos_roles = OrganizationPersonRole.query.filter_by(OrganizationId=curso.OrganizationId, RoleId=6, ExitDate=None).all()
        if not alumnos_roles: continue
        asistencias = db.session.query(EdugestSessionAttendance.AttendanceStatusId, func.count(EdugestSessionAttendance.SessionAttendanceId).label('total')).filter(
            EdugestSessionAttendance.OrganizationPersonRoleId.in_([r.OrganizationPersonRoleId for r in alumnos_roles]),
            EdugestSessionAttendance.FechaRegistro >= fecha_inicio, EdugestSessionAttendance.FechaRegistro <= fecha_fin
        ).group_by(EdugestSessionAttendance.AttendanceStatusId).all()
        for a in asistencias:
            if a.AttendanceStatusId in totales: totales[a.AttendanceStatusId] += a.total

    labels, sizes, colors_list, explode = [], [], [], []
    estados = {1: ('Presentes', '#10b981', 0.05), 2: ('Ausentes', '#f43f5e', 0.05), 3: ('Atrasados', '#f59e0b', 0.05)}
    for estado_id, total in totales.items():
        if total > 0:
            label, color, exp = estados[estado_id]
            labels.append(f'{label}\n({total})'); sizes.append(total); colors_list.append(color); explode.append(exp)
    if not sizes:
        labels, sizes, colors_list, explode = ['Sin registros'], [1], ['#e5e7eb'], [0]
    grado = Organization.query.get_or_404(grado_id)
    fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors_list,
        autopct='%1.1f%%', shadow=False, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
    for autotext in autotexts:
        autotext.set_color('white'); autotext.set_fontsize(12); autotext.set_fontweight('bold')
    ax.set_title(f'Asistencia Consolidada - {grado.Name}\n{fecha_inicio.strftime("%d/%m/%Y")} - {fecha_fin.strftime("%d/%m/%Y")}', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    img = BytesIO()
    plt.savefig(img, format='png', dpi=100, bbox_inches='tight', facecolor='white', edgecolor='none')
    img.seek(0); plt.close(fig)
    return send_file(img, mimetype='image/png')


def calcular_rango_fechas(fecha_base, periodo):
    if periodo == 'mes':
        fecha_inicio = fecha_base.replace(day=1, hour=0, minute=0, second=0)
        if fecha_base.month == 12:
            fecha_fin = fecha_base.replace(year=fecha_base.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fecha_fin = fecha_base.replace(month=fecha_base.month + 1, day=1) - timedelta(days=1)
        fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
    elif periodo == 'semestre':
        if fecha_base.month <= 6:
            fecha_inicio = fecha_base.replace(month=1, day=1, hour=0, minute=0, second=0)
            fecha_fin = fecha_base.replace(month=6, day=30, hour=23, minute=59, second=59)
        else:
            fecha_inicio = fecha_base.replace(month=7, day=1, hour=0, minute=0, second=0)
            fecha_fin = fecha_base.replace(month=12, day=31, hour=23, minute=59, second=59)
    elif periodo == 'anio':
        fecha_inicio = fecha_base.replace(month=1, day=1, hour=0, minute=0, second=0)
        fecha_fin = fecha_base.replace(month=12, day=31, hour=23, minute=59, second=59)
    else:
        fecha_inicio = fecha_base.replace(day=1, hour=0, minute=0, second=0)
        if fecha_base.month == 12:
            fecha_fin = fecha_base.replace(year=fecha_base.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fecha_fin = fecha_base.replace(month=fecha_base.month + 1, day=1) - timedelta(days=1)
        fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
    return fecha_inicio, fecha_fin