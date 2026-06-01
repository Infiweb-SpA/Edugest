from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import (
    db, Person, Organization, OrganizationPersonRole, 
    OrganizationCalendarSession, RoleAttendanceEvent, EdugestCurriculumPlan
)

libro_digital_bp = Blueprint('libro_digital', __name__, url_prefix='/libro-digital')

@libro_digital_bp.route('/')
def mis_asignaturas():
    asignaturas = Organization.query.filter_by(RefOrganizationTypeId=22).all()
    return render_template('libro_digital/asignaturas.html', asignaturas=asignaturas)

@libro_digital_bp.route('/asignatura/<int:org_id>/clase/nueva', methods=['GET', 'POST'])
def registrar_bloque(org_id):
    asignatura = Organization.query.get_or_404(org_id)
    unidades = EdugestCurriculumPlan.query.filter_by(OrganizationId=org_id).all()
    
    estudiantes_roles = OrganizationPersonRole.query.filter_by(
        OrganizationId=org_id, 
        RoleId=6
    ).all()

    if request.method == 'POST':
        contenido_leccionario = request.form.get('descripcion')
        plan_id = request.form.get('plan_id')
        
        # Guardar en base a los tipos String del archivo mineduc.py
        hoy_str = datetime.now().strftime('%Y-%m-%d')
        hora_str = datetime.now().strftime('%H:%M:%S')
        
        nueva_sesion = OrganizationCalendarSession(
            OrganizationId=org_id,
            BeginDate=hoy_str,
            EndDate=hoy_str,
            SessionStartTime=hora_str,
            SessionEndTime=hora_str,
            Description=contenido_leccionario,
            MarkingTermIndicator=True,
            SchedulingTermIndicator=False,
            PlanId=int(plan_id) if plan_id else None
        )
        db.session.add(nueva_sesion)
        db.session.flush()
        
        for r in estudiantes_roles:
            status_id = request.form.get(f'asistencia_{r.OrganizationPersonRoleId}')
            
            evento_asistencia = RoleAttendanceEvent(
                OrganizationPersonRoleId=r.OrganizationPersonRoleId,
                Date=datetime.now().date(),
                RefAttendanceEventTypeId=1, # 1 = Asistencia por bloque horario
                RefAttendanceStatusId=int(status_id) if status_id else 1,
                digitalRandomKey="FIRMA_DIGITAL_DOCENTE_TOKEN"
            )
            db.session.add(evento_asistencia)
            
        db.session.commit()
        flash('Clase, leccionario y asistencia registrados con éxito.', 'success')
        return redirect(url_for('libro_digital.mis_asignaturas'))

    return render_template(
        'libro_digital/registrar_clase.html', 
        asignatura=asignatura, 
        unidades=unidades, 
        estudiantes=estudiantes_roles
    )