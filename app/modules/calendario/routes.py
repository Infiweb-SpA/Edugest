from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.database import db
from app.models.mineduc import (
    Organization, OrganizationRelationship, OrganizationPersonRole,
    PersonRelationship
)
from app.models.edugest import EdugestRolePermission, EdugestModule, EdugestAssessmentInstrument
from app.models.EdugestCalendar import EdugestCalendarEvent
from app.modules.auth.routes import permiso_requerido
from datetime import date, datetime
import calendar

calendario_bp = Blueprint('calendario', __name__, url_prefix='/calendario')

# ============================================================================
# CONFIGURACIÓN DE TIPOS DE EVENTO
# ============================================================================
EVENT_TYPES = {
    'Evaluacion': {
        'label': 'Evaluación',
        'bg': 'bg-blue-500', 'text': 'text-blue-700',
        'bg_light': 'bg-blue-50', 'border': 'border-blue-200'
    },
    'Vacunacion': {
        'label': 'Vacunación',
        'bg': 'bg-pink-500', 'text': 'text-pink-700',
        'bg_light': 'bg-pink-50', 'border': 'border-pink-200'
    },
    'Taller': {
        'label': 'Taller',
        'bg': 'bg-green-500', 'text': 'text-green-700',
        'bg_light': 'bg-green-50', 'border': 'border-green-200'
    },
    'ActividadExtracurricular': {
        'label': 'Actividad Extracurricular',
        'bg': 'bg-purple-500', 'text': 'text-purple-700',
        'bg_light': 'bg-purple-50', 'border': 'border-purple-200'
    },
    'Reunion': {
        'label': 'Reunión',
        'bg': 'bg-orange-500', 'text': 'text-orange-700',
        'bg_light': 'bg-orange-50', 'border': 'border-orange-200'
    },
    'Feriado': {
        'label': 'Feriado',
        'bg': 'bg-gray-500', 'text': 'text-gray-700',
        'bg_light': 'bg-gray-50', 'border': 'border-gray-200'
    },
    'Otro': {
        'label': 'Otro',
        'bg': 'bg-slate-500', 'text': 'text-slate-700',
        'bg_light': 'bg-slate-50', 'border': 'border-slate-200'
    },
}


# ============================================================================
# HELPERS
# ============================================================================
def _get_nivel_permiso():
    """Retorna el nivel de permiso del usuario actual para el módulo Calendario"""
    if current_user.RoleId == 1:
        return 2
    modulo = EdugestModule.query.filter_by(ModuleName='Calendario').first()
    if modulo:
        perm = EdugestRolePermission.query.filter_by(
            RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
        ).first()
        if perm:
            return perm.PermissionLevel
    return 0


def _get_nivel_permiso_evaluaciones():
    """Retorna el nivel de permiso del usuario actual para el módulo Evaluaciones"""
    if current_user.RoleId == 1:
        return 2
    modulo = EdugestModule.query.filter_by(ModuleName='Evaluaciones').first()
    if modulo:
        perm = EdugestRolePermission.query.filter_by(
            RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
        ).first()
        if perm:
            return perm.PermissionLevel
    return 0


