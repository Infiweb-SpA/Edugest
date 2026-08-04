from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from datetime import datetime
import re
import logging
from app.database import db
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationPersonRole, PersonAddress, PersonTelephone,
    PersonRelationship, PersonDegreeOrCertificate, PersonEmailAddress,
    PersonStatus, PersonHealth, PersonAllergy, PersonBirthplace
)
from app.models.edugest import (
    EdugestModule, EdugestRolePermission,
    EdugestStudentEnrollment, EdugestEmergencyContact,
    EdugestStudentHealth, EdugestStudentPIE,
    EdugestPersonRelationshipDetail
)
import unicodedata


def _normalizar_texto(texto):
    """Normaliza texto para comparación: minúsculas, sin acentos, sin espacios extra."""
    if not texto:
        return ''
    texto = texto.strip().lower()
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


# Diccionario completo: nombre de comuna normalizado -> código INE (RefCountyId)
# Fuente: Catálogo territorial INE / MINEDUC
# NOTA: Los códigos de regiones 01-09 pierden el cero inicial al ser Integer.
COMUNAS_REF = {
    # ═══ Región 15: Arica y Parinacota ═══
    'arica': 15101, 'camarones': 15102,
    'putre': 15201, 'general lagos': 15202,
    # ═══ Región 01: Tarapacá ═══
    'iquique': 1101, 'alto hospicio': 1102,
    'pozo almonte': 1201, 'camina': 1202, 'colchane': 1203,
    'huara': 1204, 'pica': 1205,
    # ═══ Región 02: Antofagasta ═══
    'antofagasta': 2101, 'mejillones': 2102, 'sierra gorda': 2103, 'taltal': 2104,
    'calama': 2201, 'ollague': 2202, 'san pedro de atacama': 2203,
    'tocopilla': 2301, 'maria elena': 2302,
    # ═══ Región 03: Atacama ═══
    'copiapo': 3101, 'caldera': 3102, 'tierra amarilla': 3103,
    'chanaral': 3201, 'diego de almagro': 3202,
    'vallenar': 3301, 'alto del carmen': 3302, 'freirina': 3303, 'huasco': 3304,
    # ═══ Región 04: Coquimbo ═══
    'la serena': 4101, 'coquimbo': 4102, 'andacollo': 4103,
    'la higuera': 4104, 'paiguano': 4105, 'vicuna': 4106,
    'illapel': 4201, 'canela': 4202, 'los vilos': 4203, 'salamanca': 4204,
    'ovalle': 4301, 'combarbala': 4302, 'monte patria': 4303,
    'punitaqui': 4304, 'rio hurtado': 4305,
    # ═══ Región 05: Valparaíso ═══
    'valparaiso': 5101, 'casablanca': 5102, 'concon': 5103,
    'juan fernandez': 5104, 'puchuncavi': 5105, 'quintero': 5106, 'vina del mar': 5107,
    'isla de pascua': 5201,
    'los andes': 5301, 'calle larga': 5302, 'rinconada': 5303, 'san esteban': 5304,
    'la ligua': 5401, 'cabildo': 5402, 'papudo': 5403, 'petorca': 5404, 'zapallar': 5405,
    'quillota': 5501, 'calera': 5502, 'hijuelas': 5503, 'la cruz': 5504,
    'limache': 5505, 'nogales': 5506, 'olmue': 5507,
    'san antonio': 5601, 'algarrobo': 5602, 'cartagena': 5603,
    'el quisco': 5604, 'el tabo': 5605, 'santo domingo': 5606,
    'san felipe': 5701, 'catemu': 5702, 'llaillay': 5703,
    'panquehue': 5704, 'putaendo': 5705, 'santa maria': 5706,
    'quilpue': 5801, 'villa alemana': 5802,
    # ═══ Región 06: O'Higgins ═══
    'rancagua': 6101, 'codegua': 6102, 'coinco': 6103, 'coltauco': 6104,
    'donihue': 6105, 'graneros': 6106, 'las cabras': 6107, 'machali': 6108,
    'malloa': 6109, 'mostazal': 6110, 'olivar': 6111, 'peumo': 6112,
    'pichidegua': 6113, 'quinta de tilcoco': 6114, 'rengo': 6115,
    'requinoa': 6116, 'san vicente': 6117,
    'pichilemu': 6201, 'la estrella': 6202, 'litueche': 6203,
    'marchihue': 6204, 'navidad': 6205, 'paredones': 6206,
    'san fernando': 6301, 'chepica': 6302, 'chimbarongo': 6303, 'lolol': 6304,
    'nancagua': 6305, 'palmilla': 6306, 'peralillo': 6307, 'placilla': 6308,
    'pumanque': 6309, 'santa cruz': 6310,
    # ═══ Región 07: Maule ═══
    'cauquenes': 7101, 'chanco': 7102, 'pelluhue': 7103,
    'curico': 7201, 'hualane': 7202, 'licanten': 7203, 'molina': 7204,
    'rauco': 7205, 'romeral': 7206, 'sagrada familia': 7207, 'teno': 7208, 'vichuquen': 7209,
    'linares': 7301, 'colbun': 7302, 'longavi': 7303, 'parral': 7304,
    'retiro': 7305, 'san javier': 7306, 'villa alegre': 7307, 'yerbas buenas': 7308,
    'talca': 7401, 'constitucion': 7402, 'curepto': 7403, 'empedrado': 7404,
    'maule': 7405, 'pelarco': 7406, 'pencahue': 7407, 'rio claro': 7408,
    'san clemente': 7409, 'san rafael': 7410,
    # ═══ Región 08: Biobío ═══
    'concepcion': 8101, 'coronel': 8102, 'chiguayante': 8103, 'florida': 8104,
    'hualqui': 8105, 'lota': 8106, 'penco': 8107, 'san pedro de la paz': 8108,
    'santajuana': 8109, 'talcahuano': 8110, 'tome': 8111, 'hualpen': 8112,
    'lebu': 8201, 'arauco': 8202, 'canete': 8203, 'contulmo': 8204,
    'curanilahue': 8205, 'los alamos': 8206, 'tirua': 8207,
    'los angeles': 8301, 'antuco': 8302, 'cabrero': 8303, 'laja': 8304,
    'mulchen': 8305, 'nacimiento': 8306, 'negrete': 8307, 'quilaco': 8308,
    'quilleco': 8309, 'san rosendo': 8310, 'santa barbara': 8311,
    'tucapel': 8312, 'yumbel': 8313, 'alto biobio': 8314,
    # ═══ Región 09: La Araucanía ═══
    'temuco': 9101, 'carahue': 9102, 'cunco': 9103, 'curarrehue': 9104,
    'freire': 9105, 'galvarino': 9106, 'gorbea': 9107, 'lautaro': 9108,
    'loncoche': 9109, 'melipeuco': 9110, 'nueva imperial': 9111,
    'padre las casas': 9112, 'perquenco': 9113, 'pitrufquen': 9114,
    'pucon': 9115, 'saavedra': 9116, 'teodoro schmidt': 9117,
    'tolten': 9118, 'vilcun': 9119, 'villarrica': 9120, 'cholchol': 9121,
    'angol': 9201, 'collipulli': 9202, 'curacautin': 9203, 'ercilla': 9204,
    'lonquimay': 9205, 'los sauces': 9206, 'lumaco': 9207,
    'puren': 9208, 'renaico': 9209, 'traiguen': 9210, 'victoria': 9211,
    # ═══ Región 10: Los Lagos ═══
    'puerto montt': 10101, 'calbuco': 10102, 'cochamo': 10103, 'fresia': 10104,
    'frutillar': 10105, 'los muermos': 10106, 'llanquihue': 10107,
    'maullin': 10108, 'puerto varas': 10109,
    'castro': 10201, 'ancud': 10202, 'chonchi': 10203, 'curaco de velez': 10204,
    'dalcahue': 10205, 'puqueldon': 10206, 'quelen': 10207, 'quellon': 10208,
    'quemchi': 10209, 'quinchao': 10210,
    'osorno': 10301, 'puerto octay': 10302, 'purranque': 10303, 'puyehue': 10304,
    'rio negro': 10305, 'san juan de la costa': 10306, 'san pablo': 10307,
    'chaiten': 10401, 'futaleufu': 10402, 'hualaihue': 10403, 'palena': 10404,
    # ═══ Región 11: Aysén ═══
    'coyhaique': 11101, 'lago verde': 11102,
    'aysen': 11201, 'cisnes': 11202, 'guaitecas': 11203,
    'chile chico': 11301, 'rio ibanez': 11302,
    'cochrane': 11401, "o'higgins": 11402, 'tortel': 11403,
    # ═══ Región 12: Magallanes ═══
    'punta arenas': 12101, 'laguna blanca': 12102, 'rio verde': 12103, 'san gregorio': 12104,
    'porvenir': 12201, 'primavera': 12202, 'timaukel': 12203,
    'natales': 12301, 'torres del paine': 12302,
    'cabo de hornos': 12401, 'antartica': 12402,
    # ═══ Región 13: Metropolitana ═══
    'santiago': 13101, 'cerrillos': 13102, 'cerro navia': 13103, 'conchali': 13104,
    'el bosque': 13105, 'estacion central': 13106, 'huechuraba': 13107,
    'independencia': 13108, 'la cisterna': 13109, 'la florida': 13110,
    'la granja': 13111, 'la pintana': 13112, 'la reina': 13113,
    'las condes': 13114, 'lo barnechea': 13115, 'lo espejo': 13116,
    'lo prado': 13117, 'macul': 13118, 'maipu': 13119, 'nunoa': 13120,
    'pedro aguirre cerda': 13121, 'penalolen': 13122, 'providencia': 13123,
    'pudahuel': 13124, 'quilicura': 13125, 'quinta normal': 13126,
    'recoleta': 13127, 'renca': 13128, 'san joaquin': 13129,
    'san miguel': 13130, 'san ramon': 13131, 'vitacura': 13132,
    'puente alto': 13201, 'pirque': 13202, 'san jose de maipo': 13203,
    'colina': 13301, 'lampa': 13302, 'tiltil': 13303,
    'san bernardo': 13401, 'buin': 13402, 'calera de tango': 13403, 'paine': 13404,
    'melipilla': 13501, 'alhue': 13502, 'curacavi': 13503, 'maria pinto': 13504, 'san pedro': 13505,
    'talagante': 13601, 'el monte': 13602, 'isla de maipo': 13603,
    'padre hurtado': 13604, 'penaflor': 13605,
    # ═══ Región 14: Los Ríos ═══
    'valdivia': 14101, 'corral': 14102, 'lanco': 14103, 'los lagos': 14104,
    'mafil': 14105, 'mariquina': 14106, 'paillaco': 14107, 'panguipulli': 14108,
    'la union': 14201, 'futrono': 14202, 'lago ranco': 14203, 'rio bueno': 14204,
    # ═══ Región 16: Ñuble ═══
    'bulnes': 16101, 'chillan': 16102, 'chillan viejo': 16103, 'el carmen': 16104,
    'pemuco': 16105, 'pinto': 16106, 'quillon': 16107, 'san ignacio': 16108, 'yungay': 16109,
    'quirihue': 16201, 'cobquecura': 16202, 'coelemu': 16203, 'ninhue': 16204,
    'portezuelo': 16205, 'ranquil': 16206, 'treguaco': 16207,
    'san carlos': 16301, 'coihueco': 16302, 'niquen': 16303,
        'san fabian': 16304, 'san nicolas': 16305,
}


