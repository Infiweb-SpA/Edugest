from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import re
from app.database import db
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationPersonRole
)
from app.models.edugest import EdugestModule

matricula_bp = Blueprint('matricula', __name__, url_prefix='/matricula')


# ============================================================================
# HELPERS
# ============================================================================
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

    # Obtener niveles disponibles
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

        # DEBUG: Imprimir datos recibidos
        print(f"DEBUG - Datos recibidos: curso_id={curso_id}, entry_date={entry_date}")
        print(f"DEBUG - Nombre: {first_name} {last_name}, RUT: {rut}")

                # Validación mínima
        if not all([first_name, last_name, rut, curso_id, entry_date]):
            flash("Los campos obligatorios son: nombres, apellido paterno, RUT, curso y fecha de matrícula.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))
        
        # Validar formato RUT normalizado
        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$', rut):
            flash(f"El RUT ingresado no tiene un formato válido. Se intentó normalizar a: {rut}", "warning")

        # Validar que el curso existe y es tipo 21
        curso = Organization.query.get(curso_id)
        if not curso:
            flash(f"El curso seleccionado (ID: {curso_id}) no existe.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))
        
        if curso.RefOrganizationTypeId != 21:
            flash(f"La organización seleccionada no es un curso (Tipo: {curso.RefOrganizationTypeId}).", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        try:
            # 1. Crear Persona
            # Convertir birthdate si existe
            birthdate_obj = datetime.strptime(birthdate, '%Y-%m-%d').date() if birthdate else None
            
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
            # Convertir string a objeto date para SQLite
            entry_date_obj = datetime.strptime(entry_date, '%Y-%m-%d').date() if entry_date else None
            
            nuevo_rol = OrganizationPersonRole(
                OrganizationId=int(curso_id),
                PersonId=nueva_persona.PersonId,
                RoleId=6,  # Estudiante
                EntryDate=entry_date_obj,
                ExitDate=None
            )
            db.session.add(nuevo_rol)
            print(f"DEBUG - Rol creado: OrgID={curso_id}, PersonID={nueva_persona.PersonId}, RoleID=6")

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

    # Enriquecer matrículas con jerarquía
    matriculas_data = []
    for rol in roles:
        jerarquia = obtener_jerarquia_curso(rol.OrganizationId)
        matriculas_data.append({
            'rol': rol,
            'jerarquia': jerarquia
        })

    return render_template('matricula/ver.html',
                           persona=persona,
                           ids_map=ids_map,
                           matriculas=matriculas_data)