def _get_org_ids_for_user():
    """
    Retorna los OrganizationIds que el usuario actual debería poder ver.
    - Admin (RoleId=1): retorna None (ve todo)
    - Otros: retorna lista de IDs relevantes
    """
    org_ids = []

    if current_user.RoleId == 1:
        return None  # Admin ve todo

    if current_user.RoleId == 6:
        # Estudiante: su curso, grado y asignaturas
        matriculas = OrganizationPersonRole.query.filter_by(
            PersonId=current_user.PersonId, RoleId=6, ExitDate=None
        ).all()
        for mat in matriculas:
            org = Organization.query.get(mat.OrganizationId)
            if org and org.RefOrganizationTypeId == 21:
                org_ids.append(org.OrganizationId)
                rel = OrganizationRelationship.query.filter_by(
                    OrganizationId=org.OrganizationId
                ).first()
                if rel:
                    org_ids.append(rel.ParentOrganizationId)
                    asignaturas = Organization.query.join(
                        OrganizationRelationship,
                        Organization.OrganizationId == OrganizationRelationship.OrganizationId
                    ).filter(
                        OrganizationRelationship.ParentOrganizationId == rel.ParentOrganizationId,
                        Organization.RefOrganizationTypeId == 22
                    ).all()
                    for asig in asignaturas:
                        org_ids.append(asig.OrganizationId)

    elif current_user.RoleId == 5:
        # Apoderado: cursos de sus hijos
        relaciones = PersonRelationship.query.filter_by(
            RelatedPersonId=current_user.PersonId
        ).all()
        for rel_p in relaciones:
            rol_hijo = OrganizationPersonRole.query.filter_by(
                PersonId=rel_p.PersonId, RoleId=6, ExitDate=None
            ).first()
            if rol_hijo:
                org = Organization.query.get(rol_hijo.OrganizationId)
                if org and org.RefOrganizationTypeId == 21:
                    org_ids.append(org.OrganizationId)
                    rel_curso = OrganizationRelationship.query.filter_by(
                        OrganizationId=org.OrganizationId
                    ).first()
                    if rel_curso:
                        org_ids.append(rel_curso.ParentOrganizationId)
                        asignaturas = Organization.query.join(
                            OrganizationRelationship,
                            Organization.OrganizationId == OrganizationRelationship.OrganizationId
                        ).filter(
                            OrganizationRelationship.ParentOrganizationId == rel_curso.ParentOrganizationId,
                            Organization.RefOrganizationTypeId == 22
                        ).all()
                        for asig in asignaturas:
                            org_ids.append(asig.OrganizationId)

    else:
        # Profesor, Director, Inspector: organizaciones donde tiene rol activo
        # + organizaciones hermanas bajo el mismo padre (asignaturas, otros cursos)
        roles = OrganizationPersonRole.query.filter_by(
            PersonId=current_user.PersonId, ExitDate=None
        ).all()
        for rol in roles:
            org_ids.append(rol.OrganizationId)
            rel = OrganizationRelationship.query.filter_by(
                OrganizationId=rol.OrganizationId
            ).first()
            if rel:
                parent_id = rel.ParentOrganizationId
                org_ids.append(parent_id)

                # Buscar TODAS las organizaciones hermanas bajo el mismo padre
                # (incluye asignaturas tipo 22 y otros cursos tipo 21)
                hermanas = Organization.query.join(
                    OrganizationRelationship,
                    Organization.OrganizationId == OrganizationRelationship.OrganizationId
                ).filter(
                    OrganizationRelationship.ParentOrganizationId == parent_id
                ).all()
                for h in hermanas:
                    org_ids.append(h.OrganizationId)

    return list(set(org_ids)) if org_ids else []


