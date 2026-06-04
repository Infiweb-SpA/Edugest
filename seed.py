from app import create_app
from app.database import db
from app.models import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationIdentifier, OrganizationPersonRole,
    EdugestCurriculumPlan, EdugestModule
)

app = create_app()


def crear_jerarquia_completa():
    """
    Crea la jerarquía completa MINEDUC para un establecimiento de prueba.

    Jerarquía: RBD(10) → Modalidad(38) → Jornada(39) → Nivel(40) → Rama(41) 
               → Sector(42) → Especialidad(43) → TipoCurso(44) → CódigoEnseñanza(45) 
               → Grado(46) → Curso(21)
    """

    # ============================================================
    # 0. MÓDULOS DEL SISTEMA
    # ============================================================
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

    # ============================================================
    # 1. ESTABLECIMIENTO (RBD)
    # ============================================================
    rbd = Organization.query.filter_by(ShortName="RBD09599", RefOrganizationTypeId=10).first()
    if not rbd:
        rbd = Organization(
            Name="Liceo Bicentenario Temuco",
            ShortName="RBD09599",
            RefOrganizationTypeId=10
        )
        db.session.add(rbd)
        db.session.flush()

        # Identificador RBD
        db.session.add(OrganizationIdentifier(
            OrganizationId=rbd.OrganizationId,
            Identifier="09599",
            RefOrganizationIdentificationSystemId=1  # RBD
        ))
        print(f"✅ Establecimiento creado: {rbd.Name} ({rbd.ShortName})")
    else:
        print(f"ℹ️ Establecimiento ya existe: {rbd.Name}")

    # ============================================================
    # 2. MODALIDAD (Tipo 38)
    # ============================================================
    modalidad = Organization.query.filter_by(Name="Regular", RefOrganizationTypeId=38).first()
    if not modalidad:
        modalidad = Organization(Name="Regular", RefOrganizationTypeId=38)
        db.session.add(modalidad)
        db.session.flush()
        db.session.add(OrganizationRelationship(
            OrganizationId=modalidad.OrganizationId,
            ParentOrganizationId=rbd.OrganizationId
        ))
        print("✅ Modalidad creada: Regular")

    # ============================================================
    # 3. JORNADA (Tipo 39)
    # ============================================================
    jornada = Organization.query.filter_by(Name="Mañana", RefOrganizationTypeId=39).first()
    if not jornada:
        jornada = Organization(Name="Mañana", RefOrganizationTypeId=39)
        db.session.add(jornada)
        db.session.flush()
        db.session.add(OrganizationRelationship(
            OrganizationId=jornada.OrganizationId,
            ParentOrganizationId=modalidad.OrganizationId
        ))
        print("✅ Jornada creada: Mañana")

    # ============================================================
    # 4. NIVEL (Tipo 40) - Enseñanza Básica y Media
    # ============================================================
    niveles_data = [
        ("02", "Enseñanza Básica Niños"),
        ("05", "Enseñanza Media Humanístico Científica Jóvenes")
    ]
    niveles = {}
    for codigo, nombre in niveles_data:
        nivel = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=40).first()
        if not nivel:
            nivel = Organization(Name=nombre, ShortName=codigo, RefOrganizationTypeId=40)
            db.session.add(nivel)
            db.session.flush()
            db.session.add(OrganizationRelationship(
                OrganizationId=nivel.OrganizationId,
                ParentOrganizationId=jornada.OrganizationId
            ))
            print(f"✅ Nivel creado: {nombre}")
        niveles[codigo] = nivel

    # ============================================================
    # 5. RAMA (Tipo 41)
    # ============================================================
        # 5. RAMA (Tipo 41) — UNA por cada nivel
    ramas = {}
    
    # Rama para Básica
    rama_basica = Organization.query.filter_by(Name="Educación General", RefOrganizationTypeId=41).first()
    if not rama_basica:
        rama_basica = Organization(Name="Educación General", RefOrganizationTypeId=41)
        db.session.add(rama_basica)
        db.session.flush()
        print("✅ Rama creada: Educación General")
    ramas["02"] = rama_basica
    
    # Rama para Media
    rama_media = Organization.query.filter_by(Name="Humanístico-Científica", RefOrganizationTypeId=41).first()
    if not rama_media:
        rama_media = Organization(Name="Humanístico-Científica", RefOrganizationTypeId=41)
        db.session.add(rama_media)
        db.session.flush()
        print("✅ Rama creada: Humanístico-Científica")
    ramas["05"] = rama_media

    # Relacionar cada rama con SU nivel
    db.session.add(OrganizationRelationship(
        OrganizationId=rama_basica.OrganizationId,
        ParentOrganizationId=niveles["02"].OrganizationId
    ))
    db.session.add(OrganizationRelationship(
        OrganizationId=rama_media.OrganizationId,
        ParentOrganizationId=niveles["05"].OrganizationId
    ))

    # ============================================================
    # 6. SECTOR (Tipo 42)
    # ============================================================
        # 6. SECTOR (Tipo 42) — UNO por cada rama
    sectores = {}
    
    for codigo_nivel, rama in ramas.items():
        sector_nombre = f"Sin Sector {codigo_nivel}"
        sector = Organization.query.filter_by(Name=sector_nombre, RefOrganizationTypeId=42).first()
        if not sector:
            sector = Organization(Name=sector_nombre, RefOrganizationTypeId=42)
            db.session.add(sector)
            db.session.flush()
            db.session.add(OrganizationRelationship(
                OrganizationId=sector.OrganizationId,
                ParentOrganizationId=rama.OrganizationId
            ))
            print(f"✅ Sector creado: {sector_nombre}")
        sectores[codigo_nivel] = sector

    # ============================================================
    # 7. ESPECIALIDAD (Tipo 43)
    # ============================================================
        # 7. ESPECIALIDAD (Tipo 43) — UNA por cada sector
    especialidades = {}
    
    for codigo_nivel, sector in sectores.items():
        esp_nombre = f"Sin Especialidad {codigo_nivel}"
        especialidad = Organization.query.filter_by(Name=esp_nombre, RefOrganizationTypeId=43).first()
        if not especialidad:
            especialidad = Organization(Name=esp_nombre, RefOrganizationTypeId=43)
            db.session.add(especialidad)
            db.session.flush()
            db.session.add(OrganizationRelationship(
                OrganizationId=especialidad.OrganizationId,
                ParentOrganizationId=sector.OrganizationId
            ))
            print(f"✅ Especialidad creada: {esp_nombre}")
        especialidades[codigo_nivel] = especialidad

    # ============================================================
    # 8. TIPO DE CURSO (Tipo 44)
    # ============================================================
        # 8. TIPO DE CURSO (Tipo 44) — UNO por cada especialidad
    tipos_curso = {}
    
    for codigo_nivel, especialidad in especialidades.items():
        tipo_nombre = f"Simple {codigo_nivel}"
        tipo_curso = Organization.query.filter_by(Name=tipo_nombre, RefOrganizationTypeId=44).first()
        if not tipo_curso:
            tipo_curso = Organization(Name=tipo_nombre, RefOrganizationTypeId=44)
            db.session.add(tipo_curso)
            db.session.flush()
            db.session.add(OrganizationRelationship(
                OrganizationId=tipo_curso.OrganizationId,
                ParentOrganizationId=especialidad.OrganizationId
            ))
            print(f"✅ Tipo de curso creado: {tipo_nombre}")
        tipos_curso[codigo_nivel] = tipo_curso

    # ============================================================
    # 9. CÓDIGO DE ENSEÑANZA (Tipo 45)
    # ============================================================
        # 9. CÓDIGO DE ENSEÑANZA (Tipo 45) — UNO por cada tipo de curso
    codigos = {}
    
    codigo_data = {
        "02": ("110", "Básica Niños"),
        "05": ("310", "Media HC Jóvenes")
    }
    
    for codigo_nivel, tipo_curso in tipos_curso.items():
        codigo_val, codigo_short = codigo_data[codigo_nivel]
        codigo = Organization.query.filter_by(Name=codigo_val, RefOrganizationTypeId=45).first()
        if not codigo:
            codigo = Organization(Name=codigo_val, ShortName=codigo_short, RefOrganizationTypeId=45)
            db.session.add(codigo)
            db.session.flush()
            db.session.add(OrganizationRelationship(
                OrganizationId=codigo.OrganizationId,
                ParentOrganizationId=tipo_curso.OrganizationId
            ))
            print(f"✅ Código enseñanza creado: {codigo_val} ({codigo_short})")
        codigos[codigo_nivel] = codigo

    # ============================================================
    # 10. GRADOS (Tipo 46) - 1° a 8° Básico, 1° a 4° Medio
    # ============================================================
        # 10. GRADOS (Tipo 46)
    grados_data = {
        "02": ["1º Básico", "2º Básico", "3º Básico", "4º Básico",
               "5º Básico", "6º Básico", "7º Básico", "8º Básico"],
        "05": ["1º Medio", "2º Medio", "3º Medio", "4º Medio"]
    }
    
    grados_creados = {}
    
    for codigo_nivel, lista_grados in grados_data.items():
        for grado_nombre in lista_grados:
            grado = Organization.query.filter_by(Name=grado_nombre, RefOrganizationTypeId=46).first()
            if not grado:
                grado = Organization(Name=grado_nombre, RefOrganizationTypeId=46)
                db.session.add(grado)
                db.session.flush()
                db.session.add(OrganizationRelationship(
                    OrganizationId=grado.OrganizationId,
                    ParentOrganizationId=codigos[codigo_nivel].OrganizationId
                ))
                print(f"✅ Grado creado: {grado_nombre}")
            grados_creados[grado_nombre] = grado

    # ============================================================
    # 11. CURSOS CON LETRAS (Tipo 21)
    # ============================================================
        import string
    letras = list(string.ascii_uppercase)  # ['A', 'B', 'C', ..., 'Z']
    cursos_creados = []

    for grado_nombre, grado in grados_creados.items():
        for letra in letras:
            curso_nombre = f"{grado_nombre} {letra}"
            curso = Organization.query.filter_by(Name=curso_nombre, RefOrganizationTypeId=21).first()
            if not curso:
                curso = Organization(
                    Name=curso_nombre,
                    ShortName=letra,
                    RefOrganizationTypeId=21
                )
                db.session.add(curso)
                db.session.flush()
                db.session.add(OrganizationRelationship(
                    OrganizationId=curso.OrganizationId,
                    ParentOrganizationId=grado.OrganizationId
                ))
                print(f"✅ Curso creado: {curso_nombre}")
                cursos_creados.append(curso_nombre)

    db.session.commit()
    print(f"\n🎉 Jerarquía completa creada. Total cursos: {len(cursos_creados)}")
    return True


