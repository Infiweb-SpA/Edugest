from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import db
from app.models.mineduc import Person, PersonIdentifier, Organization, OrganizationPersonRole
from app.models.edugest import EdugestModule

matricula_bp = Blueprint('matricula', __name__, url_prefix='/matricula')

# ───────────────────────────────────────────────
# LISTADO DE ESTUDIANTES
# ───────────────────────────────────────────────
@matricula_bp.route('/')
def listar_estudiantes():
    modulo = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
    if not modulo or not modulo.IsEnabled:
        flash("El módulo de Matrícula se encuentra deshabilitado.", "warning")
        return redirect(url_for('admin.dashboard'))

    # Traemos todos los estudiantes (RoleId = 6)
    roles = OrganizationPersonRole.query.filter_by(RoleId=6).all()
    return render_template('matricula/listar.html', estudiantes=roles)

# ───────────────────────────────────────────────
# FORMULARIO NUEVO ESTUDIANTE
# ───────────────────────────────────────────────
@matricula_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_estudiante():
    modulo = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
    if not modulo or not modulo.IsEnabled:
        flash("El módulo de Matrícula se encuentra deshabilitado.", "warning")
        return redirect(url_for('admin.dashboard'))

    # Cursos disponibles (RefOrganizationTypeId = 21 según el mapeo MINEDUC)
    cursos = Organization.query.filter_by(RefOrganizationTypeId=21).order_by(Organization.Name).all()

    if request.method == 'POST':
        # ── Datos Personales ──
        first_name   = request.form.get('first_name')
        middle_name  = request.form.get('middle_name', '')
        last_name    = request.form.get('last_name')
        second_last  = request.form.get('second_last_name', '')
        ref_sex_id   = request.form.get('ref_sex_id')
        birthdate    = request.form.get('birthdate')

        # ── Identificadores MINEDUC ──
        rut          = request.form.get('rut')
        ipe          = request.form.get('ipe', '')
        num_matricula= request.form.get('num_matricula', '')
        num_lista    = request.form.get('num_lista', '')

        # ── Matrícula ──
        curso_id     = request.form.get('curso_id')
        entry_date   = request.form.get('entry_date')

        # Validación mínima
        if not all([first_name, last_name, rut, curso_id, entry_date]):
            flash("Los campos obligatorios son: nombres, apellido paterno, RUT, curso y fecha de matrícula.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        try:
            # 1. Crear Persona
            nueva_persona = Person(
                FirstName=first_name,
                MiddleName=middle_name,
                LastName=last_name,
                SecondLastName=second_last,
                RefSexId=int(ref_sex_id) if ref_sex_id else None
            )
            db.session.add(nueva_persona)
            db.session.flush()  # Obtener PersonId

            # 2. Crear Identificadores (RUT=51, IPE=52, N°Matrícula=55, N°Lista=54)
            if rut:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId,
                    Identifier=rut,
                    RefPersonIdentificationSystemId=51
                ))
            if ipe:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId,
                    Identifier=ipe,
                    RefPersonIdentificationSystemId=52
                ))
            if num_matricula:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId,
                    Identifier=num_matricula,
                    RefPersonIdentificationSystemId=55
                ))
            if num_lista:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId,
                    Identifier=num_lista,
                    RefPersonIdentificationSystemId=54
                ))

            # 3. Crear Rol de Estudiante en el Curso
            nuevo_rol = OrganizationPersonRole(
                OrganizationId=int(curso_id),
                PersonId=nueva_persona.PersonId,
                RoleId=6,  # Estudiante
                EntryDate=entry_date,
                ExitDate=None
            )
            db.session.add(nuevo_rol)

            db.session.commit()
            flash(f"Estudiante {first_name} {last_name} matriculado correctamente.", "success")
            return redirect(url_for('matricula.listar_estudiantes'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar: {str(e)}", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

    return render_template('matricula/formulario.html', cursos=cursos, estudiante=None)

# ───────────────────────────────────────────────
# VER DETALLE DE UN ESTUDIANTE
# ───────────────────────────────────────────────
@matricula_bp.route('/<int:person_id>')
def ver_estudiante(person_id):
    modulo = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
    if not modulo or not modulo.IsEnabled:
        flash("El módulo de Matrícula se encuentra deshabilitado.", "warning")
        return redirect(url_for('admin.dashboard'))

    persona = Person.query.get_or_404(person_id)
    identificadores = PersonIdentifier.query.filter_by(PersonId=person_id).all()
    roles = OrganizationPersonRole.query.filter_by(PersonId=person_id, RoleId=6).all()

    # Diccionario rápido para mostrar en la vista
    ids_map = {i.RefPersonIdentificationSystemId: i.Identifier for i in identificadores}

    return render_template('matricula/ver.html',
                           persona=persona,
                           ids_map=ids_map,
                           matriculas=roles)