def obtener_ref_county_id(nombre_comuna):
    """Convierte nombre de comuna a código RefCountyId MINEDUC/INE. Retorna None si no encuentra."""
    if not nombre_comuna:
        return None
    clave = _normalizar_texto(nombre_comuna)
    return COMUNAS_REF.get(clave)


# Diccionario: nombre de pueblo originario normalizado -> código MINEDUC (RefTribalAffiliationId)
# Fuente: Ley 19.253 / Catálogo MINEDUC CEDS - Pueblos originarios reconocidos en Chile
PUEBLOS_ORIGINARIOS_REF = {
    'mapuche': 1,
    'aymara': 2,
    'atacameno': 3,
    'atacameño': 3,
    'lickanantay': 3,
    'quechua': 4,
    'rapa nui': 5,
    'rapanui': 5,
    'pascuense': 5,
    'colla': 6,
    'diaguita': 7,
    'kawashkar': 8,
    'kawesqar': 8,
    'alacalufe': 8,
    'yagan': 9,
    'yagán': 9,
    'yamana': 9,
    'yámana': 9,
    'chango': 10,
}


def obtener_ref_tribal_affiliation_id(nombre_pueblo):
    """Convierte nombre de pueblo originario a código RefTribalAffiliationId MINEDUC. Retorna None si no encuentra."""
    if not nombre_pueblo:
        return None
    clave = _normalizar_texto(nombre_pueblo)
    return PUEBLOS_ORIGINARIOS_REF.get(clave)