# seed.py

def crear_asignaturas_basicas_mineduc(grado_id):
    """
    Crea asignaturas (Tipo 22) y las vincula al grado (Tipo 46) 
    mediante OrganizationRelationship.
    """
    asignaturas_nombres = ["Lenguaje y Comunicación", "Matemática", "Historia", "Ciencias Naturales"]
    creadas = []
    
    for nombre in asignaturas_nombres:
        # 1. Crear la asignatura
        asig = Organization.query.filter_by(Name=nombre, RefOrganizationTypeId=22).first()
        if not asig:
            asig = Organization(Name=nombre, ShortName=nombre[:3].upper(), RefOrganizationTypeId=22)
            db.session.add(asig)
            db.session.flush()
            
            # 2. Vincularla al Grado
            db.session.add(OrganizationRelationship(
                OrganizationId=asig.OrganizationId,
                ParentOrganizationId=grado_id
            ))
            creadas.append(asig)
            print(f"✅ Asignatura creada y vinculada: {nombre}")
    
    db.session.commit()
    return creadas


def crear_planificaciones(asignatura):
    """Crea planificaciones curriculares"""
    if not EdugestCurriculumPlan.query.filter_by(OrganizationId=asignatura.OrganizationId).first():
        unidades = [
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, 
                                  UnitTitle="Unidad 1: Números racionales y potencias"),
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, 
                                  UnitTitle="Unidad 2: Álgebra y funciones lineales"),
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, 
                                  UnitTitle="Unidad 3: Geometría y Teorema de Pitágoras")
        ]
        db.session.add_all(unidades)
        db.session.commit()
        print("✅ Planificaciones curriculares creadas.")


