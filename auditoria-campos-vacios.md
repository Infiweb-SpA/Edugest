# Informe de Auditoría: Campos Vacíos y Tablas Incompletas en `edugest.db`

**Fecha:** Julio 2026  
**Motor de BD:** SQLite (`edugest.db`)  
**Estándar:** Modelo EDE MINEDUC / CEDS y Tablas de Extensión Edugest  

---

## 1. Resumen Ejecutivo

El presente diagnóstico detalla los campos nulos, cadenas vacías y tablas sin registros detectados en la base de datos `edugest.db`. El análisis se divide en dos grandes capas:

1. **Capa Estándar MINEDUC (EDE):** Tablas de la estructura oficial chilena.
2. **Capa de Extensión Edugest (`edugest_*`):** Tablas específicas de la aplicación para fichas de matrícula extendidas, módulos pedagógicos y funcionales.

---

## 2. Tablas Estándar MINEDUC (EDE) con Registros Parciales

A continuación se detallan las tablas oficiales que poseen registros, pero cuentan con atributos sin poblar ($NULL$ o cadenas vacías):

### 2.1. Tabla `Person` (Total Registros: 20)
Almacena la identidad de alumnos, apoderados, docentes y personal del establecimiento.

| Campo Vacío | Incompletitud | % Vacío | Descripción del Campo | Fuente u Origen del Dato |
| :--- | :---: | :---: | :--- | :--- |
| `MiddleName` | 18 / 20 | 90.0% | Segundo nombre de la persona. | Input "Segundo Nombre" en el Formulario de Matrícula / Registro de Usuario. *(Legítimo que quede vacío si la persona no posee)*. |
| `RefSexId` | 11 / 20 | 55.0% | Sexo biológico (Catálogo MINEDUC: `1` Masculino, `2` Femenino). | Certificado de Nacimiento / Cédula en el módulo de Matrícula. |
| `Birthdate` | 11 / 20 | 55.0% | Fecha de nacimiento (`AAAA-MM-DD`). | Ficha de Matrícula / Cédula de Identidad. |
| `RefTribalAffiliationId` | 20 / 20 | 100.0% | Código oficial de pertenencia a pueblo originario/etnia indígena. | Declaración del apoderado/estudiante en el proceso de matrícula o ficha socioeconómica. |

---

### 2.2. Tabla `Organization` (Total Registros: 387)
Estructura jerárquica del establecimiento (RBD, Modalidad, Niveles, Grados, Cursos y Asignaturas).

| Campo Vacío | Incompletitud | % Vacío | Descripción del Campo | Fuente u Origen del Dato |
| :--- | :---: | :---: | :--- | :--- |
| `ShortName` | 22 / 387 | 5.7% | Sigla o nombre corto de la unidad/curso (ej. "1A", "MAT-8B"). | Parametrización inicial realizada por UTP o Administrador al crear asignaturas/cursos. |

---

### 2.3. Tabla `OrganizationIdentifier` (Total Registros: 1)
Identificadores oficiales de la institución.

| Campo Vacío | Incompletitud | % Vacío | Descripción del Campo | Fuente u Origen del Dato |
| :--- | :---: | :---: | :--- | :--- |
| `RefOrganizationIdentifierTypeId` | 1 / 1 | 100.0% | Tipo de identificación institucional (Código RBD, Sede, Reconocimiento Oficial). | Selector de tipo de identificador en el módulo de Configuración del Establecimiento. |

---

### 2.4. Tabla `OrganizationPersonRole` (Total Registros: 13)
Vínculo entre la persona, la organización y el rol asignado (ej. Estudiante en 1º Básico A).

| Campo Vacío | Incompletitud | % Vacío | Descripción del Campo | Fuente u Origen del Dato |
| :--- | :---: | :---: | :--- | :--- |
| `ExitDate` | 9 / 13 | 69.2% | Fecha de retiro o desvinculación de la persona. | Módulo de Retiro de Estudiantes o desvinculación docente. *(Correcto que esté vacío en alumnos activos)*. |

---

### 2.5. Tabla `PersonAddress` (Total Registros: 14)
Dirección de residencia de alumnos y apoderados.

| Campo Vacío | Incompletitud | % Vacío | Descripción del Campo | Fuente u Origen del Dato |
| :--- | :---: | :---: | :--- | :--- |
| `RefCountyId` | 14 / 14 | 100.0% | Código INE/MINEDUC de la comuna de residencia. | Selector/Dropdown de Comuna en el Formulario de Matrícula (Mapeo a catálogo oficial). |

---

### 2.6. Tabla `PersonStatus` (Total Registros: 2)
Histórico de estados del estudiante (Matriculado, Retirado, Suspendido).

| Campos Vacíos | Incompletitud | % Vacío | Descripción de los Campos | Fuente u Origen del Dato |
| :--- | :---: | :---: | :--- | :--- |
| `StatusEndDate`, `docNumber`, `fileScanBase64`, `recordEndDateTime` | 2 / 2 | 100.0% | Fecha fin de estado, N° de documento oficial de respaldo, copia digitalizada Base64 y fecha límite. | Módulo de Gestión de Matrícula / Tramitación de retiros con documento firmado. |

---

## 3. Tablas Estándar MINEDUC Totalmente Vacías (0 Registros)

Estas tablas corresponden a módulos operativos EDE que aún no han sido ejecutados en la base de datos actual:

