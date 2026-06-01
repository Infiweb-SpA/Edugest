-- Activar el soporte de llaves foráneas en SQLite
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 0. TABLAS BASE ESENCIALES DEL MINEDUC (REQUERIDAS PARA RELACIONES)
-- ============================================================================

CREATE TABLE Person (
    PersonId INTEGER PRIMARY KEY AUTOINCREMENT,
    FirstName TEXT NOT NULL,
    MiddleName TEXT,
    LastName TEXT NOT NULL,
    SecondLastName TEXT,
    RefSexId INTEGER
);

CREATE TABLE Organization (
    OrganizationId INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    ShortName TEXT,
    RefOrganizationTypeId INTEGER NOT NULL -- 10=Colegio, 21=Curso, 22=Asignatura
);

-- ============================================================================
-- MÓDULO A: CONFIGURACIÓN Y MATRIZ DE PERMISOS (ADMINISTRADOR)
-- ============================================================================

-- Catálogo global de módulos del sistema
CREATE TABLE edugest_module (
    ModuleId INTEGER PRIMARY KEY AUTOINCREMENT,
    ModuleName TEXT NOT NULL UNIQUE,
    IsEnabled INTEGER NOT NULL DEFAULT 1 CHECK (IsEnabled IN (0, 1)) -- 0 = Falso, 1 = Verdadero
);

-- Matriz de accesos granulares por Rol
CREATE TABLE edugest_role_permission (
    PermissionId INTEGER PRIMARY KEY AUTOINCREMENT,
    RoleId INTEGER NOT NULL, -- Hace match conceptual con el RoleId de la EDE (ej: 6=Estudiante)
    ModuleId INTEGER NOT NULL,
    PermissionLevel INTEGER NOT NULL CHECK (PermissionLevel IN (0, 1, 2)), -- 0=No acceso, 1=Lectura, 2=Escritura
    FOREIGN KEY (ModuleId) REFERENCES edugest_module(ModuleId) ON DELETE CASCADE
);

-- ============================================================================
-- MÓDULO B: PLANIFICACIÓN CURRICULAR AVANZADA (PROFESOR / LIBRO DIGITAL)
-- ============================================================================

-- Planificaciones anuales o por unidad didáctica
CREATE TABLE edugest_curriculum_plan (
    PlanId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrganizationId INTEGER NOT NULL, -- Relación directa a la Asignatura/Sección (Tipo 22)
    UnitTitle TEXT NOT NULL,
    LearningObjectives TEXT,
    EstimatedClasses INTEGER,
    FOREIGN KEY (OrganizationId) REFERENCES Organization(OrganizationId) ON DELETE CASCADE
);

-- Extensión del Leccionario Oficial MINEDUC vinculado a la Planificación de Edugest
CREATE TABLE OrganizationCalendarSession (
    OrganizationCalendarSessionId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrganizationId INTEGER NOT NULL, -- Asignatura (Tipo 22)
    BeginDate TEXT NOT NULL,         -- Formato ISO8601 YYYY-MM-DD
    EndDate TEXT NOT NULL,           -- Formato ISO8601 YYYY-MM-DD
    SessionStartTime TEXT,          -- Formato HH:MM:SS
    SessionEndTime TEXT,            -- Formato HH:MM:SS
    Description TEXT,               -- Contenido dictado del Leccionario
    MarkingTermIndicator INTEGER DEFAULT 0 CHECK (MarkingTermIndicator IN (0, 1)),   -- Control de asistencia tomado
    SchedulingTermIndicator INTEGER DEFAULT 0 CHECK (SchedulingTermIndicator IN (0, 1)), -- Control de evaluación realizada
    PlanId INTEGER,                 -- EXTENSIÓN EDUGEST: Enlace a la planificación curricular (Nullable)
    FOREIGN KEY (OrganizationId) REFERENCES Organization(OrganizationId) ON DELETE CASCADE,
    FOREIGN KEY (PlanId) REFERENCES edugest_curriculum_plan(PlanId) ON DELETE SET NULL
);

-- ============================================================================
-- DATA SEMILLA PARA PRUEBAS INICIALES
-- ============================================================================

-- Insertar Módulos Core
INSERT INTO edugest_module (ModuleName, IsEnabled) VALUES 
('Libro Digital', 1),
('Evaluaciones', 1),
('Biblioteca', 1),
('Comunicación', 1);

-- Configuración de Permisos por Defecto
-- Profesor (Nivel 2 en todos los módulos)
INSERT INTO edugest_role_permission (RoleId, ModuleId, PermissionLevel) VALUES 
(3, 1, 2), (3, 2, 2), (3, 3, 2), (3, 4, 2); -- Asumiendo RoleId 3 para Profesor

-- Estudiante (Nivel 1 en todos los módulos)
INSERT INTO edugest_role_permission (RoleId, ModuleId, PermissionLevel) VALUES 
(6, 1, 1), (6, 2, 1), (6, 3, 1), (6, 4, 1); -- RoleId 6 estándar MINEDUC