# ============================================================================
# RUTA PRINCIPAL: Vista mensual del calendario
# ============================================================================
@calendario_bp.route('/')
@login_required
@permiso_requerido('Calendario', 1)
def index():
    nivel_permiso = _get_nivel_permiso()

    # Parsear mes/año desde query params
    hoy = date.today()
    year = request.args.get('year', hoy.year, type=int)
    month = request.args.get('month', hoy.month, type=int)

    # Validar mes
    if month < 1:
        month, year = 12, year - 1
    if month > 12:
        month, year = 1, year + 1

    # Primer y último día del mes
    first_day = date(year, month, 1)
    num_days = calendar.monthrange(year, month)[1]
    last_day = date(year, month, num_days)

    # Consultar eventos del mes
    query = EdugestCalendarEvent.query.filter(
        EdugestCalendarEvent.EventDate >= first_day,
        EdugestCalendarEvent.EventDate <= last_day
    )

    # Filtrar por visibilidad según rol
    org_ids = _get_org_ids_for_user()
    if org_ids is None:
        pass  # Admin: sin filtro, ve todo
    elif org_ids:
        query = query.filter(
            (EdugestCalendarEvent.TargetOrganizationId.is_(None)) |
            (EdugestCalendarEvent.TargetOrganizationId.in_(org_ids))
        )
    else:
        # Sin organizaciones: solo eventos globales
        query = query.filter(EdugestCalendarEvent.TargetOrganizationId.is_(None))

    events_raw = query.order_by(EdugestCalendarEvent.EventDate).all()

    # ── Filtrar evaluaciones no publicadas para usuarios sin permiso nivel 2 ──
    nivel_eval = _get_nivel_permiso_evaluaciones()

    if nivel_eval < 2:
        # Recopilar IDs de instrumentos vinculados a eventos de evaluación
        instrument_ids = [
            ev.InstrumentId for ev in events_raw
            if ev.InstrumentId and ev.EventType == 'Evaluacion'
        ]

        # Consulta batch: qué instrumentos están publicados (IsVisible=True)
        instrumentos_publicados = set()
        if instrument_ids:
            publicados = EdugestAssessmentInstrument.query.filter(
                EdugestAssessmentInstrument.InstrumentId.in_(instrument_ids),
                EdugestAssessmentInstrument.IsVisible == True
            ).all()
            instrumentos_publicados = {i.InstrumentId for i in publicados}

        # Filtrar: eventos de evaluación no publicadas se ocultan
        events = []
        for ev in events_raw:
            if ev.InstrumentId and ev.EventType == 'Evaluacion':
                if ev.InstrumentId not in instrumentos_publicados:
                    continue
            events.append(ev)
    else:
        events = events_raw

    # Agrupar eventos por día
    events_by_day = {}
    for event in events:
        d = event.EventDate.day
        if d not in events_by_day:
            events_by_day[d] = []
        events_by_day[d].append(event)

    # Grilla del calendario
    cal = calendar.monthcalendar(year, month)

    # Navegación
    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    month_name = MESES[month]

    # Datos para formulario de creación (solo nivel 2)
    grados = []
    asignaturas = []
    if nivel_permiso >= 2:
        grados = Organization.query.filter_by(
            RefOrganizationTypeId=46
        ).order_by(Organization.Name).all()
        asignaturas = Organization.query.filter_by(
            RefOrganizationTypeId=22
        ).order_by(Organization.Name).all()

    return render_template('calendario/index.html',
        year=year, month=month, month_name=month_name,
        cal=cal, events_by_day=events_by_day,
        event_types=EVENT_TYPES,
        nivel_permiso=nivel_permiso,
        hoy=hoy,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        grados=grados, asignaturas=asignaturas
    )


# ============================================================================
# RUTA: Crear evento
# ============================================================================
@calendario_bp.route('/evento', methods=['POST'])
@login_required
@permiso_requerido('Calendario', 2)
def crear_evento():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    event_date_str = request.form.get('event_date', '')
    event_type = request.form.get('event_type', 'Otro')
    target_org_id = request.form.get('target_organization_id', '')

    if not title or not event_date_str:
        flash('El título y la fecha son obligatorios.', 'error')
        return redirect(url_for('calendario.index'))

    try:
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de fecha inválido.', 'error')
        return redirect(url_for('calendario.index'))

    nuevo = EdugestCalendarEvent(
        Title=title,
        Description=description if description else None,
        EventDate=event_date,
        EventType=event_type if event_type in EVENT_TYPES else 'Otro',
        TargetOrganizationId=int(target_org_id) if target_org_id else None,
        CreatedBy=current_user.PersonId
    )
    db.session.add(nuevo)
    db.session.commit()

    flash('Evento creado correctamente.', 'success')
    return redirect(url_for('calendario.index', year=event_date.year, month=event_date.month))


# ============================================================================
# RUTA: Eliminar evento
# ============================================================================
@calendario_bp.route('/evento/<int:event_id>/eliminar', methods=['POST'])
@login_required
@permiso_requerido('Calendario', 2)
def eliminar_evento(event_id):
    evento = EdugestCalendarEvent.query.get_or_404(event_id)
    year, month = evento.EventDate.year, evento.EventDate.month

    db.session.delete(evento)
    db.session.commit()

    flash('Evento eliminado correctamente.', 'info')
    return redirect(url_for('calendario.index', year=year, month=month))