-- MIGRACIÓN V2: Extensión Edugest (Grados, Unidades Curriculares y Asistencia Granular)

-- Tabla para Habilitar/Deshabilitar Grados
CREATE TABLE IF NOT EXISTS edugest_organization_config (
    ConfigId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrganizationId INTEGER NOT NULL UNIQUE,
    IsActive BOOLEAN NOT NULL DEFAULT 1,
    FOREIGN KEY(OrganizationId) REFERENCES Organization(OrganizationId) ON DELETE CASCADE
);

-- Tabla para CRUD de Unidades
CREATE TABLE IF NOT EXISTS edugest_curriculum_plan (
    PlanId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrganizationId INTEGER NOT NULL,
    UnitTitle VARCHAR(255) NOT NULL,
    Contenido TEXT,
    Actividad TEXT,
    DetallesActividad TEXT,
    Objetivo TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(OrganizationId) REFERENCES Organization(OrganizationId) ON DELETE CASCADE
);

-- Tabla para Asistencia por Bloque Horario (Ej: 08:00 a 10:00)
CREATE TABLE IF NOT EXISTS edugest_session_attendance (
    SessionAttendanceId INTEGER PRIMARY KEY AUTOINCREMENT,
    OrganizationCalendarSessionId INTEGER NOT NULL,
    OrganizationPersonRoleId INTEGER NOT NULL,
    RefAttendanceStatusId INTEGER NOT NULL,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(OrganizationCalendarSessionId) REFERENCES OrganizationCalendarSession(OrganizationCalendarSessionId) ON DELETE CASCADE,
    FOREIGN KEY(OrganizationPersonRoleId) REFERENCES OrganizationPersonRole(OrganizationPersonRoleId) ON DELETE CASCADE
);