# Diccionario: nombre de país normalizado -> código MINEDUC (RefCountryId)
# Fuente: Catálogo CEDS/MINEDUC basado en ISO 3166-1 numeric
# NOTA: Los códigos de 1-3 dígitos se completan a 3 dígitos según catálogo MINEDUC
PAISES_REF = {
    'chile': 152,
    'argentina': 32,
    'bolivia': 68,
    'bolivia estado plurinacional': 68,
    'brasil': 76,
    'colombia': 170,
    'ecuador': 218,
    'peru': 604,
    'perú': 604,
    'venezuela': 862,
    'venezuela republica bolivariana': 862,
    'paraguay': 600,
    'uruguay': 858,
    'mexico': 484,
    'méxico': 484,
    'cuba': 192,
    'republica dominicana': 214,
    'haiti': 332,
    'haití': 332,
    'españa': 724,
    'estados unidos': 840,
    'estados unidos de america': 840,
    'china': 156,
    'japon': 392,
    'japón': 392,
    'corea del sur': 410,
    'alemania': 276,
    'francia': 250,
    'italia': 380,
    'reino unido': 826,
    'canada': 124,
    'canadá': 124,
    'australia': 36,
    'rusia': 643,
    'india': 356,
    'honduras': 340,
    'guatemala': 320,
    'el salvador': 222,
    'nicaragua': 558,
    'costa rica': 188,
    'panama': 591,
    'panamá': 591,
    'palestina': 275,
    'siria': 760,
    'turquia': 792,
    'turquía': 792,
    'pakistan': 586,
    'senegal': 686,
    'colombia': 170,
}


def obtener_ref_country_id(nombre_pais):
    """Convierte nombre de país a código RefCountryId MINEDUC. Retorna None si no encuentra."""
    if not nombre_pais:
        return None
    clave = _normalizar_texto(nombre_pais)
    return PAISES_REF.get(clave)


def _obtener_nombre_comuna(ref_county_id):
    """Reverse lookup: código RefCountyId -> nombre de comuna. Retorna None si no encuentra."""
    if not ref_county_id:
        return None
    for nombre, codigo in COMUNAS_REF.items():
        if codigo == ref_county_id:
            return nombre.title()
    return None

logger = logging.getLogger(__name__)

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


def normalizar_rut(rut):
    """Normaliza RUT a formato xx.xxx.xxx-x."""
    if not rut:
        return None
    rut_limpio = re.sub(r'[^0-9kK]', '', rut)
    if len(rut_limpio) < 2:
        return None
    cuerpo = rut_limpio[:-1]
    dv = rut_limpio[-1].upper()
    cuerpo_formateado = ''
    while len(cuerpo) > 3:
        cuerpo_formateado = '.' + cuerpo[-3:] + cuerpo_formateado
        cuerpo = cuerpo[:-3]
    cuerpo_formateado = cuerpo + cuerpo_formateado
    return f"{cuerpo_formateado}-{dv}"


def validar_rut(rut_formateado):
    """
    Valida RUT chileno con algoritmo módulo 11.
    Retorna True si el dígito verificador es correcto.
    """
    try:
        partes = rut_formateado.split('-')
        if len(partes) != 2:
            return False
        cuerpo = partes[0].replace('.', '')
        dv = partes[1].upper()

        if not cuerpo.isdigit():
            return False

        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2

        resto = 11 - (suma % 11)
        if resto == 11:
            dv_esperado = '0'
        elif resto == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(resto)

        return dv == dv_esperado
    except (ValueError, IndexError):
        return False


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


def get_permiso_modulo(module_name):
    """Obtiene el nivel de permiso del usuario actual para un módulo.
    Admin (RoleId=1) retorna 2 automáticamente.
    Retorna: 0=Sin acceso, 1=Solo lectura, 2=Lectura y escritura"""
    if current_user.RoleId == 1:
        return 2
    modulo = EdugestModule.query.filter_by(
        ModuleName=module_name, IsEnabled=True
    ).first()
    if not modulo:
        return 0
    permiso = EdugestRolePermission.query.filter_by(
        RoleId=current_user.RoleId,
        ModuleId=modulo.ModuleId
    ).first()
    return permiso.PermissionLevel if permiso else 0


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
        email_obj = PersonEmailAddress.query.filter_by(PersonId=apod.PersonId).first()
        direccion = PersonAddress.query.filter_by(PersonId=apod.PersonId).first()
        nivel = PersonDegreeOrCertificate.query.filter_by(PersonId=apod.PersonId).first()
        detalle = EdugestPersonRelationshipDetail.query.filter_by(
            PersonRelationshipId=rel.PersonRelationshipId
        ).first()

        resultado.append({
            'persona': apod,
            'rut': rut.Identifier if rut else None,
            'telefono': fono.TelephoneNumber if fono else None,
            'email': email_obj.EmailAddress if email_obj else None,
            'direccion': direccion.StreetNumberAndName if direccion else None,
            'nivel': nivel.RefDegreeOrCertificateTypeId if nivel else None,
            'detalle': detalle
        })
    return resultado


