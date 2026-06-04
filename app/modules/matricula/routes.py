from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import re
from app.database import db
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationPersonRole, PersonAddress, PersonTelephone,
    PersonRelationship, PersonDegreeOrCertificate
)
from app.models.edugest import EdugestModule

matricula_bp = Blueprint('matricula', __name__, url_prefix='/matricula')


# ============================================================================
# HELPERS
# ============================================================================
# Mapeo de niveles educativos para apoderados
NIVELES_EDUCATIVOS = {
    1: 'Educación Parvularia',
    2: 'Educación Básica',
    3: 'Educación Media',
    4: 'Educación Técnico-Profesional',
    5: 'Educación Universitaria',
    6: 'Postgrado'
}


def crear_apoderado_estudiante(estudiante_id, prefix, ref_rel_id=31):
    """
    Crea una persona apoderado, sus identificadores y la vincula con el estudiante.
    prefix: 'ap_titular', 'ap_suplente1', 'ap_suplente2'
    Retorna el objeto Person creado o None si no hay datos.
    """
    first_name = request.form.get(f'{prefix}_first_name')
    last_name  = request.form.get(f'{prefix}_last_name')
    second_last= request.form.get(f'{prefix}_second_last_name', '')
    rut_raw    = request.form.get(f'{prefix}_rut')
    telefono   = request.form.get(f'{prefix}_telefono')
    nivel      = request.form.get(f'{prefix}_nivel_educativo')

    if not first_name or not last_name:
        return None

    rut = normalizar_rut(rut_raw) if rut_raw else None

    apoderado = Person(
        FirstName=first_name,
        MiddleName='',
        LastName=last_name,
        SecondLastName=second_last
    )
    db.session.add(apoderado)
    db.session.flush()

    if rut:
        db.session.add(PersonIdentifier(
            PersonId=apoderado.PersonId,
            Identifier=rut,
            RefPersonIdentificationSystemId=51
        ))
    if telefono:
        db.session.add(PersonTelephone(
            PersonId=apoderado.PersonId,
            TelephoneNumber=telefono
        ))
    if nivel:
        db.session.add(PersonDegreeOrCertificate(
            PersonId=apoderado.PersonId,
            RefDegreeOrCertificateTypeId=int(nivel)
        ))

    db.session.add(PersonRelationship(
        PersonId=estudiante_id,
        RelatedPersonId=apoderado.PersonId,
        RefPersonRelationshipId=ref_rel_id
    ))

    return apoderado


def obtener_apoderados_estudiante(person_id):
    """Retorna lista ordenada de apoderados (titular + suplentes) con sus datos enriquecidos."""
    relaciones = PersonRelationship.query.filter_by(
        PersonId=person_id, RefPersonRelationshipId=31
    ).order_by(PersonRelationship.PersonRelationshipId).all()

    resultado = []
    for rel in relaciones:
        apod = Person.query.get(rel.RelatedPersonId)
        if not apod:
            continue
        rut = PersonIdentifier.query.filter_by(
            PersonId=apod.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        fono = PersonTelephone.query.filter_by(PersonId=apod.PersonId).first()
        nivel = PersonDegreeOrCertificate.query.filter_by(PersonId=apod.PersonId).first()

        resultado.append({
            'persona': apod,
            'rut': rut.Identifier if rut else None,
            'telefono': fono.TelephoneNumber if fono else None,
            'nivel': nivel.RefDegreeOrCertificateTypeId if nivel else None
        })
    return resultado

def normalizar_rut(rut):
    """
    Normaliza cualquier formato de RUT al estándar MINEDUC: xx.xxx.xxx-x
    Acepta: 12345678-9, 12.345.678-9, 123456789, 12.345.6789, etc.
    """
    if not rut:
        return None
    
    # Eliminar todos los caracteres que no sean dígitos o K/k
    rut_limpio = re.sub(r'[^0-9kK]', '', rut)
    
    # Separar cuerpo y dígito verificador
    if len(rut_limpio) < 2:
        return rut  # No se puede normalizar, devolver original
    
    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1].upper()
    
    # Formatear con puntos cada 3 dígitos desde la derecha
    cuerpo_formateado = ''
    while len(cuerpo) > 3:
        cuerpo_formateado = '.' + cuerpo[-3:] + cuerpo_formateado
        cuerpo = cuerpo[:-3]
    cuerpo_formateado = cuerpo + cuerpo_formateado
    
    return f"{cuerpo_formateado}-{dv}"

def verificar_modulo_habilitado():
    """Verifica que el módulo Matrícula esté habilitado"""
    modulo = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
    if not modulo or not modulo.IsEnabled:
        flash("El módulo de Matrícula se encuentra deshabilitado.", "warning")
        return False
    return True


