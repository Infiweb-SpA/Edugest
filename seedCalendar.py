"""
seedCalendar.py - Datos de prueba para el módulo Calendario Académico
Ejecutar después de seed.py: python seedCalendar.py
"""
from app import create_app
from app.database import db
from app.models.mineduc import Organization, OrganizationRelationship
from app.models.edugest import EdugestModule, EdugestRolePermission
from app.models.EdugestCalendar import EdugestCalendarEvent
from datetime import date

app = create_app()

with app.app_context():
    print("📅 Iniciando siembra del Calendario Académico...")
    print("=" * 60)

    # ================================================================
    # 1. ASEGURAR QUE EL MÓDULO "Calendario" EXISTA
    # ================================================================
    modulo_cal = EdugestModule.query.filter_by(ModuleName='Calendario').first()
    if not modulo_cal:
        modulo_cal = EdugestModule(ModuleName='Calendario', IsEnabled=True)
        db.session.add(modulo_cal)
        db.session.commit()
        print("✅ Módulo 'Calendario' creado.")
    else:
        print("ℹ️ Módulo 'Calendario' ya existe.")

    # ================================================================
    # 2. ASIGNAR PERMISOS POR DEFECTO A ROLES EXISTENTES
    # ================================================================
    # RolId 3 = Profesor (nivel 2: lectura y escritura)
    # RolId 5 = Apoderado (nivel 1: solo lectura)
    # RolId 6 = Alumno (nivel 1: solo lectura)
    roles_permisos = {3: 2, 5: 1, 6: 1}
    for role_id, nivel in roles_permisos.items():
        existente = EdugestRolePermission.query.filter_by(
            RoleId=role_id, ModuleId=modulo_cal.ModuleId
        ).first()
        if not existente:
            db.session.add(EdugestRolePermission(
                RoleId=role_id,
                ModuleId=modulo_cal.ModuleId,
                PermissionLevel=nivel
            ))
            print(f"   ✅ Permiso nivel {nivel} asignado a RolId {role_id}")
        else:
            print(f"   ℹ️ Permiso ya existe para RolId {role_id}")

    db.session.commit()

    # ================================================================
    # 3. BUSCAR ORGANIZACIONES EXISTENTES PARA EVENTOS DIRIGIDOS
    # ================================================================
    grado_1basico = Organization.query.filter_by(
        Name="1º Básico", RefOrganizationTypeId=46
    ).first()

    # Buscar curso 1° Básico A
    curso_1A = None
    if grado_1basico:
        curso_1A = Organization.query.join(
            OrganizationRelationship,
            Organization.OrganizationId == OrganizationRelationship.OrganizationId
        ).filter(
            Organization.RefOrganizationTypeId == 21,
            Organization.ShortName == 'A',
            OrganizationRelationship.ParentOrganizationId == grado_1basico.OrganizationId
        ).first()

    # Buscar asignaturas
    asig_matematica = Organization.query.filter_by(
        Name="Matemática", RefOrganizationTypeId=22
    ).first()
    asig_lenguaje = Organization.query.filter_by(
        Name="Lenguaje y Comunicación", RefOrganizationTypeId=22
    ).first()
    asig_ciencias = Organization.query.filter_by(
        Name="Ciencias Naturales", RefOrganizationTypeId=22
    ).first()
    asig_historia = Organization.query.filter_by(
        Name="Historia", RefOrganizationTypeId=22
    ).first()

    # ================================================================
    # 4. CREAR EVENTOS DE PRUEBA
    # ================================================================
    eventos_a_crear = []

    # --- EVENTOS GLOBALES (todo el establecimiento) ---
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Fiestas Patrias - Feriado",
        Description="Semana de celebración por las Fiestas Patrias chilenas. El establecimiento permanecerá cerrado.",
        EventDate=date(2026, 9, 18),
        EventType="Feriado",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Fiestas Patrias - Feriado",
        Description="Segundo día de Fiestas Patrias.",
        EventDate=date(2026, 9, 19),
        EventType="Feriado",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Día del Deporte Escolar",
        Description="Jornada deportiva interna con actividades recreativas y competencias entre cursos.",
        EventDate=date(2026, 7, 18),
        EventType="ActividadExtracurricular",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Reunión General de Apoderados",
        Description="Reunión informativa semestral para todos los apoderados del establecimiento. Sala multiuso a las 18:00 hrs.",
        EventDate=date(2026, 7, 25),
        EventType="Reunion",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Ceremonia de Graduación",
        Description="Ceremonia de graduación de 4° Medio. Gimnasio del establecimiento.",
        EventDate=date(2026, 12, 5),
        EventType="ActividadExtracurricular",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Jornada de Integración",
        Description="Actividades de integración y convivencia escolar para todos los cursos.",
        EventDate=date(2026, 8, 14),
        EventType="ActividadExtracurricular",
        TargetOrganizationId=None
    ))

    # --- EVENTOS DIRIGIDOS A GRADOS ---
    if grado_1basico:
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Vacunación Influenza - 1° Básico",
            Description="Vacunación contra la influenza para estudiantes de 1° Básico. Sala de enfermería.",
            EventDate=date(2026, 7, 22),
            EventType="Vacunacion",
            TargetOrganizationId=grado_1basico.OrganizationId
        ))
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Feria de Ciencias - 1° Básico",
            Description="Presentación de proyectos científicos de los estudiantes de 1° Básico.",
            EventDate=date(2026, 8, 7),
            EventType="Taller",
            TargetOrganizationId=grado_1basico.OrganizationId
        ))

    # --- EVENTOS DIRIGIDOS A CURSOS ---
    if curso_1A:
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Taller de Lectura - 1°A",
            Description="Taller de fomento lector con la bibliotecaria del establecimiento.",
            EventDate=date(2026, 7, 15),
            EventType="Taller",
            TargetOrganizationId=curso_1A.OrganizationId
        ))

    # --- EVENTOS DIRIGIDOS A ASIGNATURAS ---
    if asig_matematica:
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Evaluación Sumativa - Matemática",
            Description="Prueba parcial de la Unidad 1: Números racionales y potencias.",
            EventDate=date(2026, 7, 10),
            EventType="Evaluacion",
            TargetOrganizationId=asig_matematica.OrganizationId
        ))
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Control de Matemática",
            Description="Control breve de contenidos de la semana.",
            EventDate=date(2026, 7, 31),
            EventType="Evaluacion",
            TargetOrganizationId=asig_matematica.OrganizationId
        ))

    if asig_lenguaje:
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Entrega Proyecto Lenguaje",
            Description="Fecha límite para la entrega del proyecto de comprensión lectora.",
            EventDate=date(2026, 7, 28),
            EventType="Evaluacion",
            TargetOrganizationId=asig_lenguaje.OrganizationId
        ))

    if asig_ciencias:
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Taller de Laboratorio - Ciencias",
            Description="Práctica de laboratorio: ecosistemas y cadena alimentaria.",
            EventDate=date(2026, 8, 4),
            EventType="Taller",
            TargetOrganizationId=asig_ciencias.OrganizationId
        ))

    if asig_historia:
        eventos_a_crear.append(EdugestCalendarEvent(
            Title="Evaluación Historia - Independencia",
            Description="Evaluación de la unidad sobre procesos de independencia en América Latina.",
            EventDate=date(2026, 8, 11),
            EventType="Evaluacion",
            TargetOrganizationId=asig_historia.OrganizationId
        ))

    # --- MÁS EVENTOS PARA AGOSTO Y SEPTIEMBRE ---
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Simulacro de Emergencia",
        Description="Simulacro de evacuación sísmica para todo el establecimiento.",
        EventDate=date(2026, 8, 20),
        EventType="Otro",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Día del Profesor",
        Description="Homenaje al cuerpo docente del establecimiento.",
        EventDate=date(2026, 10, 16),
        EventType="Feriado",
        TargetOrganizationId=None
    ))
    eventos_a_crear.append(EdugestCalendarEvent(
        Title="Reunión de Apoderados - 1° Básico",
        Description="Reunión específica para apoderados de 1° Básico. Entrega de informes.",
        EventDate=date(2026, 8, 28),
        EventType="Reunion",
        TargetOrganizationId=grado_1basico.OrganizationId if grado_1basico else None
    ))

    # ================================================================
    # 5. INSERTAR EVENTOS
    # ================================================================
    creados = 0
    for evento in eventos_a_crear:
        # Evitar duplicados verificando título + fecha
        existente = EdugestCalendarEvent.query.filter_by(
            Title=evento.Title, EventDate=evento.EventDate
        ).first()
        if not existente:
            db.session.add(evento)
            creados += 1
            print(f"   ✅ {evento.Title} - {evento.EventDate}")
        else:
            print(f"   ℹ️ Ya existe: {evento.Title} - {evento.EventDate}")

    db.session.commit()

    print(f"\n{'=' * 60}")
    print(f"🎉 Siembra del calendario completada. {creados} eventos nuevos creados.")