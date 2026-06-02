from app import create_app
from app.database import db
from app.models import (
    Person, PersonIdentifier, Organization,
    OrganizationPersonRole, EdugestCurriculumPlan, EdugestModule
)

app = create_app()

with app.app_context():
    print("🚀 Iniciando siembra de datos de prueba para Edugest...")

    # ============================================================
    # 0. SEMILLA DE MÓDULOS DEL SISTEMA (incluye Matrícula)
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
        print("✅ Módulos base creados (Libro Digital, Evaluaciones, Biblioteca CRA, Comunicaciones, Matrícula).")
    else:
        # Si ya existen módulos pero falta Matrícula, la creamos individualmente
        modulo_matricula = EdugestModule.query.filter_by(ModuleName="Matrícula").first()
        if not modulo_matricula:
            db.session.add(EdugestModule(ModuleName="Matrícula", IsEnabled=True))
            db.session.commit()
            print("✅ Módulo Matrícula agregado al catálogo existente.")
        else:
            print("ℹ️ El módulo Matrícula ya existe en el catálogo.")

    # ============================================================
    # 1. Crear Asignatura de prueba (RefOrganizationTypeId=22)
    # ============================================================
    asignatura = Organization.query.filter_by(Name="Matemáticas - 1º Medio", RefOrganizationTypeId=22).first()
    if not asignatura:
        asignatura = Organization(
            Name="Matemáticas - 1º Medio",
            ShortName="MAT-1M",
            RefOrganizationTypeId=22
        )
        db.session.add(asignatura)
        db.session.flush()
        print(f"✅ Asignatura creada: {asignatura.Name}")
    else:
        print(f"ℹ️ La asignatura ya existe: {asignatura.Name}")

    # ============================================================
    # 2. Crear Planificaciones Curriculares asociadas
    # ============================================================
    if not EdugestCurriculumPlan.query.filter_by(OrganizationId=asignatura.OrganizationId).first():
        unidades = [
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, UnitTitle="Unidad 1: Números racionales y potencias"),
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, UnitTitle="Unidad 2: Álgebra y funciones lineales"),
            EdugestCurriculumPlan(OrganizationId=asignatura.OrganizationId, UnitTitle="Unidad 3: Geometría y Teorema de Pitágoras")
        ]
        db.session.add_all(unidades)
        print("✅ Unidades de planificación curricular añadidas.")

    # ============================================================
    # 3. Datos de los 5 Alumnos Ficticios
    # ============================================================
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
            print(f"👤 Estudiante matriculado: {data['nombre']} {data['apellido_p']} (RUT: {data['rut']})")
        else:
            print(f"ℹ️ El estudiante con RUT {data['rut']} ya se encuentra en el sistema.")

    db.session.commit()
    print("🎉 ¡Proceso de siembra completado con éxito!")