def crear_apoderado_estudiante(estudiante_id, prefix, ref_rel_id=31):
    """
    PASO 1: Recoge los datos del formulario.
    PASO 2: Si ya existe un apoderado en ese slot, lo actualiza.
    PASO 3: Si no existe, busca por RUT para reutilizar.
    PASO 4: Si tampoco existe, crea uno nuevo.
    """

    # PASO 1: LEER DATOS DEL FORMULARIO
    first_name = request.form.get(f'{prefix}_first_name')
    last_name = request.form.get(f'{prefix}_last_name')
    second_last = request.form.get(f'{prefix}_second_last_name', '')
    rut_raw = request.form.get(f'{prefix}_rut')
    telefono = request.form.get(f'{prefix}_telefono')
    nivel = request.form.get(f'{prefix}_nivel_educativo')
    parentesco = request.form.get(f'{prefix}_parentesco')
    email = request.form.get(f'{prefix}_email')
    profesion = request.form.get(f'{prefix}_profesion')
    trabajo = request.form.get(f'{prefix}_lugar_trabajo')
    direccion = request.form.get(f'{prefix}_direccion')

    if not first_name or not last_name:
        return None

    rut = normalizar_rut(rut_raw) if rut_raw else None

    # PASO 2: DETERMINAR EL SLOT
    slot_map = {
        'ap_titular': 0,
        'ap_suplente1': 1,
        'ap_suplente2': 2
    }
    slot_index = slot_map.get(prefix, 0)

    # PASO 3: BUSCAR SI YA EXISTE UN APODERADO EN ESE SLOT
    relaciones_existentes = PersonRelationship.query.filter_by(
        PersonId=estudiante_id,
        RefPersonRelationshipId=ref_rel_id
    ).order_by(PersonRelationship.PersonRelationshipId).all()

    relacion_existente = None
    if slot_index < len(relaciones_existentes):
        relacion_existente = relaciones_existentes[slot_index]

    if relacion_existente:
        # CASO A: YA EXISTE -> ACTUALIZAR
        apoderado = Person.query.get(relacion_existente.RelatedPersonId)
        if not apoderado:
            apoderado = Person(
                FirstName=first_name, MiddleName='',
                LastName=last_name, SecondLastName=second_last
            )
            db.session.add(apoderado)
            db.session.flush()
            relacion_existente.RelatedPersonId = apoderado.PersonId
        else:
            apoderado.FirstName = first_name
            apoderado.MiddleName = ''
            apoderado.LastName = last_name
            apoderado.SecondLastName = second_last

        if rut:
            ident = PersonIdentifier.query.filter_by(
                PersonId=apoderado.PersonId,
                RefPersonIdentificationSystemId=51
            ).first()
            if ident:
                ident.Identifier = rut
            else:
                db.session.add(PersonIdentifier(
                    PersonId=apoderado.PersonId, Identifier=rut,
                    RefPersonIdentificationSystemId=51
                ))

        if telefono:
            tel = PersonTelephone.query.filter_by(PersonId=apoderado.PersonId).first()
            if tel:
                tel.TelephoneNumber = telefono
            else:
                db.session.add(PersonTelephone(
                    PersonId=apoderado.PersonId, TelephoneNumber=telefono
                ))

        if email:
            em = PersonEmailAddress.query.filter_by(PersonId=apoderado.PersonId).first()
            if em:
                em.EmailAddress = email
            else:
                db.session.add(PersonEmailAddress(
                    PersonId=apoderado.PersonId, EmailAddress=email
                ))

        if direccion:
            addr = PersonAddress.query.filter_by(PersonId=apoderado.PersonId).first()
            if addr:
                addr.StreetNumberAndName = direccion
            else:
                db.session.add(PersonAddress(
                    PersonId=apoderado.PersonId, StreetNumberAndName=direccion
                ))

        if nivel:
            deg = PersonDegreeOrCertificate.query.filter_by(PersonId=apoderado.PersonId).first()
            if deg:
                deg.RefDegreeOrCertificateTypeId = int(nivel)
            else:
                db.session.add(PersonDegreeOrCertificate(
                    PersonId=apoderado.PersonId,
                    RefDegreeOrCertificateTypeId=int(nivel)
                ))

        if parentesco or profesion or trabajo or direccion or email:
            detalle = EdugestPersonRelationshipDetail.query.filter_by(
                PersonRelationshipId=relacion_existente.PersonRelationshipId
            ).first()
            if detalle:
                detalle.Parentesco = parentesco
                detalle.ProfesionOcupacion = profesion
                detalle.LugarTrabajo = trabajo
                detalle.Direccion = direccion
                detalle.CorreoElectronico = email
                detalle.EstadoCivil = request.form.get(f'{prefix}_estado_civil')
                detalle.AutorizadoRetirarEstablecimiento = _parse_bool(f'{prefix}_autorizado_retirar')
            else:
                db.session.add(EdugestPersonRelationshipDetail(
                    PersonRelationshipId=relacion_existente.PersonRelationshipId,
                    Parentesco=parentesco,
                    ProfesionOcupacion=profesion,
                    LugarTrabajo=trabajo,
                    Direccion=direccion,
                    CorreoElectronico=email,
                    EstadoCivil=request.form.get(f'{prefix}_estado_civil'),
                    AutorizadoRetirarEstablecimiento=_parse_bool(f'{prefix}_autorizado_retirar')
                ))

        return apoderado

    else:
        # CASO B: NO EXISTE EN ESE SLOT
        apoderado_existente = None
        if rut:
            apoderado_existente = Person.query.join(PersonIdentifier).filter(
                PersonIdentifier.Identifier == rut,
                PersonIdentifier.RefPersonIdentificationSystemId == 51
            ).first()

        if apoderado_existente:
            apoderado = apoderado_existente
            apoderado.FirstName = first_name
            apoderado.MiddleName = ''
            apoderado.LastName = last_name
            apoderado.SecondLastName = second_last
        else:
            apoderado = Person(
                FirstName=first_name, MiddleName='',
                LastName=last_name, SecondLastName=second_last
            )
            db.session.add(apoderado)
            db.session.flush()

        if rut:
            ident = PersonIdentifier.query.filter_by(
                PersonId=apoderado.PersonId,
                RefPersonIdentificationSystemId=51
            ).first()
            if ident:
                ident.Identifier = rut
            else:
                db.session.add(PersonIdentifier(
                    PersonId=apoderado.PersonId, Identifier=rut,
                    RefPersonIdentificationSystemId=51
                ))

        if telefono:
            tel = PersonTelephone.query.filter_by(PersonId=apoderado.PersonId).first()
            if tel:
                tel.TelephoneNumber = telefono
            else:
                db.session.add(PersonTelephone(
                    PersonId=apoderado.PersonId, TelephoneNumber=telefono
                ))

        if email:
            em = PersonEmailAddress.query.filter_by(PersonId=apoderado.PersonId).first()
            if em:
                em.EmailAddress = email
            else:
                db.session.add(PersonEmailAddress(
                    PersonId=apoderado.PersonId, EmailAddress=email
                ))

        if direccion:
            addr = PersonAddress.query.filter_by(PersonId=apoderado.PersonId).first()
            if addr:
                addr.StreetNumberAndName = direccion
            else:
                db.session.add(PersonAddress(
                    PersonId=apoderado.PersonId, StreetNumberAndName=direccion
                ))

        if nivel:
            deg = PersonDegreeOrCertificate.query.filter_by(PersonId=apoderado.PersonId).first()
            if deg:
                deg.RefDegreeOrCertificateTypeId = int(nivel)
            else:
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
                CorreoElectronico=email,
                EstadoCivil=request.form.get(f'{prefix}_estado_civil'),
                AutorizadoRetirarEstablecimiento=_parse_bool(f'{prefix}_autorizado_retirar')
            ))

        return apoderado


