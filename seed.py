from app import create_app
from app.database import db
from app.models import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationIdentifier, OrganizationPersonRole,
    EdugestCurriculumPlan, EdugestModule,
    # NUEVOS MODELOS DE MATRÍCULA
    EdugestStudentEnrollment, EdugestEmergencyContact,
    EdugestStudentHealth, EdugestStudentPIE,
    EdugestPersonRelationshipDetail
)

app = create_app()


def crear_jerarquia_completa():
    """Crea la jerarquía completa MINEDUC para un establecimiento de prueba."""
    import string

    # 0. MÓDULOS DEL SISTEMA
    if not EdugestModule.query.first():
        modulos_iniciales = [
            EdugestModule(ModuleName="Libro Digital", IsEnabled=True),
            EdugestModule(ModuleName="Evaluaciones", IsEnabled=True),
            EdugestModule(ModuleName="Biblioteca CRA", IsEnabled=True),
            EdugestModule(ModuleName="Comunicaciones", IsEnabled=True),
            EdugestModule(ModuleName="Matrícula", IsEnabled=True)
        ]
        db.session.add_all(modulos_iniciales)
        db.session.commit()
        print("✅ Módulos base creados.")
    else:
        modulo_matricula = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
        if not modulo_matricula:
            db.session.add(EdugestModule(ModuleName="Matrícula", IsEnabled=True))
            db.session.commit()
            print("✅ Módulo Matrícula agregado.")
        else:
            print("ℹ️ Módulos ya existen.")

    # 1. ESTABLECIMIENTO (RBD)
    rbd = Organization.query.filter_by(ShortName="RBD09599", RefOrganizationTypeId=10).first()
    if not rbd:
        rbd = Organization(Name="Liceo Bicentenario Temuco", ShortName="RBD09599", RefOrganizationTypeId=10)
        db.session.add(rbd)
        db.session.flush()
        db.session.add(OrganizationIdentifier(OrganizationId=rbd.OrganizationId, Identifier="09599", RefOrganizationIdentificationSystemId=1))
        print(f"✅ Establecimiento creado: {rbd.Name}")
    else:
        print(f"ℹ️ Establecimiento ya existe: {rbd.Name}")

    # 2. MODALIDAD (38)
    modalidad = Organization.query.filter_by(Name="Regular", RefOrganizationTypeId=38).first()
    if not modalidad:
        modalidad = Organization(Name="Regular", RefOrganizationTypeId=38)
        db.session.add(modalidad)
        db.session.flush()
        db.session.add(OrganizationRelationship(OrganizationId=modalidad.OrganizationId, ParentOrganizationId=rbd.OrganizationId))
        print("✅ Modalidad creada: Regular")

    # 3. JORNADA (39)
    jornada = Organization.query.filter_by(Name="Mañana", RefOrganizationTypeId=39).first()
    if not jornada:
        jornada = Organization(Name="Mañana", RefOrganizationTypeId=39)
        db.session.add(jornada)
        db.session.flush()
        db.session.add(OrganizationRelationship(OrganizationId=jornada.OrganizationId, ParentOrganizationId=modalidad.OrganizationId))
        print("✅ Jornada creada: Mañana")

    # 4. NIVELES (40)
    niveles_data = [("02", "Enseñanza Básica Niños"), ("05", "Enseñanza Media Humanístico Científica Jóvenes")]
    niveles = {}
    for codigo, nombre in niveles_data:
        nivel = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=40).first()
        if not nivel:
            nivel = Organization(Name=nombre, ShortName=codigo, RefOrganizationTypeId=40)
            db.session.add(nivel)
            db.session.flush()
            db.session.add(OrganizationRelationship(OrganizationId=nivel.OrganizationId, ParentOrganizationId=jornada.OrganizationId))
            print(f"✅ Nivel creado: {nombre}")
        niveles[codigo] = nivel

    # 5. RAMAS (41)
    ramas_data = [("02", "Educación General"), ("05", "Humanístico-Científica")]
    ramas = {}
    for codigo, nombre in ramas_data:
        rama = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=41).first()
        if not rama:
            rama = Organization(Name=nombre, RefOrganizationTypeId=41)
            db.session.add(rama)
            db.session.flush()
            print(f"✅ Rama creada: {nombre}")
        ramas[codigo] = rama
        db.session.add(OrganizationRelationship(OrganizationId=rama.OrganizationId, ParentOrganizationId=niveles[codigo].OrganizationId))

    # 6. SECTORES (42)
    sectores = {}
    for codigo, rama in ramas.items():
        nombre = f"Sin Sector {codigo}"
        sector = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=42).first()
        if not sector:
            sector = Organization(Name=nombre, RefOrganizationTypeId=42)
            db.session.add(sector)
            db.session.flush()
            db.session.add(OrganizationRelationship(OrganizationId=sector.OrganizationId, ParentOrganizationId=rama.OrganizationId))
            print(f"✅ Sector creado: {nombre}")
        sectores[codigo] = sector

    # 7. ESPECIALIDADES (43)
    especialidades = {}
    for codigo, sector in sectores.items():
        nombre = f"Sin Especialidad {codigo}"
        esp = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=43).first()
        if not esp:
            esp = Organization(Name=nombre, RefOrganizationTypeId=43)
            db.session.add(esp)
            db.session.flush()
            db.session.add(OrganizationRelationship(OrganizationId=esp.OrganizationId, ParentOrganizationId=sector.OrganizationId))
            print(f"✅ Especialidad creada: {nombre}")
        especialidades[codigo] = esp

    # 8. TIPOS DE CURSO (44)
    tipos_curso = {}
    for codigo, esp in especialidades.items():
        nombre = f"Simple {codigo}"
        tipo = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=44).first()
        if not tipo:
            tipo = Organization(Name=nombre, RefOrganizationTypeId=44)
            db.session.add(tipo)
            db.session.flush()
            db.session.add(OrganizationRelationship(OrganizationId=tipo.OrganizationId, ParentOrganizationId=esp.OrganizationId))
            print(f"✅ Tipo de curso creado: {nombre}")
        tipos_curso[codigo] = tipo

    # 9. CÓDIGOS DE ENSEÑANZA (45)
    codigos_data = {"02": ("110", "Básica Niños"), "05": ("310", "Media HC Jóvenes")}
    codigos = {}
    for codigo, tipo in tipos_curso.items():
        val, short = codigos_data[codigo]
        c = Organization.query.filter_by(Name=val, RefOrganizationTypeId=45).first()
        if not c:
            c = Organization(Name=val, ShortName=short, RefOrganizationTypeId=45)
            db.session.add(c)
            db.session.flush()
            db.session.add(OrganizationRelationship(OrganizationId=c.OrganizationId, ParentOrganizationId=tipo.OrganizationId))
            print(f"✅ Código enseñanza creado: {val} ({short})")
        codigos[codigo] = c

    # 10. GRADOS (46)
    grados_data = {
        "02": ["1º Básico", "2º Básico", "3º Básico", "4º Básico", "5º Básico", "6º Básico", "7º Básico", "8º Básico"],
        "05": ["1º Medio", "2º Medio", "3º Medio", "4º Medio"]
    }
    grados_creados = {}
    for codigo_nivel, lista in grados_data.items():
        for nombre in lista:
            g = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=46).first()
            if not g:
                g = Organization(Name=nombre, RefOrganizationTypeId=46)
                db.session.add(g)
                db.session.flush()
                db.session.add(OrganizationRelationship(OrganizationId=g.OrganizationId, ParentOrganizationId=codigos[codigo_nivel].OrganizationId))
                print(f"✅ Grado creado: {nombre}")
            grados_creados[nombre] = g

    # 11. CURSOS CON LETRAS (21)
    letras = list(string.ascii_uppercase)
    creados = 0
    for grado_nombre, grado in grados_creados.items():
        for letra in letras:
            curso_nombre = f"{grado_nombre} {letra}"
            if not Organization.query.filter_by(Name=curso_nombre, RefOrganizationTypeId=21).first():
                curso = Organization(Name=curso_nombre, ShortName=letra, RefOrganizationTypeId=21)
                db.session.add(curso)
                db.session.flush()
                db.session.add(OrganizationRelationship(OrganizationId=curso.OrganizationId, ParentOrganizationId=grado.OrganizationId))
                creados += 1
    db.session.commit()
    print(f"\n🎉 Jerarquía completa. Total cursos nuevos: {creados}")
    return True


