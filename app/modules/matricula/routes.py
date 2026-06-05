from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import re
from app.database import db
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationPersonRole, PersonAddress, PersonTelephone,
    PersonRelationship, PersonDegreeOrCertificate, PersonEmailAddress
)
from app.models.edugest import (
    EdugestModule,
    EdugestStudentEnrollment, EdugestEmergencyContact,
    EdugestStudentHealth, EdugestStudentPIE,
    EdugestPersonRelationshipDetail
)

matricula_bp = Blueprint('matricula', __name__, url_prefix='/matricula')


# ============================================================================
# HELPERS
# ============================================================================
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
    Ahora incluye: parentesco, email, profesión, trabajo y dirección.
    """
    first_name = request.form.get(f'{prefix}_first_name')
    last_name  = request.form.get(f'{prefix}_last_name')
    second_last= request.form.get(f'{prefix}_second_last_name', '')
    rut_raw    = request.form.get(f'{prefix}_rut')
    telefono   = request.form.get(f'{prefix}_telefono')
    nivel      = request.form.get(f'{prefix}_nivel_educativo')
    
    # NUEVOS CAMPOS
    parentesco = request.form.get(f'{prefix}_parentesco')
    email      = request.form.get(f'{prefix}_email')
    profesion  = request.form.get(f'{prefix}_profesion')
    trabajo    = request.form.get(f'{prefix}_lugar_trabajo')
    direccion  = request.form.get(f'{prefix}_direccion')

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
    if email:
        db.session.add(PersonEmailAddress(
            PersonId=apoderado.PersonId,
            EmailAddress=email
        ))
    if direccion:
        db.session.add(PersonAddress(
            PersonId=apoderado.PersonId,
            StreetNumberAndName=direccion
        ))
    if nivel:
        db.session.add(PersonDegreeOrCertificate(
            PersonId=apoderado.PersonId,
            RefDegreeOrCertificateTypeId=int(nivel)
        ))

    rel = PersonRelationship(
        PersonId=estudiante_id,
        RelatedPersonId=apoderado.PersonId,
        RefPersonRelationshipId=ref_rel_id
    )
    db.session.add(rel)
    db.session.flush()  # Necesario para obtener el ID de la relación

    # Guardar detalles adicionales de la relación
    if parentesco or profesion or trabajo or direccion or email:
        db.session.add(EdugestPersonRelationshipDetail(
            PersonRelationshipId=rel.PersonRelationshipId,
            Parentesco=parentesco,
            ProfesionOcupacion=profesion,
            LugarTrabajo=trabajo,
            Direccion=direccion,
            CorreoElectronico=email
        ))

    return apoderado


def obtener_apoderados_estudiante(person_id):
    """Retorna lista ordenada de apoderados con datos enriquecidos."""
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
        email = PersonEmailAddress.query.filter_by(PersonId=apod.PersonId).first()
        direccion = PersonAddress.query.filter_by(PersonId=apod.PersonId).first()
        nivel = PersonDegreeOrCertificate.query.filter_by(PersonId=apod.PersonId).first()
        detalle = EdugestPersonRelationshipDetail.query.filter_by(
            PersonRelationshipId=rel.PersonRelationshipId
        ).first()

        resultado.append({
            'persona': apod,
            'rut': rut.Identifier if rut else None,
            'telefono': fono.TelephoneNumber if fono else None,
            'email': email.EmailAddress if email else None,
            'direccion': direccion.StreetNumberAndName if direccion else None,
            'nivel': nivel.RefDegreeOrCertificateTypeId if nivel else None,
            'detalle': detalle
        })
    return resultado


def normalizar_rut(rut):
    """Normaliza cualquier formato de RUT al estándar MINEDUC: xx.xxx.xxx-x"""
    if not rut:
        return None
    rut_limpio = re.sub(r'[^0-9kK]', '', rut)
    if len(rut_limpio) < 2:
        return rut
    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1].upper()
    cuerpo_formateado = ''
    while len(cuerpo) > 3:
        cuerpo_formateado = '.' + cuerpo[-3:] + cuerpo_formateado
        cuerpo = cuerpo[:-3]
    cuerpo_formateado = cuerpo + cuerpo_formateado
    return f"{cuerpo_formateado}-{dv}"


def verificar_modulo_habilitado():
    modulo = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
    if not modulo or not modulo.IsEnabled:
        flash("El módulo de Matrícula se encuentra deshabilitado.", "warning")
        return False
    return True


def obtener_jerarquia_curso(curso_id):
    resultado = {"nivel": "", "grado": "", "letra": ""}
    curso = Organization.query.get(curso_id)
    if not curso:
        return resultado
    resultado["letra"] = curso.ShortName or ""
    visitados = set()
    actual_id = curso.OrganizationId
    while actual_id and actual_id not in visitados:
        visitados.add(actual_id)
        rel = OrganizationRelationship.query.filter_by(OrganizationId=actual_id).first()
        if not rel:
            break
        padre = Organization.query.get(rel.ParentOrganizationId)
        if not padre:
            break
        if padre.RefOrganizationTypeId == 46:
            resultado["grado"] = padre.Name
        elif padre.RefOrganizationTypeId == 40:
            resultado["nivel"] = padre.Name
        actual_id = padre.OrganizationId
    return resultado


def _parse_date(campo):
    """Helper para parsear fechas de formulario de forma segura"""
    val = request.form.get(campo)
    if val:
        try:
            return datetime.strptime(val, '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


def _parse_int(campo):
    val = request.form.get(campo)
    return int(val) if val and val.isdigit() else None


def _parse_bool(campo):
    return request.form.get(campo) == '1'


# ============================================================================
# LISTADO DE ESTUDIANTES
# ============================================================================
@matricula_bp.route('/')
def listar_estudiantes():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))
    roles = OrganizationPersonRole.query.filter_by(RoleId=6).all()
    estudiantes_data = []
    for rol in roles:
        jerarquia = obtener_jerarquia_curso(rol.OrganizationId)
        estudiantes_data.append({'rol': rol, 'jerarquia': jerarquia})
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
        # ── Datos Personales Básicos ──
        first_name   = request.form.get('first_name')
        middle_name  = request.form.get('middle_name', '')
        last_name    = request.form.get('last_name')
        second_last  = request.form.get('second_last_name', '')
        ref_sex_id   = request.form.get('ref_sex_id')
        birthdate    = request.form.get('birthdate')

        # ── Identificadores ──
        rut_raw      = request.form.get('rut')
        rut          = normalizar_rut(rut_raw) if rut_raw else None
        ipe          = request.form.get('ipe', '')
        num_matricula= request.form.get('num_matricula', '')
        num_lista    = request.form.get('num_lista', '')

        # ── Matrícula ──
        curso_id     = request.form.get('curso_id')
        entry_date   = request.form.get('entry_date')
        residencia   = request.form.get('residencia')

        # ── Apoderado Titular ──
        ap_t_first   = request.form.get('ap_titular_first_name')
        ap_t_last    = request.form.get('ap_titular_last_name')
        ap_t_rut     = request.form.get('ap_titular_rut')

        # Validación mínima
        campos_obligatorios = [
            first_name, last_name, rut, curso_id, entry_date,
            residencia, ap_t_first, ap_t_last, ap_t_rut
        ]
        if not all(campos_obligatorios):
            flash("Complete todos los campos obligatorios.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$', rut):
            flash(f"El RUT del estudiante no tiene formato válido: {rut}", "warning")

        curso = Organization.query.get(curso_id)
        if not curso or curso.RefOrganizationTypeId != 21:
            flash("El curso seleccionado no es válido.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        try:
            birthdate_obj = _parse_date('birthdate')
            entry_date_obj = _parse_date('entry_date')

            # 1. Crear Persona
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

            # 2. Identificadores
            if rut:
                db.session.add(PersonIdentifier(PersonId=nueva_persona.PersonId, Identifier=rut, RefPersonIdentificationSystemId=51))
            if ipe:
                db.session.add(PersonIdentifier(PersonId=nueva_persona.PersonId, Identifier=ipe, RefPersonIdentificationSystemId=52))
            if num_matricula:
                db.session.add(PersonIdentifier(PersonId=nueva_persona.PersonId, Identifier=num_matricula, RefPersonIdentificationSystemId=55))
            if num_lista:
                db.session.add(PersonIdentifier(PersonId=nueva_persona.PersonId, Identifier=num_lista, RefPersonIdentificationSystemId=54))

            # 3. Rol en Curso
            db.session.add(OrganizationPersonRole(
                OrganizationId=int(curso_id),
                PersonId=nueva_persona.PersonId,
                RoleId=6,
                EntryDate=entry_date_obj,
                ExitDate=None
            ))

            # 4. Residencia
            if residencia:
                db.session.add(PersonAddress(PersonId=nueva_persona.PersonId, StreetNumberAndName=residencia))

            # 5. Apoderados
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_titular')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente1')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente2')

            # 6. DATOS ADICIONALES DE MATRÍCULA
            db.session.add(EdugestStudentEnrollment(
                PersonId=nueva_persona.PersonId,
                Nacionalidad=request.form.get('nacionalidad'),
                PaisOrigen=request.form.get('pais_origen'),
                ComunaResidencia=request.form.get('comuna_residencia'),
                RegionResidencia=request.form.get('region_residencia'),
                EmailEstudiante=request.form.get('email_estudiante'),
                TelefonoEstudiante=request.form.get('telefono_estudiante'),
                ColegioProcedencia=request.form.get('colegio_procedencia'),
                ComunaColegioAnterior=request.form.get('comuna_colegio_anterior'),
                RegionColegioAnterior=request.form.get('region_colegio_anterior'),
                UltimoCursoAprobado=request.form.get('ultimo_curso_aprobado'),
                AnioUltimoCursoAprobado=_parse_int('anio_ultimo_curso'),
                MotivoTraslado=request.form.get('motivo_traslado'),
                FechaIngresoEstablecimiento=_parse_date('fecha_ingreso_establecimiento'),
                NivelEducacionalMadre=_parse_int('nivel_madre'),
                NivelEducacionalPadre=_parse_int('nivel_padre'),
                NivelEducacionalApoderado=_parse_int('nivel_apoderado'),
                IngresoFamiliar=request.form.get('ingreso_familiar'),
                NumIntegrantesHogar=_parse_int('num_integrantes_hogar'),
                AlumnoPrioritario=_parse_bool('alumno_prioritario'),
                AlumnoPreferente=_parse_bool('alumno_preferente'),
                BeneficiarioSEP=_parse_bool('beneficiario_sep'),
                PertenecePuebloOriginario=_parse_bool('pertenece_pueblo_originario'),
                PuebloOriginario=request.form.get('pueblo_originario'),
                HablaLenguaIndigena=_parse_bool('habla_lengua_indigena'),
                LenguaIndigena=request.form.get('lengua_indigena'),
                NacionalidadExtranjera=request.form.get('nacionalidad_extranjera'),
                MedioTransporte=request.form.get('medio_transporte'),
                UtilizaTransporteEscolar=_parse_bool('utiliza_transporte_escolar'),
                NombreTransportista=request.form.get('nombre_transportista'),
                TelefonoTransportista=request.form.get('telefono_transportista'),
                TiempoEstimadoTraslado=request.form.get('tiempo_traslado'),
                AutorizaFotografias=_parse_bool('autoriza_fotografias'),
                AutorizaRedesSociales=_parse_bool('autoriza_redes_sociales'),
                AutorizaSalidasPedagogicas=_parse_bool('autoriza_salidas'),
                AutorizaTrasladoCentroAsistencial=_parse_bool('autoriza_traslado_medico'),
                AutorizaAtencionMedicaUrgencia=_parse_bool('autoriza_atencion_urgencia'),
                EntregaCertificadoNacimiento=_parse_bool('doc_cert_nacimiento'),
                EntregaCertificadoAnualEstudios=_parse_bool('doc_cert_estudios'),
                EntregaInformePersonalidad=_parse_bool('doc_informe_personalidad'),
                EntregaInformeNotas=_parse_bool('doc_informe_notas'),
                EntregaInformePIE=_parse_bool('doc_informe_pie'),
                EntregaFotocopiaRUNEstudiante=_parse_bool('doc_fotocopia_run_est'),
                EntregaFotocopiaRUNApoderado=_parse_bool('doc_fotocopia_run_apod'),
                EntregaComprobanteDomicilio=_parse_bool('doc_comprobante_domicilio'),
                EntregaFichaMedica=_parse_bool('doc_ficha_medica'),
                ObservacionesAcademicas=request.form.get('obs_academicas'),
                ObservacionesMedicas=request.form.get('obs_medicas'),
                ObservacionesFamiliares=request.form.get('obs_familiares'),
                ComentariosEstablecimiento=request.form.get('obs_establecimiento')
            ))

            # 7. CONTACTOS DE EMERGENCIA
            for i in [1, 2]:
                nombre = request.form.get(f'contacto_emergencia_{i}_nombre')
                if nombre:
                    db.session.add(EdugestEmergencyContact(
                        PersonId=nueva_persona.PersonId,
                        Orden=i,
                        NombreCompleto=nombre,
                        RUN=normalizar_rut(request.form.get(f'contacto_emergencia_{i}_run')),
                        Parentesco=request.form.get(f'contacto_emergencia_{i}_parentesco'),
                        TelefonoPrincipal=request.form.get(f'contacto_emergencia_{i}_telefono'),
                        TelefonoAlternativo=request.form.get(f'contacto_emergencia_{i}_telefono_alt')
                    ))

            # 8. INFORMACIÓN MÉDICA
            if any([
                request.form.get('grupo_sanguineo'), request.form.get('sistema_salud'),
                request.form.get('enfermedades_permanentes'), request.form.get('alergias'),
                request.form.get('medicamentos_permanentes'), request.form.get('restricciones_alimentarias'),
                request.form.get('necesidades_medicas'), request.form.get('obs_medicas_detalle'),
                request.form.get('centro_salud'), request.form.get('medico_tratante'), request.form.get('telefono_medico')
            ]):
                db.session.add(EdugestStudentHealth(
                    PersonId=nueva_persona.PersonId,
                    GrupoSanguineo=request.form.get('grupo_sanguineo'),
                    SistemaSalud=request.form.get('sistema_salud'),
                    EnfermedadesPermanentes=request.form.get('enfermedades_permanentes'),
                    Alergias=request.form.get('alergias'),
                    MedicamentosPermanentes=request.form.get('medicamentos_permanentes'),
                    RestriccionesAlimentarias=request.form.get('restricciones_alimentarias'),
                    NecesidadesMedicasEspeciales=request.form.get('necesidades_medicas'),
                    ObservacionesMedicasDetalle=request.form.get('obs_medicas_detalle'),
                    CentroSaludHabitual=request.form.get('centro_salud'),
                    MedicoTratante=request.form.get('medico_tratante'),
                    TelefonoMedicoTratante=request.form.get('telefono_medico')
                ))

            # 9. PIE
            if _parse_bool('pertenece_pie'):
                db.session.add(EdugestStudentPIE(
                    PersonId=nueva_persona.PersonId,
                    PertenecePIE=True,
                    DiagnosticoPIE=request.form.get('diagnostico_pie'),
                    FechaDiagnostico=_parse_date('fecha_diagnostico_pie'),
                    ProfesionalTratante=request.form.get('profesional_pie'),
                    ObservacionesPIE=request.form.get('observaciones_pie')
                ))

            db.session.commit()
            flash(f"Estudiante {first_name} {last_name} matriculado correctamente.", "success")
            return redirect(url_for('matricula.listar_estudiantes'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar: {str(e)}", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

    return render_template('matricula/formulario.html', niveles=niveles, estudiante=None)


# ============================================================================
# AJAX: GRADOS Y CURSOS
# ============================================================================
@matricula_bp.route('/ajax/grados/<int:nivel_id>')
def ajax_grados(nivel_id):
    if not verificar_modulo_habilitado():
        return jsonify([])
    relaciones = OrganizationRelationship.query.all()
    hijos = {}
    for r in relaciones:
        hijos.setdefault(r.ParentOrganizationId, []).append(r.OrganizationId)
    def get_all_descendants(org_id):
        result = []
        for hijo_id in hijos.get(org_id, []):
            result.append(hijo_id)
            result.extend(get_all_descendants(hijo_id))
        return result
    descendientes = get_all_descendants(nivel_id)
    grados = Organization.query.filter(
        Organization.OrganizationId.in_(descendientes),
        Organization.RefOrganizationTypeId == 46
    ).order_by(Organization.Name).all()
    return jsonify([{'id': g.OrganizationId, 'nombre': g.Name} for g in grados])


@matricula_bp.route('/ajax/cursos/<int:grado_id>')
def ajax_cursos(grado_id):
    if not verificar_modulo_habilitado():
        return jsonify([])
    relaciones = OrganizationRelationship.query.filter_by(ParentOrganizationId=grado_id).all()
    curso_ids = [r.OrganizationId for r in relaciones]
    cursos = Organization.query.filter(
        Organization.OrganizationId.in_(curso_ids),
        Organization.RefOrganizationTypeId == 21
    ).order_by(Organization.ShortName).all()
    return jsonify([{'id': c.OrganizationId, 'nombre': f"{c.Name} ({c.ShortName})", 'letra': c.ShortName} for c in cursos])


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
    residencia = PersonAddress.query.filter_by(PersonId=person_id).first()

    # Apoderados enriquecidos
    apoderados_data = obtener_apoderados_estudiante(person_id)
    ap_titular   = apoderados_data[0] if len(apoderados_data) > 0 else None
    ap_suplente1 = apoderados_data[1] if len(apoderados_data) > 1 else None
    ap_suplente2 = apoderados_data[2] if len(apoderados_data) > 2 else None

    # NUEVOS: Datos extendidos
    enrollment = EdugestStudentEnrollment.query.filter_by(PersonId=person_id).first()
    contactos_emergencia = EdugestEmergencyContact.query.filter_by(PersonId=person_id).order_by(EdugestEmergencyContact.Orden).all()
    health = EdugestStudentHealth.query.filter_by(PersonId=person_id).first()
    pie = EdugestStudentPIE.query.filter_by(PersonId=person_id).first()

    # Matrículas con jerarquía
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
                           niveles_map=NIVELES_EDUCATIVOS,
                           # NUEVOS
                           enrollment=enrollment,
                           contactos_emergencia=contactos_emergencia,
                           health=health,
                           pie=pie)