def _serialize_estudiante(person_id):
    """Serializa todos los datos de un estudiante para precarga via AJAX."""
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
    contactos = EdugestEmergencyContact.query.filter_by(
        PersonId=person_id
    ).order_by(EdugestEmergencyContact.Orden).all()

    # Datos MINEDUC complementarios
    email_mineduc = PersonEmailAddress.query.filter_by(PersonId=person_id).first()
    person_status = PersonStatus.query.filter_by(PersonId=person_id).first()

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
            'estado_civil': ap['detalle'].EstadoCivil if ap['detalle'] else None,
            'autorizado_retirar': ap['detalle'].AutorizadoRetirarEstablecimiento if ap['detalle'] else False,
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

    enrollment_data = {}
    if enrollment:
        enrollment_data = {
            'nacionalidad': enrollment.Nacionalidad,
            'pais_origen': enrollment.PaisOrigen,
                        'comuna_residencia': enrollment.ComunaResidencia or _obtener_nombre_comuna(residencia.RefCountyId) if residencia else enrollment.ComunaResidencia,
            'region_residencia': enrollment.RegionResidencia,
            'email_estudiante': enrollment.EmailEstudiante,
            'telefono_estudiante': enrollment.TelefonoEstudiante,
            'colegio_procedencia': enrollment.ColegioProcedencia,
            'comuna_colegio_anterior': enrollment.ComunaColegioAnterior,
            'region_colegio_anterior': enrollment.RegionColegioAnterior,
            'ultimo_curso_aprobado': enrollment.UltimoCursoAprobado,
            'anio_ultimo_curso': enrollment.AnioUltimoCursoAprobado,
            'motivo_traslado': enrollment.MotivoTraslado,
            'fecha_ingreso_establecimiento': enrollment.FechaIngresoEstablecimiento.isoformat() if enrollment.FechaIngresoEstablecimiento else None,
            'nivel_madre': enrollment.NivelEducacionalMadre,
            'nivel_padre': enrollment.NivelEducacionalPadre,
            'nivel_apoderado': enrollment.NivelEducacionalApoderado,
            'ingreso_familiar': enrollment.IngresoFamiliar,
            'num_integrantes_hogar': enrollment.NumIntegrantesHogar,
            'alumno_prioritario': enrollment.AlumnoPrioritario,
            'alumno_preferente': enrollment.AlumnoPreferente,
            'beneficiario_sep': enrollment.BeneficiarioSEP,
            'pertenece_pueblo_originario': enrollment.PertenecePuebloOriginario,
            'pueblo_originario': enrollment.PuebloOriginario,
            'habla_lengua_indigena': enrollment.HablaLenguaIndigena,
            'lengua_indigena': enrollment.LenguaIndigena,
            'nacionalidad_extranjera': enrollment.NacionalidadExtranjera,
            'medio_transporte': enrollment.MedioTransporte,
            'utiliza_transporte_escolar': enrollment.UtilizaTransporteEscolar,
            'nombre_transportista': enrollment.NombreTransportista,
            'telefono_transportista': enrollment.TelefonoTransportista,
            'tiempo_traslado': enrollment.TiempoEstimadoTraslado,
            'autoriza_fotografias': enrollment.AutorizaFotografias,
            'autoriza_redes_sociales': enrollment.AutorizaRedesSociales,
            'autoriza_salidas': enrollment.AutorizaSalidasPedagogicas,
            'autoriza_traslado_medico': enrollment.AutorizaTrasladoCentroAsistencial,
            'autoriza_atencion_urgencia': enrollment.AutorizaAtencionMedicaUrgencia,
            'doc_cert_nacimiento': enrollment.EntregaCertificadoNacimiento,
            'doc_cert_estudios': enrollment.EntregaCertificadoAnualEstudios,
            'doc_informe_personalidad': enrollment.EntregaInformePersonalidad,
            'doc_informe_notas': enrollment.EntregaInformeNotas,
            'doc_informe_pie': enrollment.EntregaInformePIE,
            'doc_fotocopia_run_est': enrollment.EntregaFotocopiaRUNEstudiante,
            'doc_fotocopia_run_apod': enrollment.EntregaFotocopiaRUNApoderado,
            'doc_comprobante_domicilio': enrollment.EntregaComprobanteDomicilio,
            'doc_ficha_medica': enrollment.EntregaFichaMedica,
            'obs_academicas': enrollment.ObservacionesAcademicas,
            'obs_medicas': enrollment.ObservacionesMedicas,
            'obs_familiares': enrollment.ObservacionesFamiliares,
            'obs_establecimiento': enrollment.ComentariosEstablecimiento,
            'religion': enrollment.Religion,
            'acepta_religion': enrollment.AceptaReligionEnColegio,
            'tiene_computadores': enrollment.TieneComputadores,
            'cantidad_computadores': enrollment.CantidadComputadores,
            'vive_con': enrollment.ViveCon,
            'es_nuevo': enrollment.EsNuevoEnEstablecimiento,
        }

    health_data = None
    if health:
        health_data = {
            'grupo_sanguineo': health.GrupoSanguineo,
            'sistema_salud': health.SistemaSalud,
            'enfermedades_permanentes': health.EnfermedadesPermanentes,
            'alergias': health.Alergias,
            'medicamentos_permanentes': health.MedicamentosPermanentes,
            'restricciones_alimentarias': health.RestriccionesAlimentarias,
            'necesidades_medicas': health.NecesidadesMedicasEspeciales,
            'obs_medicas_detalle': health.ObservacionesMedicasDetalle,
            'centro_salud': health.CentroSaludHabitual,
            'medico_tratante': health.MedicoTratante,
            'telefono_medico': health.TelefonoMedicoTratante,
            'estatura': health.Estatura,
            'peso': health.Peso,
            'apto_educacion_fisica': health.AptoEducacionFisica,
        }

    pie_data = None
    if pie:
        pie_data = {
            'pertenece_pie': pie.PertenecePIE,
            'diagnostico_pie': pie.DiagnosticoPIE,
            'fecha_diagnostico_pie': pie.FechaDiagnostico.isoformat() if pie.FechaDiagnostico else None,
            'profesional_pie': pie.ProfesionalTratante,
            'observaciones_pie': pie.ObservacionesPIE,
            'tipo_permanencia': pie.TipoPermanencia,
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
            'ref_tribal_affiliation_id': persona.RefTribalAffiliationId,
        },
        'identificadores': ids_map,
        'residencia': residencia.StreetNumberAndName if residencia else None,
        'ref_county_id': residencia.RefCountyId if residencia else None,
        'comuna_residencia_mineduc': _obtener_nombre_comuna(residencia.RefCountyId) if residencia and residencia.RefCountyId else None,
        'ap_titular': ap_json(ap_titular),
        'ap_suplente1': ap_json(ap_suplente1),
        'ap_suplente2': ap_json(ap_suplente2),
        'enrollment': enrollment_data,
        'contactos_emergencia': [contacto_json(c) for c in contactos],
        'health': health_data,
        'pie': pie_data,
        'mineduc_extras': {
            'email_mineduc': email_mineduc.EmailAddress if email_mineduc else None,
            'status_activo': person_status.RefPersonStatusTypeId == 1 if person_status else False,
        },
    }