def crear_asignaturas_basicas_mineduc(grado_id):
    """
    Crea asignaturas (Tipo 22) y las vincula al grado (Tipo 46).
    Verifica por grado específico para no saltarse grados posteriores.
    """
    asignaturas_nombres = ["Lenguaje y Comunicación", "Matemática", "Historia", "Ciencias Naturales"]
    creadas = []

    for nombre in asignaturas_nombres:
        # Verificar si YA existe esta asignatura vinculada a ESTE grado específico
        asig_existente = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.Name == nombre,
            Organization.RefOrganizationTypeId == 22,
            OrganizationRelationship.ParentOrganizationId == grado_id
        ).first()

        if not asig_existente:
            asig = Organization(Name=nombre, ShortName=nombre[:3].upper(), RefOrganizationTypeId=22)
            db.session.add(asig)
            db.session.flush()

            db.session.add(OrganizationRelationship(
                OrganizationId=asig.OrganizationId,
                ParentOrganizationId=grado_id
            ))
            creadas.append(asig)
            print(f"   ✅ {nombre} creada para Grado ID {grado_id}")
        else:
            creadas.append(asig_existente)
            print(f"   ℹ️ {nombre} ya existe para Grado ID {grado_id}")

    db.session.commit()
    return creadas


def crear_planificaciones(asignatura):
    """Crea planificaciones curriculares para una asignatura"""
    if not EdugestCurriculumPlan.query.filter_by(OrganizationId=asignatura.OrganizationId).first():
        unidades = [
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, UnitTitle="Unidad 1: Números racionales y potencias"),
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, UnitTitle="Unidad 2: Álgebra y funciones lineales"),
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, UnitTitle="Unidad 3: Geometría y Teorema de Pitágoras")
        ]
        db.session.add_all(unidades)
        db.session.commit()
        print("✅ Planificaciones curriculares creadas.")