def obtener_jerarquia_curso(curso_id):
    """
    Obtiene la jerarquía completa de un curso subiendo por OrganizationRelationship.
    Retorna dict con: nivel, grado, letra
    """
    resultado = {"nivel": "", "grado": "", "letra": ""}

    curso = Organization.query.get(curso_id)
    if not curso:
        return resultado

    resultado["letra"] = curso.ShortName or ""

    # Subir la jerarquía
    visitados = set()
    actual_id = curso.OrganizationId

    while actual_id and actual_id not in visitados:
        visitados.add(actual_id)
        rel = OrganizationRelationship.query.filter_by(
            OrganizationId=actual_id
        ).first()

        if not rel:
            break

        padre = Organization.query.get(rel.ParentOrganizationId)
        if not padre:
            break

        if padre.RefOrganizationTypeId == 46:  # Grado
            resultado["grado"] = padre.Name
        elif padre.RefOrganizationTypeId == 40:  # Nivel
            resultado["nivel"] = padre.Name
        elif padre.RefOrganizationTypeId == 45:  # Código Enseñanza
            pass

        actual_id = padre.OrganizationId

    return resultado


# ============================================================================
# LISTADO DE ESTUDIANTES
# ============================================================================
@matricula_bp.route('/')
def listar_estudiantes():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    roles = OrganizationPersonRole.query.filter_by(RoleId=6).all()

    # Enriquecer con jerarquía
    estudiantes_data = []
    for rol in roles:
        jerarquia = obtener_jerarquia_curso(rol.OrganizationId)
        estudiantes_data.append({
            'rol': rol,
            'jerarquia': jerarquia
        })

    return render_template('matricula/listar.html', estudiantes=estudiantes_data)