# ============================================================================
# LISTADO DE ESTUDIANTES
# ============================================================================
@matricula_bp.route('/')
@login_required
def listar_estudiantes():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    nivel = get_permiso_modulo('Matrícula')
    if nivel == 0:
        flash("No tiene acceso al módulo de Matrícula.", "warning")
        return redirect(url_for('portada.bienvenida'))

    roles = OrganizationPersonRole.query.filter_by(RoleId=6, ExitDate=None).all()

    mejores_por_rut = {}
    for rol in roles:
        rut_id = PersonIdentifier.query.filter_by(
            PersonId=rol.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        rut = rut_id.Identifier if rut_id else None
        if not rut:
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

    return render_template('matricula/listar.html',
                           estudiantes=estudiantes_data,
                           puede_crear=(nivel >= 2))


# ============================================================================
# FORMULARIO NUEVO / EDICION
# ============================================================================
@matricula_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_estudiante():
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    nivel = get_permiso_modulo('Matrícula')
    if nivel < 2:
        flash("No tiene permisos para crear o editar estudiantes.", "danger")
        return redirect(url_for('matricula.listar_estudiantes'))

    niveles = Organization.query.filter_by(
        RefOrganizationTypeId=40
    ).order_by(Organization.Name).all()

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        middle_name = request.form.get('middle_name', '')
        last_name = request.form.get('last_name')
        second_last = request.form.get('second_last_name', '')
        ref_sex_id = request.form.get('ref_sex_id')
        birthdate = request.form.get('birthdate')
        rut_raw = request.form.get('rut')
        rut = normalizar_rut(rut_raw) if rut_raw else None
        ipe = request.form.get('ipe', '')
        num_matricula = request.form.get('num_matricula', '')
        num_lista = request.form.get('num_lista', '')
        curso_id = request.form.get('curso_id')
        entry_date = request.form.get('entry_date')
        residencia = request.form.get('residencia')
        ap_t_first = request.form.get('ap_titular_first_name')
        ap_t_last = request.form.get('ap_titular_last_name')
        ap_t_rut = request.form.get('ap_titular_rut')

        if not all([first_name, last_name, rut, curso_id, entry_date,
                    residencia, ap_t_first, ap_t_last, ap_t_rut]):
            flash("Complete todos los campos obligatorios.", "danger")
            return redirect(url_for('matricula.nuevo_estudiante'))

        # S5 + S6: Validar formato Y dígito verificador
        if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$', rut):
            flash('El RUT del estudiante no tiene formato válido. '
                  'Use el formato: xx.xxx.xxx-x', 'danger')
            return redirect(url_for('matricula.nuevo_estudiante'))

        if not validar_rut(rut):
            flash('El RUT ingresado no es válido. '
                  'Verifique el dígito verificador.', 'danger')
            return redirect(url_for('matricula.nuevo_estudiante'))

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

            # Verificar si ya existe una persona con este RUT
            persona_existente = None
            if rut:
                persona_existente = Person.query.join(PersonIdentifier).filter(
                    PersonIdentifier.Identifier == rut,
                    PersonIdentifier.RefPersonIdentificationSystemId == 51
                ).first()

            # Validar person_id_precargado contra el RUT
            person_id_precargado = request.form.get('person_id_precargado')
            if person_id_precargado and person_id_precargado.isdigit():
                persona_precargada = Person.query.get(int(person_id_precargado))
                if not persona_precargada:
                    flash("El estudiante seleccionado no existe.", "danger")
                    return redirect(url_for('matricula.nuevo_estudiante'))

                rut_precargado = PersonIdentifier.query.filter_by(
                    PersonId=persona_precargada.PersonId,
                    RefPersonIdentificationSystemId=51
                ).first()

                if rut_precargado and rut and rut_precargado.Identifier == rut:
                    nueva_persona = persona_precargada
                    es_nuevo = False
                else:
                    if persona_existente:
                        nueva_persona = persona_existente
                        es_nuevo = False
                        flash("Se detectó un estudiante existente con el mismo RUT. "
                              "Se procederá a re-matricular.", "info")
                    else:
                        nueva_persona = Person(
                            FirstName=first_name, MiddleName=middle_name,
                            LastName=last_name, SecondLastName=second_last,
                            RefSexId=int(ref_sex_id) if ref_sex_id else None,
                            Birthdate=birthdate_obj
                        )
                        db.session.add(nueva_persona)
                        db.session.flush()
                        es_nuevo = True
            elif persona_existente:
                nueva_persona = persona_existente
                es_nuevo = False
                flash("Se detectó un estudiante existente con el mismo RUT. "
                      "Se procederá a re-matricular.", "info")
            else:
                nueva_persona = Person(
                    FirstName=first_name, MiddleName=middle_name,
                    LastName=last_name, SecondLastName=second_last,
                    RefSexId=int(ref_sex_id) if ref_sex_id else None,
                    Birthdate=birthdate_obj
                )
                db.session.add(nueva_persona)
                db.session.flush()
                es_nuevo = True

            # Actualizar datos personales
            nueva_persona.FirstName = first_name
            nueva_persona.MiddleName = middle_name
            nueva_persona.LastName = last_name
            nueva_persona.SecondLastName = second_last
            nueva_persona.RefSexId = int(ref_sex_id) if ref_sex_id else None
            nueva_persona.Birthdate = birthdate_obj

            # Cerrar roles anteriores (re-matricula)
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
                        PersonId=nueva_persona.PersonId,
                        RefPersonIdentificationSystemId=sys_id
                    ).first()
                    if ident:
                        ident.Identifier = val_identificador
                    else:
                        db.session.add(PersonIdentifier(
                            PersonId=nueva_persona.PersonId,
                            Identifier=val_identificador,
                            RefPersonIdentificationSystemId=sys_id
                        ))

            upsert_identifier(51, rut)
            upsert_identifier(52, ipe)
            upsert_identifier(55, num_matricula)
            upsert_identifier(54, num_lista)

            # Nuevo rol en el curso
            db.session.add(OrganizationPersonRole(
                OrganizationId=int(curso_id),
                PersonId=nueva_persona.PersonId,
                RoleId=6,
                EntryDate=entry_date_obj,
                ExitDate=None
            ))

            # Residencia (con mapeo de comuna a código MINEDUC)
            if residencia:
                addr = PersonAddress.query.filter_by(
                    PersonId=nueva_persona.PersonId
                ).first()
                ref_county_id = obtener_ref_county_id(
                    request.form.get('comuna_residencia')
                )
                if addr:
                    addr.StreetNumberAndName = residencia
                    addr.RefCountyId = ref_county_id
                else:
                    db.session.add(PersonAddress(
                        PersonId=nueva_persona.PersonId,
                        StreetNumberAndName=residencia,
                        RefCountyId=ref_county_id
                    ))

            # Apoderados
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_titular')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente1')
            crear_apoderado_estudiante(nueva_persona.PersonId, 'ap_suplente2')

            # Datos adicionales de matricula (EDUGEST)
            enrollment = EdugestStudentEnrollment.query.filter_by(
                PersonId=nueva_persona.PersonId
            ).first()
            if not enrollment:
                enrollment = EdugestStudentEnrollment(
                    PersonId=nueva_persona.PersonId
                )
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
            enrollment.Religion = request.form.get('religion')
            enrollment.AceptaReligionEnColegio = _parse_bool('acepta_religion')
            enrollment.TieneComputadores = _parse_bool('tiene_computadores')
            enrollment.CantidadComputadores = _parse_int('cantidad_computadores')
            enrollment.ViveCon = request.form.get('vive_con')

                        # Contactos de emergencia
            for i in [1, 2]:
                first_name_c = request.form.get(f'contacto_emergencia_{i}_first_name', '').strip()
                last_name_c = request.form.get(f'contacto_emergencia_{i}_last_name', '').strip()
                telefono_c = request.form.get(f'contacto_emergencia_{i}_telefono', '').strip()
                parentesco_c = request.form.get(f'contacto_emergencia_{i}_parentesco', '').strip()

                # Guardar si hay ALGÚN dato del contacto, no solo el nombre
                tiene_datos = any([
                    first_name_c, last_name_c, telefono_c, parentesco_c,
                    request.form.get(f'contacto_emergencia_{i}_second_last_name', '').strip(),
                    request.form.get(f'contacto_emergencia_{i}_run', '').strip(),
                    request.form.get(f'contacto_emergencia_{i}_email', '').strip(),
                    request.form.get(f'contacto_emergencia_{i}_telefono_alt', '').strip(),
                    request.form.get(f'contacto_emergencia_{i}_profesion', '').strip(),
                ])

                if tiene_datos:
                    nombre_completo = (
                        f"{first_name_c} "
                        f"{last_name_c} "
                        f"{request.form.get(f'contacto_emergencia_{i}_second_last_name', '')}"
                    ).strip()
                    contacto = EdugestEmergencyContact.query.filter_by(
                        PersonId=nueva_persona.PersonId, Orden=i
                    ).first()
                    if not contacto:
                        contacto = EdugestEmergencyContact(
                            PersonId=nueva_persona.PersonId, Orden=i
                        )
                        db.session.add(contacto)
                    contacto.FirstName = first_name_c or None
                    contacto.LastName = last_name_c or None
                    contacto.SecondLastName = request.form.get(f'contacto_emergencia_{i}_second_last_name') or None
                    contacto.NombreCompleto = nombre_completo or None
                    contacto.RUN = normalizar_rut(request.form.get(f'contacto_emergencia_{i}_run'))
                    contacto.Parentesco = parentesco_c or None
                    contacto.TelefonoPrincipal = telefono_c or None
                    contacto.TelefonoAlternativo = request.form.get(f'contacto_emergencia_{i}_telefono_alt') or None
                    contacto.Email = request.form.get(f'contacto_emergencia_{i}_email') or None
                    contacto.ProfesionOcupacion = request.form.get(f'contacto_emergencia_{i}_profesion') or None
                    contacto.NivelEducacional = _parse_int(f'contacto_emergencia_{i}_nivel_educativo')

            # Salud (EDUGEST)
            if any([
                request.form.get('grupo_sanguineo'),
                request.form.get('sistema_salud'),
                request.form.get('enfermedades_permanentes'),
                request.form.get('alergias'),
                request.form.get('medicamentos_permanentes'),
                request.form.get('restricciones_alimentarias'),
                request.form.get('necesidades_medicas'),
                request.form.get('obs_medicas_detalle'),
                request.form.get('centro_salud'),
                request.form.get('medico_tratante'),
                request.form.get('telefono_medico')
            ]):
                health = EdugestStudentHealth.query.filter_by(
                    PersonId=nueva_persona.PersonId
                ).first()
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
                health.Estatura = request.form.get('estatura')
                health.Peso = request.form.get('peso')
                health.AptoEducacionFisica = _parse_bool('apto_educacion_fisica')

            # PIE
            pie = EdugestStudentPIE.query.filter_by(
                PersonId=nueva_persona.PersonId
            ).first()
            if _parse_bool('pertenece_pie'):
                if not pie:
                    pie = EdugestStudentPIE(PersonId=nueva_persona.PersonId)
                    db.session.add(pie)
                pie.PertenecePIE = True
                pie.DiagnosticoPIE = request.form.get('diagnostico_pie')
                pie.FechaDiagnostico = _parse_date('fecha_diagnostico_pie')
                pie.ProfesionalTratante = request.form.get('profesional_pie')
                pie.ObservacionesPIE = request.form.get('observaciones_pie')
                pie.TipoPermanencia = request.form.get('tipo_permanencia')
            elif pie:
                pie.PertenecePIE = False

            # ═══════════════════════════════════════════════════════════
            # ESPEJO EN TABLAS MINEDUC
            # ═══════════════════════════════════════════════════════════

            # --- PersonStatus: Marcar estudiante como activo ---
            status = PersonStatus.query.filter_by(
                PersonId=nueva_persona.PersonId
            ).first()
            if not status:
                status = PersonStatus(
                    PersonId=nueva_persona.PersonId,
                    RefPersonStatusTypeId=1,  # 1 = Activo
                    StatusStartDate=entry_date_obj,
                    Description='Matriculado'
                )
                db.session.add(status)
            else:
                status.RefPersonStatusTypeId = 1
                status.StatusStartDate = entry_date_obj
                status.StatusEndDate = None
                status.Description = 'Matriculado'

                        # --- PersonEmailAddress: Correo del estudiante ---
            email_est = request.form.get('email_estudiante')
            if email_est:
                email_mineduc = PersonEmailAddress.query.filter_by(
                    PersonId=nueva_persona.PersonId
                ).first()
                if email_mineduc:
                    email_mineduc.EmailAddress = email_est
                else:
                    db.session.add(PersonEmailAddress(
                        PersonId=nueva_persona.PersonId,
                        Address=email_est
                    ))

            # --- PersonTelephone: Teléfono del estudiante ---
            telefono_est = request.form.get('telefono_estudiante')
            if telefono_est:
                tel_mineduc = PersonTelephone.query.filter_by(
                    PersonId=nueva_persona.PersonId
                ).first()
                if tel_mineduc:
                    tel_mineduc.TelephoneNumber = telefono_est
                else:
                    db.session.add(PersonTelephone(
                        PersonId=nueva_persona.PersonId,
                        TelephoneNumber=telefono_est
                    ))

            # --- PersonHealth: Datos de salud en formato MINEDUC ---
            tiene_datos_salud = any([
                request.form.get('sistema_salud'),
                request.form.get('estatura'),
                request.form.get('peso'),
                request.form.get('grupo_sanguineo'),
            ])
            if tiene_datos_salud:
                health_mineduc = PersonHealth.query.filter_by(
                    PersonId=nueva_persona.PersonId
                ).first()
                if not health_mineduc:
                    health_mineduc = PersonHealth(
                        PersonId=nueva_persona.PersonId
                    )
                    db.session.add(health_mineduc)

                # Construir descripción consolidada
                partes_salud = []
                if request.form.get('grupo_sanguineo'):
                    partes_salud.append(f"Grupo sanguíneo: {request.form.get('grupo_sanguineo')}")
                if request.form.get('sistema_salud'):
                    partes_salud.append(f"Sistema de salud: {request.form.get('sistema_salud')}")
                if request.form.get('estatura'):
                    partes_salud.append(f"Estatura: {request.form.get('estatura')} cm")
                if request.form.get('peso'):
                    partes_salud.append(f"Peso: {request.form.get('peso')} KG")
                health_mineduc.Description = ' | '.join(partes_salud)

                        # --- PersonAllergy: Alergias en formato MINEDUC ---
            alergias_texto = request.form.get('alergias', '').strip()
            if alergias_texto:
                allergy_mineduc = PersonAllergy.query.filter_by(
                    PersonId=nueva_persona.PersonId
                ).first()
                if allergy_mineduc:
                    allergy_mineduc.AllergyDescription = alergias_texto
                else:
                    db.session.add(PersonAllergy(
                        PersonId=nueva_persona.PersonId,
                        AllergyDescription=alergias_texto
                    ))

            # --- Person.RefTribalAffiliationId: Pueblo originario ---
            if _parse_bool('pertenece_pueblo_originario'):
                pueblo_nombre = request.form.get('pueblo_originario')
                ref_tribal_id = obtener_ref_tribal_affiliation_id(pueblo_nombre)
                if ref_tribal_id:
                    nueva_persona.RefTribalAffiliationId = ref_tribal_id

                        # --- PersonBirthplace: País de nacimiento ---
            pais_origen = request.form.get('pais_origen')
            if pais_origen:
                ref_country_id = obtener_ref_country_id(pais_origen)
                if ref_country_id:
                    bp = PersonBirthplace.query.filter_by(
                        PersonId=nueva_persona.PersonId
                    ).first()
                    if bp:
                        bp.RefCountryId = ref_country_id
                    else:
                        db.session.add(PersonBirthplace(
                            PersonId=nueva_persona.PersonId,
                            RefCountryId=ref_country_id
                        ))

            # ═══════════════════════════════════════════════════════════
            # FIN ESPEJO MINEDUC
            # ═══════════════════════════════════════════════════════════

            db.session.commit()
            flash(
                f"Estudiante {first_name} {last_name} matriculado correctamente.",
                "success"
            )
            return redirect(url_for('matricula.listar_estudiantes'))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Error al guardar matrícula: {str(e)}')
            flash('Ocurrió un error al guardar. Por favor, intente nuevamente.', 'danger')
            return redirect(url_for('matricula.nuevo_estudiante'))

    return render_template(
        'matricula/formulario.html',
        niveles=niveles,
        estudiante=None
    )