def crear_apoderado_completo(estudiante_id, datos_apoderado, orden=0):
    """
    Crea un apoderado con todos los campos extendidos (email, parentesco, profesión, etc.)
    y lo vincula al estudiante.
    """
    from app.models.mineduc import PersonRelationship, PersonTelephone, PersonEmailAddress, PersonAddress, PersonDegreeOrCertificate
    
    apoderado = Person(
        FirstName=datos_apoderado["nombre"],
        MiddleName="",
        LastName=datos_apoderado["apellido_p"],
        SecondLastName=datos_apoderado.get("apellido_m", "")
    )
    db.session.add(apoderado)
    db.session.flush()

    # RUT
    if datos_apoderado.get("rut"):
        db.session.add(PersonIdentifier(
            PersonId=apoderado.PersonId,
            Identifier=datos_apoderado["rut"],
            RefPersonIdentificationSystemId=51
        ))
    
    # Teléfono
    if datos_apoderado.get("telefono"):
        db.session.add(PersonTelephone(
            PersonId=apoderado.PersonId,
            TelephoneNumber=datos_apoderado["telefono"]
        ))
    
    # Email
    if datos_apoderado.get("email"):
        db.session.add(PersonEmailAddress(
            PersonId=apoderado.PersonId,
            EmailAddress=datos_apoderado["email"]
        ))
    
    # Dirección
    if datos_apoderado.get("direccion"):
        db.session.add(PersonAddress(
            PersonId=apoderado.PersonId,
            StreetNumberAndName=datos_apoderado["direccion"]
        ))
    
    # Nivel educacional
    if datos_apoderado.get("nivel_educativo"):
        db.session.add(PersonDegreeOrCertificate(
            PersonId=apoderado.PersonId,
            RefDegreeOrCertificateTypeId=int(datos_apoderado["nivel_educativo"])
        ))

    # Relación
    rel = PersonRelationship(
        PersonId=estudiante_id,
        RelatedPersonId=apoderado.PersonId,
        RefPersonRelationshipId=31
    )
    db.session.add(rel)
    db.session.flush()

    # Detalles extendidos de la relación
    if any([
        datos_apoderado.get("parentesco"),
        datos_apoderado.get("profesion"),
        datos_apoderado.get("lugar_trabajo"),
        datos_apoderado.get("direccion"),
        datos_apoderado.get("email")
    ]):
        db.session.add(EdugestPersonRelationshipDetail(
            PersonRelationshipId=rel.PersonRelationshipId,
            Parentesco=datos_apoderado.get("parentesco"),
            ProfesionOcupacion=datos_apoderado.get("profesion"),
            LugarTrabajo=datos_apoderado.get("lugar_trabajo"),
            Direccion=datos_apoderado.get("direccion"),
            CorreoElectronico=datos_apoderado.get("email")
        ))

    return apoderado


