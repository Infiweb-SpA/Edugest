from app import create_app
from app.database import db
from app.models import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationIdentifier, OrganizationPersonRole,
    EdugestCurriculumPlan, EdugestModule
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


def crear_alumnos_prueba(curso_id):
    """Crea 5 alumnos ficticios y los matricula en el CURSO (Tipo 21)"""
    alumnos_datos = [
        {"rut": "21.345.678-9", "nombre": "Juan Carlos", "apellido_p": "Pérez", "apellido_m": "Muñoz"},
        {"rut": "22.456.789-K", "nombre": "María José", "apellido_p": "González", "apellido_m": "Tapia"},
        {"rut": "21.987.654-3", "nombre": "Diego Andrés", "apellido_p": "San Martín", "apellido_m": "Araya"},
        {"rut": "23.111.222-3", "nombre": "Valentina Paz", "apellido_p": "Contreras", "apellido_m": "Silva"},
        {"rut": "22.888.999-4", "nombre": "Sebastián Igor", "apellido_p": "Muñoz", "apellido_m": "Vergara"}
    ]

    for data in alumnos_datos:
        ident = PersonIdentifier.query.filter_by(Identifier=data["rut"], RefPersonIdentificationSystemId=51).first()
        if not ident:
            persona = Person(
                FirstName=data["nombre"],
                MiddleName="",
                LastName=data["apellido_p"],
                SecondLastName=data["apellido_m"]
            )
            db.session.add(persona)
            db.session.flush()

            db.session.add(PersonIdentifier(
                PersonId=persona.PersonId,
                Identifier=data["rut"],
                RefPersonIdentificationSystemId=51
            ))

            # MATRICULA EN EL CURSO (Tipo 21), NO EN LA ASIGNATURA
            db.session.add(OrganizationPersonRole(
                OrganizationId=curso_id,
                PersonId=persona.PersonId,
                RoleId=6
            ))
            print(f"👤 {data['nombre']} matriculado en Curso ID {curso_id}")
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