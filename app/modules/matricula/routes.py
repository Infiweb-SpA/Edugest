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
    6: 'Postgrado',
    7: 'Educación Media Científico-Humanista',
    8: 'Educación Media Técnico-Profesional (TP)',
    9: 'Educación Superior'
}


def crear_apoderado_estudiante(estudiante_id, prefix, ref_rel_id=31):
    """Crea un apoderado y lo vincula al estudiante."""
    first_name = request.form.get(f'{prefix}_first_name')
    last_name  = request.form.get(f'{prefix}_last_name')
    second_last= request.form.get(f'{prefix}_second_last_name', '')
    rut_raw    = request.form.get(f'{prefix}_rut')
    telefono   = request.form.get(f'{prefix}_telefono')
    nivel      = request.form.get(f'{prefix}_nivel_educativo')
    
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
    db.session.flush()

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
    """Retorna lista de apoderados con datos enriquecidos."""
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
    """Normaliza RUT a formato xx.xxx.xxx-x."""
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


def _serialize_estudiante(person_id):
    """Serializa todos los datos de un estudiante para precarga vía AJAX."""
    persona = Person.query.get(person_id)
    if not persona:
        return None
    
    ids = PersonIdentifier.query.filter_by(PersonId=person_id).all()
    ids_map = {i.RefPersonIdentificationSystemId: i.Identifier for i in ids}
    
    residencia = PersonAddress.query.filter_by(PersonId=person_id).first()
    apoderados = obtener_apoderados_estudiante(person_id)
    ap_titular = apoderados[0] if len(apoderados) > 0 else None
    ap_suplente1 = apoderados[1] if len(apoderados) > 1 else None
    ap_suplente2 = apoderados[2] if len(apoderados) > 2 else None
    
    enrollment = EdugestStudentEnrollment.query.filter_by(PersonId=person_id).first()
    health = EdugestStudentHealth.query.filter_by(PersonId=person_id).first()
    pie = EdugestStudentPIE.query.filter_by(PersonId=person_id).first()
    contactos = EdugestEmergencyContact.query.filter_by(PersonId=person_id).order_by(EdugestEmergencyContact.Orden).all()
    
    def ap_json(ap):
        if not ap:
            return None
        return {
            'first_name': ap['persona'].FirstName,
            'last_name': ap['persona'].LastName,
            'second_last_name': ap['persona'].SecondLastName,
            'rut': ap['rut'],
            'telefono': ap['telefono'],
            'email': ap['email'],
            'direccion': ap['direccion'],
            'nivel': ap['nivel'],
            'parentesco': ap['detalle'].Parentesco if ap['detalle'] else None,
            'profesion': ap['detalle'].ProfesionOcupacion if ap['detalle'] else None,
            'lugar_trabajo': ap['detalle'].LugarTrabajo if ap['detalle'] else None,
        }
    
    def contacto_json(c):
        return {
            'first_name': c.FirstName,
            'last_name': c.LastName,
            'second_last_name': c.SecondLastName,
            'nombre_completo': c.NombreCompleto,
            'run': c.RUN,
            'parentesco': c.Parentesco,
            'telefono': c.TelefonoPrincipal,
            'telefono_alt': c.TelefonoAlternativo,
            'email': c.Email,
            'profesion': c.ProfesionOcupacion,
            'nivel_educativo': c.NivelEducacional,
        }
    
    return {
        'persona': {
            'person_id': persona.PersonId,
            'first_name': persona.FirstName,
            'middle_name': persona.MiddleName,
            'last_name': persona.LastName,
            'second_last_name': persona.SecondLastName,
            'ref_sex_id': persona.RefSexId,
            'birthdate': persona.Birthdate.isoformat() if persona.Birthdate else None,
        },
        'identificadores': ids_map,
        'residencia': residencia.StreetNumberAndName if residencia else None,
        'ap_titular': ap_json(ap_titular),
        'ap_suplente1': ap_json(ap_suplente1),
        'ap_suplente2': ap_json(ap_suplente2),
        'enrollment': {
            'nacionalidad': enrollment.Nacionalidad if enrollment else None,
            'pais_origen': enrollment.PaisOrigen if enrollment else None,
            'comuna_residencia': enrollment.ComunaResidencia if enrollment else None,
            'region_residencia': enrollment.RegionResidencia if enrollment else None,
            'email_estudiante': enrollment.EmailEstudiante if enrollment else None,
            'telefono_estudiante': enrollment.TelefonoEstudiante if enrollment else None,
            'colegio_procedencia': enrollment.ColegioProcedencia if enrollment else None,
            'comuna_colegio_anterior': enrollment.ComunaColegioAnterior if enrollment else None,
            'region_colegio_anterior': enrollment.RegionColegioAnterior if enrollment else None,
            'ultimo_curso_aprobado': enrollment.UltimoCursoAprobado if enrollment else None,
            'anio_ultimo_curso': enrollment.AnioUltimoCursoAprobado if enrollment else None,
            'motivo_traslado': enrollment.MotivoTraslado if enrollment else None,
            'fecha_ingreso_establecimiento': enrollment.FechaIngresoEstablecimiento.isoformat() if enrollment and enrollment.FechaIngresoEstablecimiento else None,
            'nivel_madre': enrollment.NivelEducacionalMadre if enrollment else None,
            'nivel_padre': enrollment.NivelEducacionalPadre if enrollment else None,
            'nivel_apoderado': enrollment.NivelEducacionalApoderado if enrollment else None,
            'ingreso_familiar': enrollment.IngresoFamiliar if enrollment else None,
            'num_integrantes_hogar': enrollment.NumIntegrantesHogar if enrollment else None,
            'alumno_prioritario': enrollment.AlumnoPrioritario if enrollment else False,
            'alumno_preferente': enrollment.AlumnoPreferente if enrollment else False,
            'beneficiario_sep': enrollment.BeneficiarioSEP if enrollment else False,
            'pertenece_pueblo_originario': enrollment.PertenecePuebloOriginario if enrollment else False,
            'pueblo_originario': enrollment.PuebloOriginario if enrollment else None,
            'habla_lengua_indigena': enrollment.HablaLenguaIndigena if enrollment else False,
            'lengua_indigena': enrollment.LenguaIndigena if enrollment else None,
            'nacionalidad_extranjera': enrollment.NacionalidadExtranjera if enrollment else None,
            'medio_transporte': enrollment.MedioTransporte if enrollment else None,
            'utiliza_transporte_escolar': enrollment.UtilizaTransporteEscolar if enrollment else False,
            'nombre_transportista': enrollment.NombreTransportista if enrollment else None,
            'telefono_transportista': enrollment.TelefonoTransportista if enrollment else None,
            'tiempo_traslado': enrollment.TiempoEstimadoTraslado if enrollment else None,
            'autoriza_fotografias': enrollment.AutorizaFotografias if enrollment else False,
            'autoriza_redes_sociales': enrollment.AutorizaRedesSociales if enrollment else False,
            'autoriza_salidas': enrollment.AutorizaSalidasPedagogicas if enrollment else False,
            'autoriza_traslado_medico': enrollment.AutorizaTrasladoCentroAsistencial if enrollment else False,
            'autoriza_atencion_urgencia': enrollment.AutorizaAtencionMedicaUrgencia if enrollment else False,
            'doc_cert_nacimiento': enrollment.EntregaCertificadoNacimiento if enrollment else False,
            'doc_cert_estudios': enrollment.EntregaCertificadoAnualEstudios if enrollment else False,
            'doc_informe_personalidad': enrollment.EntregaInformePersonalidad if enrollment else False,
            'doc_informe_notas': enrollment.EntregaInformeNotas if enrollment else False,
            'doc_informe_pie': enrollment.EntregaInformePIE if enrollment else False,
            'doc_fotocopia_run_est': enrollment.EntregaFotocopiaRUNEstudiante if enrollment else False,
            'doc_fotocopia_run_apod': enrollment.EntregaFotocopiaRUNApoderado if enrollment else False,
            'doc_comprobante_domicilio': enrollment.EntregaComprobanteDomicilio if enrollment else False,
            'doc_ficha_medica': enrollment.EntregaFichaMedica if enrollment else False,
            'obs_academicas': enrollment.ObservacionesAcademicas if enrollment else None,
            'obs_medicas': enrollment.ObservacionesMedicas if enrollment else None,
            'obs_familiares': enrollment.ObservacionesFamiliares if enrollment else None,
            'obs_establecimiento': enrollment.ComentariosEstablecimiento if enrollment else None,
            'es_nuevo': enrollment.EsNuevoEnEstablecimiento if enrollment else True,
        },
        'contactos_emergencia': [contacto_json(c) for c in contactos],
        'health': {
            'grupo_sanguineo': health.GrupoSanguineo if health else None,
            'sistema_salud': health.SistemaSalud if health else None,
            'enfermedades_permanentes': health.EnfermedadesPermanentes if health else None,
            'alergias': health.Alergias if health else None,
            'medicamentos_permanentes': health.MedicamentosPermanentes if health else None,
            'restricciones_alimentarias': health.RestriccionesAlimentarias if health else None,
            'necesidades_medicas': health.NecesidadesMedicasEspeciales if health else None,
            'obs_medicas_detalle': health.ObservacionesMedicasDetalle if health else None,
            'centro_salud': health.CentroSaludHabitual if health else None,
            'medico_tratante': health.MedicoTratante if health else None,
            'telefono_medico': health.TelefonoMedicoTratante if health else None,
        } if health else None,
        'pie': {
            'pertenece_pie': pie.PertenecePIE if pie else False,
            'diagnostico_pie': pie.DiagnosticoPIE if pie else None,
            'fecha_diagnostico_pie': pie.FechaDiagnostico.isoformat() if pie and pie.FechaDiagnostico else None,
            'profesional_pie': pie.ProfesionalTratante if pie else None,
            'observaciones_pie': pie.ObservacionesPIE if pie else None,
        } if pie else None,
    }