# ============================================================================
# AJAX — Con verificación de permisos
# ============================================================================
@matricula_bp.route('/ajax/grados/<int:nivel_id>')
@login_required
def ajax_grados(nivel_id):
    if not verificar_modulo_habilitado():
        return jsonify([])
    permiso = get_permiso_modulo('Matrícula')
    if permiso < 1:
        return jsonify({'error': 'Sin permisos'}), 403

    # Lógica recursiva para encontrar todos los descendientes
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
@login_required
def ajax_cursos(grado_id):
    if not verificar_modulo_habilitado():
        return jsonify([])
    permiso = get_permiso_modulo('Matrícula')
    if permiso < 1:
        return jsonify({'error': 'Sin permisos'}), 403

    relaciones = OrganizationRelationship.query.filter_by(
        ParentOrganizationId=grado_id
    ).all()
    curso_ids = [r.OrganizationId for r in relaciones]
    cursos = Organization.query.filter(
        Organization.OrganizationId.in_(curso_ids),
        Organization.RefOrganizationTypeId == 21
    ).order_by(Organization.ShortName).all()
    return jsonify([
        {
            'id': c.OrganizationId,
            'nombre': f"{c.Name} ({c.ShortName})",
            'letra': c.ShortName
        }
        for c in cursos
    ])