def crear_alumnos_prueba(asignatura):
    """Crea 5 alumnos ficticios"""
    alumnos_datos = [
        {"rut": "21.345.678-9", "nombre": "Juan Carlos", "apellido_p": "Pérez", "apellido_m": "Muñoz"},
        {"rut": "22.456.789-K", "nombre": "María José", "apellido_p": "González", "apellido_m": "Tapia"},
        {"rut": "21.987.654-3", "nombre": "Diego Andrés", "apellido_p": "San Martín", "apellido_m": "Araya"},
        {"rut": "23.111.222-3", "nombre": "Valentina Paz", "apellido_p": "Contreras", "apellido_m": "Silva"},
        {"rut": "22.888.999-4", "nombre": "Sebastián Igor", "apellido_p": "Muñoz", "apellido_m": "Vergara"}
    ]

    for data in alumnos_datos:
        identificador_existente = PersonIdentifier.query.filter_by(
            Identifier=data["rut"],
            RefPersonIdentificationSystemId=51
        ).first()

        if not identificador_existente:
            nueva_persona = Person(
                FirstName=data["nombre"],
                MiddleName="",
                LastName=data["apellido_p"],
                SecondLastName=data["apellido_m"]
            )
            db.session.add(nueva_persona)
            db.session.flush()

            nuevo_rut = PersonIdentifier(
                PersonId=nueva_persona.PersonId,
                Identifier=data["rut"],
                RefPersonIdentificationSystemId=51
            )
            db.session.add(nuevo_rut)

            nuevo_rol = OrganizationPersonRole(
                OrganizationId=asignatura.OrganizationId,
                PersonId=nueva_persona.PersonId,
                RoleId=6
            )
            db.session.add(nuevo_rol)
            print(f"👤 Estudiante matriculado: {data['nombre']} {data['apellido_p']}")
        else:
            print(f"ℹ️ Estudiante ya existe: {data['rut']}")

    db.session.commit()


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================
with app.app_context():
    print("🚀 Iniciando siembra de datos de prueba para Edugest...")
    print("=" * 60)

    # 1. Jerarquía completa
    crear_jerarquia_completa()

    # 2. Obtener UN grado (Tipo 46) para vincular asignaturas
    grado_prueba = Organization.query.filter_by(RefOrganizationTypeId=46).first()

    if grado_prueba:
        # 3. Crear asignaturas vinculadas al GRADO (Tipo 46), no al curso
        asignaturas = crear_asignaturas_basicas_mineduc(grado_prueba.OrganizationId)
        print(f"✅ Asignaturas creadas y vinculadas al grado: {grado_prueba.Name}")
    else:
        print("❌ No se encontró un Grado para vincular las asignaturas.")
        asignaturas = []

    # 4. Tomar la primera asignatura para planificaciones y alumnos de prueba
    if asignaturas:
        asignatura_prueba = asignaturas[0]

        # Planificaciones
        crear_planificaciones(asignatura_prueba)

        # Alumnos ficticios
        crear_alumnos_prueba(asignatura_prueba)

    print("\n" + "=" * 60)
    print("🎉 ¡Proceso de siembra completado con éxito!")