| Tabla MINEDUC | Propósito / Función | Módulo Emisor / Origen del Dato |
| :--- | :--- | :--- |
| `OrganizationCalendarSession` | Leccionario oficial y bloques de clase ejecutados. | **Libro de Clases / Leccionario** (al firmar la hora/clase del día). |
| `RoleAttendanceEvent` | Asistencia oficial diaria y por clase/asignatura. | **Módulo de Asistencia** (paso de lista docente o inspectoría). |
| `AssessmentResult` | Actas finales y registro oficial de calificaciones. | **Módulo de Notas** (ingreso de evaluaciones y promedios). |
| `Incident` | Registro de anotaciones e incidentes escolares. | **Convivencia Escolar / Inspectoría**. |
| `IncidentPerson` | Relación de personas involucradas en un incidente. | **Convivencia Escolar** (al asociar alumnos/docentes a la anotación). |
| `K12StudentDiscipline` | Medidas disciplinarias aplicadas tras un incidente. | **Convivencia Escolar / Inspectoría**. |
| `PersonBirthplace` | Lugar y país de origen/nacimiento. | **Módulo de Matrícula** (mapeo del país/comuna natal). |

---

## 4. Tablas de Extensión Edugest (`edugest_*`)

### 4.1. Tablas con Registros e Información Parcial

*   **`edugest_student_enrollment`** *(7 registros)*: Ficha socioeconómica y complementaria.
    *   *Campos vacíos:* `NivelEducacionalMadre`, `NivelEducacionalPadre`, `NivelEducacionalApoderado`, `IngresoFamiliar`, `NumIntegrantesHogar`, `PuebloOriginario`, `LenguaIndigena`, `NacionalidadExtranjera`, `MedioTransporte`, `NombreTransportista`, `TelefonoTransportista`, `TiempoEstimadoTraslado`, `Religion`, `CantidadComputadores`, `ViveCon`, `ObservacionesAcademicas`, `ObservacionesMedicas`, `ObservacionesFamiliares`, `ComentariosEstablecimiento`.
    *   *Origen:* Formulario de Matrícula (Secciones Socioeconómica, Transporte y Observaciones).
*   **`edugest_emergency_contact`** *(13 registros)*: Contactos de emergencia secundarios.
    *   *Campos vacíos:* `FirstName`, `LastName`, `SecondLastName`, `TelefonoAlternativo`, `Email`, `ProfesionOcupacion`, `NivelEducacional`.
    *   *Origen:* Formulario de Matrícula (Pestaña "Contactos de Emergencia").
*   **`edugest_student_health`** *(7 registros)*: Ficha médica del estudiante.
    *   *Campos vacíos:* `RestriccionesAlimentarias`, `NecesidadesMedicasEspeciales`, `ObservacionesMedicasDetalle`, `CentroSaludHabitual`, `MedicoTratante`, `TelefonoMedicoTratante`, `Estatura`, `Peso`.
    *   *Origen:* Formulario de Matrícula (Sección de Salud / Ficha Médica).
*   **`edugest_person_relationship_detail`** *(12 registros)*: Detalle extendido de apoderados/tutores.
    *   *Campos vacíos:* `EstadoCivil` (83.3%), `Direccion` (41.7%), `LugarTrabajo` (16.7%).
    *   *Origen:* Formulario de Matrícula (Pestaña "Datos del Apoderado").
*   **`edugest_curriculum_plan`** *(7 registros)*: Planificación curricular.
    *   *Campos vacíos:* `Actividad` (100%), `Contenido` (71.4%), `DetallesActividad` (71.4%), `Objetivo` (71.4%).
    *   *Origen:* Módulo de Planificación Curricular / UTP.

### 4.2. Tablas de Extensión Totalmente Vacías (0 Registros)

*   `edugest_book` y `edugest_book_loan` (Biblioteca)
*   `edugest_chat_message` y `edugest_announcement` (Comunicaciones y Anuncios)
*   `edugest_student_observation` (Observaciones de alumnos)
*   `edugest_session_attendance` (Asistencia por bloque)
*   `edugest_manual_grade` y `edugest_student_response` (Calificaciones y respuestas)
*   `edugest_organization_config` (Parámetros globales del colegio)

---

## 5. Plan de Acción y Prioridades de Corrección

Para garantizar la conformidad con el Estándar Digital de Información Educativa (EDE/MINEDUC) y la integridad de la aplicación, se establecen las siguientes prioridades de ajuste en código:

1.  **Mapeo de Comuna (`PersonAddress.RefCountyId`)**:
    *   *Acción:* Modificar `app/modules/matricula/routes.py` para asegurar que la comuna seleccionada en el frontend convierta el nombre a su correspondiente `RefCountyId` del catálogo MINEDUC al insertar la dirección.
2.  **Atributos de Identidad en `Person`**:
    *   *Acción:* Asegurar que los valores de `RefSexId`, `Birthdate` y `RefTribalAffiliationId` ingresados en el formulario de matrícula se guarden directamente en la tabla `Person` (y no únicamente en la extensión `edugest_student_enrollment`).
3.  **Mapeo de Contactos de Emergencia (`edugest_emergency_contact`)**:
    *   *Acción:* Revisar la captura de nombres y datos de contacto alternativos en la vista `formulario.html` para evitar la creación de registros con nombres nulos.