@matricula_bp.route('/ajax/buscar_estudiante')
@login_required
def ajax_buscar_estudiante():
    if not verificar_modulo_habilitado():
        return jsonify([])
    permiso = get_permiso_modulo('Matrícula')
    if permiso < 1:
        return jsonify({'error': 'Sin permisos'}), 403

    q = request.args.get('q', '').strip()
    if len(q) < 3:
        return jsonify([])

    from sqlalchemy import and_

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
    ).limit(20).all()

    mejores_por_rut = {}
    for p in personas_raw:
        rut = PersonIdentifier.query.filter_by(
            PersonId=p.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        rut_str = rut.Identifier if rut else None
        if not rut_str:
            continue
        if rut_str not in mejores_por_rut:
            mejores_por_rut[rut_str] = p
        else:
            if p.PersonId > mejores_por_rut[rut_str].PersonId:
                mejores_por_rut[rut_str] = p

    resultado = []
    for p in mejores_por_rut.values():
        rut = PersonIdentifier.query.filter_by(
            PersonId=p.PersonId, RefPersonIdentificationSystemId=51
        ).first()
        resultado.append({
            'id': p.PersonId,
            'text': (
                f"{p.FirstName} {p.LastName} {p.SecondLastName or ''} "
                f"\u2014 RUT: {rut.Identifier if rut else 'Sin RUT'}"
            )
        })
    return jsonify(resultado)


@matricula_bp.route('/ajax/estudiante/<int:person_id>')
@login_required
def ajax_datos_estudiante(person_id):
    if not verificar_modulo_habilitado():
        return jsonify({})
    permiso = get_permiso_modulo('Matrícula')
    if permiso < 1:
        return jsonify({'error': 'Sin permisos'}), 403

    data = _serialize_estudiante(person_id)
    return jsonify(data or {})


# ============================================================================
# VER DETALLE
# ============================================================================
@matricula_bp.route('/<int:person_id>')
@login_required
def ver_estudiante(person_id):
    if not verificar_modulo_habilitado():
        return redirect(url_for('admin.dashboard'))

    persona = Person.query.get_or_404(person_id)
    identificadores = PersonIdentifier.query.filter_by(PersonId=person_id).all()
    roles = OrganizationPersonRole.query.filter_by(
        PersonId=person_id, RoleId=6
    ).all()
    ids_map = {
        i.RefPersonIdentificationSystemId: i.Identifier
        for i in identificadores
    }
    residencia = PersonAddress.query.filter_by(PersonId=person_id).first()

    apoderados_data = obtener_apoderados_estudiante(person_id)
    ap_titular = apoderados_data[0] if len(apoderados_data) > 0 else None
    ap_suplente1 = apoderados_data[1] if len(apoderados_data) > 1 else None
    ap_suplente2 = apoderados_data[2] if len(apoderados_data) > 2 else None

    enrollment = EdugestStudentEnrollment.query.filter_by(PersonId=person_id).first()
    contactos_emergencia = EdugestEmergencyContact.query.filter_by(
        PersonId=person_id
    ).order_by(EdugestEmergencyContact.Orden).all()
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