# ============================================================================
# FORMULARIO NUEVO ESTUDIANTE
# ============================================================================
@matricula_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_estudiante():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    niveles = Organization.query.filter_by(RefOrganizationTypeId=40).order_by(Organization.Name).all()

    if request.method == 'POST':
        # ── Datos Personales ──
        first_name   = request.form.get('first_name')
        middle_name  = request.form.get('middle_name', '')
        last_name    = request.form.get('last_name')
        second_last  = request.form.get('second_last_name', '')
        ref_sex_id   = request.form.get('ref_sex_id')
        birthdate    = request.form.get('birthdate')

        # ── Identificadores MINEDUC ──
        rut_raw      = request.form.get('rut')
        rut          = normalizar_rut(rut_raw) if rut_raw else None
        ipe          = request.form.get('ipe', '')
        num_matricula= request.form.get('num_matricula', '')
        num_lista    = request.form.get('num_lista', '')

        # ── Matrícula ──
        curso_id     = request.form.get('curso_id')
        entry_date   = request.form.get('entry_date')

        # ── Residencia ──
        residencia   = request.form.get('residencia')

        # ── Apoderado Titular (obligatorio) ──
        ap_t_first   = request.form.get('ap_titular_first_name')
        ap_t_last    = request.form.get('ap_titular_last_name')
        ap_t_rut     = request.form.get('ap_titular_rut')
        ap_t_fono    = request.form.get('ap_titular_telefono')
        ap_t_nivel   = request.form.get('ap_titular_nivel_educativo')

        print(f"DEBUG - Datos recibidos: curso_id={curso_id}, entry_date={entry_date}")
        print(f"DEBUG - Nombre: {first_name} {last_name}, RUT: {rut}")

        # Validación mínima
        campos_obligatorios = [
            first_name, last_name, rut, curso_id, entry_date,
            residencia, ap_t_first, ap_t_last, ap_t_rut, ap_t_fono, ap_t_nivel
        ]
        if not all(campos_obligatorios):
            flash("Complete todos los campos obligatorios: datos del estudiante, residencia, curso, fecha de matrícula y apoderado titular.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$', rut):
            flash(f"El RUT del estudiante no tiene formato válido. Se intentó normalizar a: {rut}", "warning")

        # Validar curso
        curso = Organization.query.get(curso_id)
        if not curso:
            flash(f"El curso seleccionado (ID: {curso_id}) no existe.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))
        if curso.RefOrganizationTypeId != 21:
            flash(f"La organización seleccionada no es un curso (Tipo: {curso.RefOrganizationTypeId}).", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        try:
            birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d').date() if birthdate else None

            # 1. Crear Persona (estudiante)
            nueva_persona = Person(
                FirstName=first_name,
                MiddleName=middle_name,
                LastName=last_name,
                SecondLastName=second_last,
                RefSexId=int(ref_sex_id) if ref_sex_id else None,
                Birthdate=birthdate_obj
            )
            db.session.add(nueva_persona)
            db.session.flush()
            print(f"DEBUG - Persona creada: ID={nueva_persona.PersonId}")

            # 2. Identificadores del estudiante
            if rut:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId, Identifier=rut,
                    RefPersonIdentificationSystemId=51
                ))
            if ipe:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId, Identifier=ipe,
                    RefPersonIdentificationSystemId=52
                ))
            if num_matricula:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId, Identifier=num_matricula,
                    RefPersonIdentificationSystemId=55
                ))
            if num_lista:
                db.session.add(PersonIdentifier(
                    PersonId=nueva_persona.PersonId, Identifier=num_lista,
                    RefPersonIdentificationSystemId=54
                ))

            # 3. Rol de Estudiante en el Curso
            entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d').date() if entry_date else None
            nuevo_rol = OrganizationPersonRole(
                OrganizationId=int(curso_id),
                PersonId=nueva_persona.PersonId,
                RoleId=6,
                EntryDate=entry_date_obj,
                ExitDate=None
            )
            db.session.add(nuevo_rol)
            print(f"DEBUG - Rol creado: OrgID={curso_id}, PersonID={nueva_persona.PersonId}")

            # 4. Residencia del estudiante
            if residencia:
                db.session.add(PersonAddress(
                    PersonId=nueva_persona.PersonId,
                    StreetNumberAndName=residencia
                ))

            # 5. Apoderados (titular obligatorio, suplentes opcionales)
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_titular')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente1')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente2')

            db.session.commit()
            print(f"DEBUG - Commit exitoso")
            flash(f"Estudiante {first_name} {last_name} matriculado correctamente.", "success")
            return redirect(url_for('matricula.listar_estudiantes'))

        except Exception as e:
            db.session.rollback()
            print(f"DEBUG - Error: {str(e)}")
            flash(f"Error al guardar: {str(e)}", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

    return render_template('matricula/formulario.html', niveles=niveles, estudiante=None)


# ============================================================================
# AJAX: OBTENER GRADOS POR NIVEL
# ============================================================================
@matricula_bp.route('/ajax/grados/<int:nivel_id>')
def ajax_grados(nivel_id):
    """Retorna JSON con los grados de un nivel específico"""
    if not verificar_modulo_habilitado():
        return jsonify([])

    # Construir mapa de relaciones padre→hijos
    relaciones = OrganizationRelationship.query.all()
    
    hijos = {}
    for r in relaciones:
        if r.ParentOrganizationId not in hijos:
            hijos[r.ParentOrganizationId] = []
        hijos[r.ParentOrganizationId].append(r.OrganizationId)
    
    # Encontrar TODOS los descendientes del nivel (recursivo)
    def get_all_descendants(org_id):
        result = []
        if org_id in hijos:
            for hijo_id in hijos[org_id]:
                result.append(hijo_id)
                result.extend(get_all_descendants(hijo_id))
        return result
    
    descendientes = get_all_descendants(nivel_id)
    
    # Filtrar solo los de tipo Grado (46)
    grados = Organization.query.filter(
        Organization.OrganizationId.in_(descendientes),
        Organization.RefOrganizationTypeId == 46
    ).order_by(Organization.Name).all()
    
    return jsonify([{
        'id': g.OrganizationId,
        'nombre': g.Name
    } for g in grados])


# ============================================================================
# AJAX: OBTENER LETRAS (CURSOS) POR GRADO
# ============================================================================
@matricula_bp.route('/ajax/cursos/<int:grado_id>')
def ajax_cursos(grado_id):
    """Retorna JSON con los cursos (letras) de un grado específico"""
    if not verificar_modulo_habilitado():
        return jsonify([])

    # Buscar cursos (tipo 21) que tengan como padre al grado
    relaciones = OrganizationRelationship.query.filter_by(ParentOrganizationId=grado_id).all()
    curso_ids = [r.OrganizationId for r in relaciones]

    cursos = Organization.query.filter(
        Organization.OrganizationId.in_(curso_ids),
        Organization.RefOrganizationTypeId == 21
    ).order_by(Organization.ShortName).all()

    return jsonify([{
        'id': c.OrganizationId,
        'nombre': f"{c.Name} ({c.ShortName})",
        'letra': c.ShortName
    } for c in cursos])


# ============================================================================
# VER DETALLE DE UN ESTUDIANTE
# ============================================================================
@matricula_bp.route('/<int:person_id>')
def ver_estudiante(person_id):
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    persona = Person.query.get_or_404(person_id)
    identificadores = PersonIdentifier.query.filter_by(PersonId=person_id).all()
    roles = OrganizationPersonRole.query.filter_by(PersonId=person_id, RoleId=6).all()

    ids_map = {i.RefPersonIdentificationSystemId: i.Identifier for i in identificadores}

    # Residencia
    residencia = PersonAddress.query.filter_by(PersonId=person_id).first()

    # Apoderados (por orden de creación: 0=titular, 1=suplente1, 2=suplente2)
    apoderados_data = obtener_apoderados_estudiante(person_id)
    ap_titular   = apoderados_data[0] if len(apoderados_data) > 0 else None
    ap_suplente1 = apoderados_data[1] if len(apoderados_data) > 1 else None
    ap_suplente2 = apoderados_data[2] if len(apoderados_data) > 2 else None

    # Enriquecer matrículas con jerarquía
    matriculas_data = []
    for rol in roles:
        jerarquia = obtener_jerarquia_curso(rol.OrganizationId)
        matriculas_data.append({'rol': rol, 'jerarquia': jerarquia})

    return render_template('matricula/ver.html',
                           persona=persona,
                           ids_map=ids_map,
                           matriculas=matriculas_data,
                           residencia=residencia,
                           ap_titular=ap_titular,
                           ap_suplente1=ap_suplente1,
                           ap_suplente2=ap_suplente2,
                           niveles_map=NIVELES_EDUCATIVOS)