def crear_alumnos_prueba(curso_id):
    """Crea 5 alumnos ficticios con datos completos de matrícula extendida"""
    from datetime import date
    from app.models.mineduc import PersonAddress, PersonTelephone, PersonEmailAddress
    
    alumnos_datos = [
        {
            "rut": "21.345.678-9", 
            "nombre": "Juan Carlos", 
            "apellido_p": "Pérez", 
            "apellido_m": "Muñoz",
            "sexo": 1,
            "nacimiento": date(2015, 3, 15),
            "residencia": "Av. Alemania 1234, Temuco",
            "email_est": "juan.perez@ejemplo.cl",
            "fono_est": "+56912345678",
            "nacionalidad": "Chilena",
            "pais_origen": "Chile",
            "comuna": "Temuco",
            "region": "La Araucanía",
            "colegio_procedencia": "Escuela Santa María",
            "comuna_colegio": "Temuco",
            "region_colegio": "La Araucanía",
            "ultimo_curso": "8º Básico",
            "anio_ultimo_curso": 2024,
            "motivo_traslado": "Cambio de domicilio familiar",
            "pie": False,
            "alergias": "Polen, maní",
            "sistema_salud": "Fonasa",
            "grupo_sanguineo": "O+",
            "enfermedades": "Asma leve",
            "medicamentos": "Salbutamol inhalador",
            "contacto_emergencia_1": {
                "nombre": "María Muñoz", "run": "15.234.567-8", "parentesco": "Madre",
                "telefono": "+56987654321", "telefono_alt": "+56911112222"
            },
            "contacto_emergencia_2": {
                "nombre": "Roberto Pérez", "run": "12.345.678-9", "parentesco": "Padre",
                "telefono": "+56933334444", "telefono_alt": ""
            },
            "apoderado": {
                "nombre": "María Elena", "apellido_p": "Muñoz", "apellido_m": "Rojas",
                "rut": "15.234.567-8", "telefono": "+56987654321", "email": "maria.munoz@email.cl",
                "parentesco": "Madre", "profesion": "Enfermera", "lugar_trabajo": "Hospital Regional",
                "direccion": "Av. Alemania 1234, Temuco", "nivel_educativo": 5
            },
            "apoderado_suplente": {
                "nombre": "Roberto", "apellido_p": "Pérez", "apellido_m": "Soto",
                "rut": "12.345.678-9", "telefono": "+56933334444", "email": "roberto.perez@email.cl",
                "parentesco": "Padre", "profesion": "Constructor", "lugar_trabajo": "Constructora Temuco",
                "direccion": "", "nivel_educativo": 3
            }
        },
        {
            "rut": "22.456.789-K", 
            "nombre": "María José", 
            "apellido_p": "González", 
            "apellido_m": "Tapia",
            "sexo": 2,
            "nacimiento": date(2015, 7, 22),
            "residencia": "Los Pinos 456, Padre Las Casas",
            "email_est": "",
            "fono_est": "",
            "nacionalidad": "Chilena",
            "pais_origen": "Chile",
            "comuna": "Padre Las Casas",
            "region": "La Araucanía",
            "colegio_procedencia": "Colegio Padre Las Casas",
            "comuna_colegio": "Padre Las Casas",
            "region_colegio": "La Araucanía",
            "ultimo_curso": "8º Básico",
            "anio_ultimo_curso": 2024,
            "motivo_traslado": "Mejor ubicación",
            "pie": True,
            "diagnostico_pie": "Trastorno del espectro autista (TEA) leve",
            "fecha_diag_pie": date(2022, 5, 10),
            "profesional_pie": "Dra. Carmen Soto",
            "obs_pie": "Requiere apoyo en comunicación social",
            "alergias": "Ninguna conocida",
            "sistema_salud": "Isapre",
            "grupo_sanguineo": "A+",
            "enfermedades": "",
            "medicamentos": "",
            "contacto_emergencia_1": {
                "nombre": "Ana Tapia", "run": "16.543.210-K", "parentesco": "Madre",
                "telefono": "+56999998888", "telefono_alt": ""
            },
            "contacto_emergencia_2": {
                "nombre": "Luis González", "run": "14.321.654-3", "parentesco": "Padre",
                "telefono": "+56977776666", "telefono_alt": "+56955554444"
            },
            "apoderado": {
                "nombre": "Ana María", "apellido_p": "Tapia", "apellido_m": "López",
                "rut": "16.543.210-K", "telefono": "+56999998888", "email": "ana.tapia@email.cl",
                "parentesco": "Madre", "profesion": "Profesora", "lugar_trabajo": "Escuela Los Pinos",
                "direccion": "Los Pinos 456, Padre Las Casas", "nivel_educativo": 5
            },
            "apoderado_suplente": None
        },
        {
            "rut": "21.987.654-3", 
            "nombre": "Diego Andrés", 
            "apellido_p": "San Martín", 
            "apellido_m": "Araya",
            "sexo": 1,
            "nacimiento": date(2015, 1, 10),
            "residencia": "Villa Universidad 789, Temuco",
            "email_est": "",
            "fono_est": "+56944443333",
            "nacionalidad": "Chilena",
            "pais_origen": "Chile",
            "comuna": "Temuco",
            "region": "La Araucanía",
            "colegio_procedencia": "Escuela Villa Universidad",
            "comuna_colegio": "Temuco",
            "region_colegio": "La Araucanía",
            "ultimo_curso": "7º Básico",
            "anio_ultimo_curso": 2024,
            "motivo_traslado": "Recomendación familiar",
            "pie": False,
            "alergias": "Penicilina",
            "sistema_salud": "Fonasa",
            "grupo_sanguineo": "B+",
            "enfermedades": "",
            "medicamentos": "",
            "contacto_emergencia_1": {
                "nombre": "Carmen Araya", "run": "17.654.321-0", "parentesco": "Madre",
                "telefono": "+56922221111", "telefono_alt": ""
            },
            "contacto_emergencia_2": {
                "nombre": "Pedro San Martín", "run": "13.456.789-0", "parentesco": "Padre",
                "telefono": "+56900009999", "telefono_alt": ""
            },
            "apoderado": {
                "nombre": "Carmen", "apellido_p": "Araya", "apellido_m": "Fuentes",
                "rut": "17.654.321-0", "telefono": "+56922221111", "email": "carmen.araya@email.cl",
                "parentesco": "Madre", "profesion": "Contadora", "lugar_trabajo": "Servicio Impuestos Internos",
                "direccion": "Villa Universidad 789, Temuco", "nivel_educativo": 5
            },
            "apoderado_suplente": {
                "nombre": "Pedro", "apellido_p": "San Martín", "apellido_m": "Díaz",
                "rut": "13.456.789-0", "telefono": "+56900009999", "email": "",
                "parentesco": "Padre", "profesion": "Mecánico", "lugar_trabajo": "Taller San Martín",
                "direccion": "", "nivel_educativo": 2
            }
        },
        {
            "rut": "23.111.222-3", 
            "nombre": "Valentina Paz", 
            "apellido_p": "Contreras", 
            "apellido_m": "Silva",
            "sexo": 2,
            "nacimiento": date(2016, 5, 30),
            "residencia": "Camino a Labranza 321, Temuco",
            "email_est": "",
            "fono_est": "",
            "nacionalidad": "Chilena",
            "pais_origen": "Chile",
            "comuna": "Temuco",
            "region": "La Araucanía",
            "colegio_procedencia": "Escuela Labranza",
            "comuna_colegio": "Temuco",
            "region_colegio": "La Araucanía",
            "ultimo_curso": "7º Básico",
            "anio_ultimo_curso": 2024,
            "motivo_traslado": "Cambio de establecimiento",
            "pie": False,
            "alergias": "Mariscos, polvo",
            "sistema_salud": "Isapre",
            "grupo_sanguineo": "AB+",
            "enfermedades": "Rinitis alérgica",
            "medicamentos": "Loratadina según necesidad",
            "contacto_emergencia_1": {
                "nombre": "Patricia Silva", "run": "18.765.432-1", "parentesco": "Madre",
                "telefono": "+56966667777", "telefono_alt": "+56988889999"
            },
            "contacto_emergencia_2": {
                "nombre": "Jorge Contreras", "run": "15.678.901-2", "parentesco": "Padre",
                "telefono": "+56933332222", "telefono_alt": ""
            },
            "apoderado": {
                "nombre": "Patricia", "apellido_p": "Silva", "apellido_m": "Morales",
                "rut": "18.765.432-1", "telefono": "+56966667777", "email": "patricia.silva@email.cl",
                "parentesco": "Madre", "profesion": "Abogada", "lugar_trabajo": "Estudio Jurídico Silva",
                "direccion": "Camino a Labranza 321, Temuco", "nivel_educativo": 5
            },
            "apoderado_suplente": None
        },
        {
            "rut": "22.888.999-4", 
            "nombre": "Sebastián Igor", 
            "apellido_p": "Muñoz", 
            "apellido_m": "Vergara",
            "sexo": 1,
            "nacimiento": date(2015, 11, 5),
            "residencia": "Av. Pablo Neruda 555, Temuco",
            "email_est": "sebastian.munoz@ejemplo.cl",
            "fono_est": "+56911110000",
            "nacionalidad": "Chilena",
            "pais_origen": "Chile",
            "comuna": "Temuco",
            "region": "La Araucanía",
            "colegio_procedencia": "Colegio Pablo Neruda",
            "comuna_colegio": "Temuco",
            "region_colegio": "La Araucanía",
            "ultimo_curso": "8º Básico",
            "anio_ultimo_curso": 2024,
            "motivo_traslado": "Traslado por trabajo de apoderados",
            "pie": False,
            "alergias": "Ninguna",
            "sistema_salud": "Fonasa",
            "grupo_sanguineo": "O+",
            "enfermedades": "",
            "medicamentos": "",
            "contacto_emergencia_1": {
                "nombre": "Laura Vergara", "run": "19.876.543-2", "parentesco": "Madre",
                "telefono": "+56944445555", "telefono_alt": ""
            },
            "contacto_emergencia_2": {
                "nombre": "Carlos Muñoz", "run": "16.789.012-3", "parentesco": "Padre",
                "telefono": "+56922223333", "telefono_alt": "+56977778888"
            },
            "apoderado": {
                "nombre": "Laura", "apellido_p": "Vergara", "apellido_m": "Herrera",
                "rut": "19.876.543-2", "telefono": "+56944445555", "email": "laura.vergara@email.cl",
                "parentesco": "Madre", "profesion": "Ingeniera Civil", "lugar_trabajo": "Municipalidad de Temuco",
                "direccion": "Av. Pablo Neruda 555, Temuco", "nivel_educativo": 5
            },
            "apoderado_suplente": {
                "nombre": "Carlos", "apellido_p": "Muñoz", "apellido_m": "Riquelme",
                "rut": "16.789.012-3", "telefono": "+56922223333", "email": "carlos.munoz@email.cl",
                "parentesco": "Padre", "profesion": "Técnico en Redes", "lugar_trabajo": "Entel",
                "direccion": "", "nivel_educativo": 4
            }
        }
    ]

    for data in alumnos_datos:
        ident = PersonIdentifier.query.filter_by(Identifier=data["rut"], RefPersonIdentificationSystemId=51).first()
        if not ident:
            # 1. Crear persona estudiante
            persona = Person(
                FirstName=data["nombre"],
                MiddleName="",
                LastName=data["apellido_p"],
                SecondLastName=data["apellido_m"],
                RefSexId=data.get("sexo"),
                Birthdate=data.get("nacimiento")
            )
            db.session.add(persona)
            db.session.flush()

            # 2. Identificadores
            db.session.add(PersonIdentifier(
                PersonId=persona.PersonId,
                Identifier=data["rut"],
                RefPersonIdentificationSystemId=51
            ))

            # 3. Residencia
            if data.get("residencia"):
                db.session.add(PersonAddress(
                    PersonId=persona.PersonId,
                    StreetNumberAndName=data["residencia"]
                ))

            # 4. Email y teléfono del estudiante
            if data.get("email_est"):
                db.session.add(PersonEmailAddress(
                    PersonId=persona.PersonId,
                    EmailAddress=data["email_est"]
                ))
            if data.get("fono_est"):
                db.session.add(PersonTelephone(
                    PersonId=persona.PersonId,
                    TelephoneNumber=data["fono_est"]
                ))

            # 5. Matrícula en curso
            db.session.add(OrganizationPersonRole(
                OrganizationId=curso_id,
                PersonId=persona.PersonId,
                RoleId=6,
                EntryDate=date(2025, 3, 1)
            ))

             # 6. DATOS EXTENDIDOS DE MATRÍCULA
            db.session.add(EdugestStudentEnrollment(
                PersonId=persona.PersonId,
                Nacionalidad=data.get("nacionalidad"),
                PaisOrigen=data.get("pais_origen"),
                ComunaResidencia=data.get("comuna"),
                RegionResidencia=data.get("region"),
                EmailEstudiante=data.get("email_est"),
                TelefonoEstudiante=data.get("fono_est"),
                ColegioProcedencia=data.get("colegio_procedencia"),
                ComunaColegioAnterior=data.get("comuna_colegio"),
                RegionColegioAnterior=data.get("region_colegio"),
                UltimoCursoAprobado=data.get("ultimo_curso"),
                AnioUltimoCursoAprobado=data.get("anio_ultimo_curso"),
                MotivoTraslado=data.get("motivo_traslado"),
                FechaIngresoEstablecimiento=date(2025, 3, 1),
                # SEP y autorizaciones de ejemplo
                AlumnoPrioritario=False,
                AlumnoPreferente=True,
                BeneficiarioSEP=False,
                AutorizaFotografias=True,
                AutorizaRedesSociales=True,
                AutorizaSalidasPedagogicas=True,
                AutorizaTrasladoCentroAsistencial=True,
                AutorizaAtencionMedicaUrgencia=True,
                # Documentación de ejemplo
                EntregaCertificadoNacimiento=True,
                EntregaCertificadoAnualEstudios=True,
                EntregaFotocopiaRUNEstudiante=True,
                EntregaFotocopiaRUNApoderado=True,
                EntregaComprobanteDomicilio=True,
                EntregaFichaMedica=True
            ))

            # 7. CONTACTOS DE EMERGENCIA
            for i, key in enumerate(["contacto_emergencia_1", "contacto_emergencia_2"], 1):
                contacto = data.get(key)
                if contacto:
                    db.session.add(EdugestEmergencyContact(
                        PersonId=persona.PersonId,
                        Orden=i,
                        NombreCompleto=contacto["nombre"],
                        RUN=contacto.get("run"),
                        Parentesco=contacto.get("parentesco"),
                        TelefonoPrincipal=contacto.get("telefono"),
                        TelefonoAlternativo=contacto.get("telefono_alt") if contacto.get("telefono_alt") else None
                    ))

            # 8. INFORMACIÓN MÉDICA
            if data.get("alergias") or data.get("enfermedades") or data.get("medicamentos") or data.get("sistema_salud") or data.get("grupo_sanguineo"):
                db.session.add(EdugestStudentHealth(
                    PersonId=persona.PersonId,
                    GrupoSanguineo=data.get("grupo_sanguineo"),
                    SistemaSalud=data.get("sistema_salud"),
                    EnfermedadesPermanentes=data.get("enfermedades"),
                    Alergias=data.get("alergias"),
                    MedicamentosPermanentes=data.get("medicamentos")
                ))

            # 9. PIE
            if data.get("pie"):
                db.session.add(EdugestStudentPIE(
                    PersonId=persona.PersonId,
                    PertenecePIE=True,
                    DiagnosticoPIE=data.get("diagnostico_pie"),
                    FechaDiagnostico=data.get("fecha_diag_pie"),
                    ProfesionalTratante=data.get("profesional_pie"),
                    ObservacionesPIE=data.get("obs_pie")
                ))

            # 10. APODERADOS
            if data.get("apoderado"):
                crear_apoderado_completo(persona.PersonId, data["apoderado"], 0)
            if data.get("apoderado_suplente"):
                crear_apoderado_completo(persona.PersonId, data["apoderado_suplente"], 1)

            print(f"👤 {data['nombre']} matriculado con datos completos en Curso ID {curso_id}")
        else:
            print(f"ℹ️ Estudiante ya existe: {data['rut']}")

    db.session.commit()


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
with app.app_context():
    print("🚀 Iniciando siembra...")
    print("=" * 60)

    crear_jerarquia_completa()

    # Crear asignaturas para TODOS los grados
    todos_los_grados = Organization.query.filter_by(RefOrganizationTypeId=46).order_by(Organization.OrganizationId).all()
    for idx, grado in enumerate(todos_los_grados):
        asignaturas = crear_asignaturas_basicas_mineduc(grado.OrganizationId)
        if idx == 0 and asignaturas:
            crear_planificaciones(asignaturas[0])

    # Buscar el Curso 1° Básico A (Tipo 21) para matricular alumnos de prueba
    grado_1basico = Organization.query.filter_by(Name="1º Básico", RefOrganizationTypeId=46).first()
    if grado_1basico:
        curso_1A = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            Organization.ShortName == 'A',
            OrganizationRelationship.ParentOrganizationId == grado_1basico.OrganizationId
        ).first()

        if curso_1A:
            crear_alumnos_prueba(curso_1A.OrganizationId)
        else:
            print("❌ No se encontró el curso 1° Básico A")
    else:
        print("❌ No se encontró el grado 1° Básico")

    print("\n" + "=" * 60)
    print("🎉 ¡Siembra completada!")