# ============================================================================
# LISTADO DE ESTUDIANTES (agrupado por RUT para evitar duplicados de persona)
# ============================================================================
@matricula_bp.route('/')
def listar_estudiantes():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    # Obtener TODOS los roles activos con sus identificadores RUT
    roles = OrganizationPersonRole.query.filter_by(RoleId=6, ExitDate=None).all()
    
    # Agrupar por RUT (normalizado) y quedarse con el rol de EntryDate más reciente
    mejores_por_rut = {}
    for rol in roles:
        # Obtener el RUT del estudiante
        rut_id = PersonIdentifier.query.filter_by(
            PersonId=rol.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        rut = rut_id.Identifier if rut_id else None
        if not rut:
            # Si no tiene RUT, usar PersonId como fallback (pero idealmente todos tienen RUT)
            rut = f"ID_{rol.PersonId}"
        
        if rut not in mejores_por_rut:
            mejores_por_rut[rut] = rol
        else:
            if rol.EntryDate > mejores_por_rut[rut].EntryDate:
                mejores_por_rut[rut] = rol
    
    estudiantes_data = []
    for rol in mejores_por_rut.values():
        jerarquia = obtener_jerarquia_curso(rol.OrganizationId)
        estudiantes_data.append({'rol': rol, 'jerarquia': jerarquia})
    
    # Opcional: detectar si hay personas duplicadas (mismo RUT pero diferente PersonId)
    # Esto se puede loguear para depuración
    return render_template('matricula/listar.html', estudiantes=estudiantes_data)


# ============================================================================
# FORMULARIO NUEVO / EDICIÓN
# ============================================================================
@matricula_bp.route('/nuevo', methods=['GET', 'POST'])
def nuevo_estudiante():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    niveles = Organization.query.filter_by(RefOrganizationTypeId=40).order_by(Organization.Name).all()

    if request.method == 'POST':
        first_name   = request.form.get('first_name')
        middle_name  = request.form.get('middle_name', '')
        last_name    = request.form.get('last_name')
        second_last  = request.form.get('second_last_name', '')
        ref_sex_id   = request.form.get('ref_sex_id')
        birthdate    = request.form.get('birthdate')

        rut_raw      = request.form.get('rut')
        rut          = normalizar_rut(rut_raw) if rut_raw else None
        ipe          = request.form.get('ipe', '')
        num_matricula= request.form.get('num_matricula', '')
        num_lista    = request.form.get('num_lista', '')

        curso_id     = request.form.get('curso_id')
        entry_date   = request.form.get('entry_date')
        residencia   = request.form.get('residencia')

        ap_t_first   = request.form.get('ap_titular_first_name')
        ap_t_last    = request.form.get('ap_titular_last_name')
        ap_t_rut     = request.form.get('ap_titular_rut')

        # Validación mínima
        if not all([first_name, last_name, rut, curso_id, entry_date, residencia, ap_t_first, ap_t_last, ap_t_rut]):
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
            if not entry_date_obj:
                flash("La fecha de matrícula es obligatoria y debe ser válida.", "danger")
                return redirect(url_for('matricula.nuevo_estudiante'))

            # Verificar si ya existe una persona con este RUT (para evitar duplicados)
            persona_existente = None
            if rut:
                persona_existente = Person.query.join(PersonIdentifier).filter(
                    PersonIdentifier.Identifier == rut,
                    PersonIdentifier.RefPersonIdentificationSystemId == 51
                ).first()
            
            # Si se envió person_id_precargado, usamos ese (viene del buscador)
            person_id_precargado = request.form.get('person_id_precargado')
            if person_id_precargado and person_id_precargado.isdigit():
                # Forzar a usar ese ID (ya sea que coincida con el RUT o no)
                persona = Person.query.get(int(person_id_precargado))
                if not persona:
                    flash("El estudiante seleccionado no existe.", "danger")
                    return redirect(url_for('matricula.nuevo_estudiante'))
                # Si el RUT del formulario no coincide con el de la persona, actualizamos
                if rut:
                    existing_rut = PersonIdentifier.query.filter_by(
                        PersonId=persona.PersonId, RefPersonIdentificationSystemId=51
                    ).first()
                    if existing_rut and existing_rut.Identifier != rut:
                        # Podría ser un error, pero permitimos actualizar
                        existing_rut.Identifier = rut
                    elif not existing_rut:
                        db.session.add(PersonIdentifier(
                            PersonId=persona.PersonId, Identifier=rut, RefPersonIdentificationSystemId=51
                        ))
                nueva_persona = persona
                es_nuevo = False
            elif persona_existente:
                # Caso: no se usó el buscador, pero el RUT ya existe -> re-matrícula
                nueva_persona = persona_existente
                es_nuevo = False
                flash("Se ha detectado un estudiante existente con el mismo RUT. Se procederá a re-matricular.", "info")
            else:
                # Estudiante completamente nuevo
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
                es_nuevo = True

            # Actualizar datos personales (siempre)
            nueva_persona.FirstName = first_name
            nueva_persona.MiddleName = middle_name
            nueva_persona.LastName = last_name
            nueva_persona.SecondLastName = second_last
            nueva_persona.RefSexId = int(ref_sex_id) if ref_sex_id else None
            nueva_persona.Birthdate = birthdate_obj

            # Cerrar TODOS los roles activos anteriores (si no es nuevo)
            if not es_nuevo:
                roles_anteriores = OrganizationPersonRole.query.filter_by(
                    PersonId=nueva_persona.PersonId, RoleId=6, ExitDate=None
                ).all()
                for rol_anterior in roles_anteriores:
                    rol_anterior.ExitDate = entry_date_obj

            # Identificadores (UPSERT)
            def upsert_identifier(sys_id, val_identificador):
                if val_identificador:
                    ident = PersonIdentifier.query.filter_by(
                        PersonId=nueva_persona.PersonId, RefPersonIdentificationSystemId=sys_id
                    ).first()
                    if ident:
                        ident.Identifier = val_identificador
                    else:
                        db.session.add(PersonIdentifier(
                            PersonId=nueva_persona.PersonId, Identifier=val_identificador, RefPersonIdentificationSystemId=sys_id
                        ))

            upsert_identifier(51, rut)
            upsert_identifier(52, ipe)
            upsert_identifier(55, num_matricula)
            upsert_identifier(54, num_lista)

            # Nuevo rol en el curso actual
            db.session.add(OrganizationPersonRole(
                OrganizationId=int(curso_id),
                PersonId=nueva_persona.PersonId,
                RoleId=6,
                EntryDate=entry_date_obj,
                ExitDate=None
            ))

            # Residencia
            if residencia:
                addr = PersonAddress.query.filter_by(PersonId=nueva_persona.PersonId).first()
                if addr:
                    addr.StreetNumberAndName = residencia
                else:
                    db.session.add(PersonAddress(PersonId=nueva_persona.PersonId, StreetNumberAndName=residencia))

            # Apoderados (solo si no existen ya? Por simplicidad se crean nuevos cada vez.
            # Para evitar duplicados, se podría buscar primero. Pero por ahora se mantiene.
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_titular')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente1')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente2')

            # Datos adicionales de matrícula
            enrollment = EdugestStudentEnrollment.query.filter_by(PersonId=nueva_persona.PersonId).first()
            if not enrollment:
                enrollment = EdugestStudentEnrollment(PersonId=nueva_persona.PersonId)
                db.session.add(enrollment)
            
            enrollment.Nacionalidad = request.form.get('nacionalidad')
            enrollment.PaisOrigen = request.form.get('pais_origen')
            enrollment.ComunaResidencia = request.form.get('comuna_residencia')
            enrollment.RegionResidencia = request.form.get('region_residencia')
            enrollment.EmailEstudiante = request.form.get('email_estudiante')
            enrollment.TelefonoEstudiante = request.form.get('telefono_estudiante')
            enrollment.ColegioProcedencia = request.form.get('colegio_procedencia')
            enrollment.ComunaColegioAnterior = request.form.get('comuna_colegio_anterior')
            enrollment.RegionColegioAnterior = request.form.get('region_colegio_anterior')
            enrollment.UltimoCursoAprobado = request.form.get('ultimo_curso_aprobado')
            enrollment.AnioUltimoCursoAprobado = _parse_int('anio_ultimo_curso')
            enrollment.MotivoTraslado = request.form.get('motivo_traslado')
            enrollment.FechaIngresoEstablecimiento = _parse_date('fecha_ingreso_establecimiento')
            enrollment.EsNuevoEnEstablecimiento = _parse_bool('es_nuevo')
            enrollment.NivelEducacionalMadre = _parse_int('nivel_madre')
            enrollment.NivelEducacionalPadre = _parse_int('nivel_padre')
            enrollment.NivelEducacionalApoderado = _parse_int('nivel_apoderado')
            enrollment.IngresoFamiliar = request.form.get('ingreso_familiar')
            enrollment.NumIntegrantesHogar = _parse_int('num_integrantes_hogar')
            enrollment.AlumnoPrioritario = _parse_bool('alumno_prioritario')
            enrollment.AlumnoPreferente = _parse_bool('alumno_preferente')
            enrollment.BeneficiarioSEP = _parse_bool('beneficiario_sep')
            enrollment.PertenecePuebloOriginario = _parse_bool('pertenece_pueblo_originario')
            enrollment.PuebloOriginario = request.form.get('pueblo_originario')
            enrollment.HablaLenguaIndigena = _parse_bool('habla_lengua_indigena')
            enrollment.LenguaIndigena = request.form.get('lengua_indigena')
            enrollment.NacionalidadExtranjera = request.form.get('nacionalidad_extranjera')
            enrollment.MedioTransporte = request.form.get('medio_transporte')
            enrollment.UtilizaTransporteEscolar = _parse_bool('utiliza_transporte_escolar')
            enrollment.NombreTransportista = request.form.get('nombre_transportista')
            enrollment.TelefonoTransportista = request.form.get('telefono_transportista')
            enrollment.TiempoEstimadoTraslado = request.form.get('tiempo_traslado')
            enrollment.AutorizaFotografias = _parse_bool('autoriza_fotografias')
            enrollment.AutorizaRedesSociales = _parse_bool('autoriza_redes_sociales')
            enrollment.AutorizaSalidasPedagogicas = _parse_bool('autoriza_salidas')
            enrollment.AutorizaTrasladoCentroAsistencial = _parse_bool('autoriza_traslado_medico')
            enrollment.AutorizaAtencionMedicaUrgencia = _parse_bool('autoriza_atencion_urgencia')
            enrollment.EntregaCertificadoNacimiento = _parse_bool('doc_cert_nacimiento')
            enrollment.EntregaCertificadoAnualEstudios = _parse_bool('doc_cert_estudios')
            enrollment.EntregaInformePersonalidad = _parse_bool('doc_informe_personalidad')
            enrollment.EntregaInformeNotas = _parse_bool('doc_informe_notas')
            enrollment.EntregaInformePIE = _parse_bool('doc_informe_pie')
            enrollment.EntregaFotocopiaRUNEstudiante = _parse_bool('doc_fotocopia_run_est')
            enrollment.EntregaFotocopiaRUNApoderado = _parse_bool('doc_fotocopia_run_apod')
            enrollment.EntregaComprobanteDomicilio = _parse_bool('doc_comprobante_domicilio')
            enrollment.EntregaFichaMedica = _parse_bool('doc_ficha_medica')
            enrollment.ObservacionesAcademicas = request.form.get('obs_academicas')
            enrollment.ObservacionesMedicas = request.form.get('obs_medicas')
            enrollment.ObservacionesFamiliares = request.form.get('obs_familiares')
            enrollment.ComentariosEstablecimiento = request.form.get('obs_establecimiento')

            # Contactos de emergencia
            for i in [1, 2]:
                first_name_c = request.form.get(f'contacto_emergencia_{i}_first_name')
                if first_name_c:
                    nombre_completo = f"{first_name_c} {request.form.get(f'contacto_emergencia_{i}_last_name', '')} {request.form.get(f'contacto_emergencia_{i}_second_last_name', '')}".strip()
                    contacto = EdugestEmergencyContact.query.filter_by(PersonId=nueva_persona.PersonId, Orden=i).first()
                    if not contacto:
                        contacto = EdugestEmergencyContact(PersonId=nueva_persona.PersonId, Orden=i)
                        db.session.add(contacto)
                    contacto.FirstName = first_name_c
                    contacto.LastName = request.form.get(f'contacto_emergencia_{i}_last_name')
                    contacto.SecondLastName = request.form.get(f'contacto_emergencia_{i}_second_last_name')
                    contacto.NombreCompleto = nombre_completo or None
                    contacto.RUN = normalizar_rut(request.form.get(f'contacto_emergencia_{i}_run'))
                    contacto.Parentesco = request.form.get(f'contacto_emergencia_{i}_parentesco')
                    contacto.TelefonoPrincipal = request.form.get(f'contacto_emergencia_{i}_telefono')
                    contacto.TelefonoAlternativo = request.form.get(f'contacto_emergencia_{i}_telefono_alt')
                    contacto.Email = request.form.get(f'contacto_emergencia_{i}_email')
                    contacto.ProfesionOcupacion = request.form.get(f'contacto_emergencia_{i}_profesion')
                    contacto.NivelEducacional = _parse_int(f'contacto_emergencia_{i}_nivel_educativo')

            # Salud
            if any([request.form.get('grupo_sanguineo'), request.form.get('sistema_salud'),
                    request.form.get('enfermedades_permanentes'), request.form.get('alergias'),
                    request.form.get('medicamentos_permanentes'), request.form.get('restricciones_alimentarias'),
                    request.form.get('necesidades_medicas'), request.form.get('obs_medicas_detalle'),
                    request.form.get('centro_salud'), request.form.get('medico_tratante'), request.form.get('telefono_medico')]):
                health = EdugestStudentHealth.query.filter_by(PersonId=nueva_persona.PersonId).first()
                if not health:
                    health = EdugestStudentHealth(PersonId=nueva_persona.PersonId)
                    db.session.add(health)
                health.GrupoSanguineo = request.form.get('grupo_sanguineo')
                health.SistemaSalud = request.form.get('sistema_salud')
                health.EnfermedadesPermanentes = request.form.get('enfermedades_permanentes')
                health.Alergias = request.form.get('alergias')
                health.MedicamentosPermanentes = request.form.get('medicamentos_permanentes')
                health.RestriccionesAlimentarias = request.form.get('restricciones_alimentarias')
                health.NecesidadesMedicasEspeciales = request.form.get('necesidades_medicas')
                health.ObservacionesMedicasDetalle = request.form.get('obs_medicas_detalle')
                health.CentroSaludHabitual = request.form.get('centro_salud')
                health.MedicoTratante = request.form.get('medico_tratante')
                health.TelefonoMedicoTratante = request.form.get('telefono_medico')

            # PIE
            pie = EdugestStudentPIE.query.filter_by(PersonId=nueva_persona.PersonId).first()
            if _parse_bool('pertenece_pie'):
                if not pie:
                    pie = EdugestStudentPIE(PersonId=nueva_persona.PersonId)
                    db.session.add(pie)
                pie.PertenecePIE = True
                pie.DiagnosticoPIE = request.form.get('diagnostico_pie')
                pie.FechaDiagnostico = _parse_date('fecha_diagnostico_pie')
                pie.ProfesionalTratante = request.form.get('profesional_pie')
                pie.ObservacionesPIE = request.form.get('observaciones_pie')
            elif pie:
                pie.PertenecePIE = False

            db.session.commit()
            flash(f"Estudiante {first_name} {last_name} matriculado correctamente.", "success")
            return redirect(url_for('matricula.listar_estudiantes'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar: {str(e)}", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

    return render_template('matricula/formulario.html', niveles=niveles, estudiante=None)


# ============================================================================
# AJAX
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


@matricula_bp.route('/ajax/buscar_estudiante')
def ajax_buscar_estudiante():
    if not verificar_modulo_habilitado():
        return jsonify([])
    q = request.args.get('q', '').strip()
    if len(q) < 3:
        return jsonify([])

    # Subconsulta: obtener el PersonId más reciente para cada RUT (evita duplicados de persona con mismo RUT)
    from sqlalchemy import func, and_

    # Primero, buscamos personas por nombre o RUT (sin join aún, para evitar duplicados)
    # Pero necesitamos el RUT para mostrarlo. Lo haremos en dos pasos: obtener los PersonId que cumplen,
    # luego agrupar por RUT.

    # Opción más robusta: usar una subconsulta que agrupe por Identifier (RUT) y elija un PersonId.
    # Como SQLAlchemy puede ser complejo, usaremos una consulta nativa (sqlalchemy.text) o una agrupación en Python.

    # Solución: obtener todos los candidatos (personas con sus RUT) y luego agrupar en Python por RUT.
    personas_raw = Person.query.distinct(Person.PersonId).outerjoin(
        PersonIdentifier,
        and_(
            PersonIdentifier.PersonId == Person.PersonId,
            PersonIdentifier.RefPersonIdentificationSystemId == 51
        )
    ).filter(
        db.or_(
            Person.FirstName.ilike(f'%{q}%'),
            Person.LastName.ilike(f'%{q}%'),
            PersonIdentifier.Identifier.ilike(f'%{q}%')
        )
    ).limit(20).all()  # Aumentamos un poco el límite porque luego agrupamos

    # Agrupar por RUT (normalizado)
    mejores_por_rut = {}
    for p in personas_raw:
        rut = PersonIdentifier.query.filter_by(
            PersonId=p.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        rut_str = rut.Identifier if rut else None
        if not rut_str:
            continue  # Si no tiene RUT, lo ignoramos (podría ser IPE, pero no debería)
        if rut_str not in mejores_por_rut:
            mejores_por_rut[rut_str] = p
        else:
            # Si ya existe, conservamos el que tenga mayor PersonId (o podrías usar EntryDate más reciente)
            if p.PersonId > mejores_por_rut[rut_str].PersonId:
                mejores_por_rut[rut_str] = p

    resultado = []
    for p in mejores_por_rut.values():
        rut = PersonIdentifier.query.filter_by(
            PersonId=p.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        resultado.append({
            'id': p.PersonId,
            'text': f"{p.FirstName} {p.LastName} {p.SecondLastName or ''} — RUT: {rut.Identifier if rut else 'Sin RUT'}"
        })
    return jsonify(resultado)


@matricula_bp.route('/ajax/estudiante/<int:person_id>')
def ajax_datos_estudiante(person_id):
    if not verificar_modulo_habilitado():
        return jsonify({})
    data = _serialize_estudiante(person_id)
    return jsonify(data or {})


# ============================================================================
# VER DETALLE
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

    apoderados_data = obtener_apoderados_estudiante(person_id)
    ap_titular   = apoderados_data[0] if len(apoderados_data) > 0 else None
    ap_suplente1 = apoderados_data[1] if len(apoderados_data) > 1 else None
    ap_suplente2 = apoderados_data[2] if len(apoderados_data) > 2 else None

    enrollment = EdugestStudentEnrollment.query.filter_by(PersonId=person_id).first()
    contactos_emergencia = EdugestEmergencyContact.query.filter_by(PersonId=person_id).order_by(EdugestEmergencyContact.Orden).all()
    health = EdugestStudentHealth.query.filter_by(PersonId=person_id).first()
    pie = EdugestStudentPIE.query.filter_by(PersonId=person_id).first()

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
                           enrollment=enrollment,
                           contactos_emergencia=contactos_emergencia,
                           health=health,
                           pie=pie)