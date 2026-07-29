# Mapeo y Diccionario de Datos: Modelo MINEDUC (Estándar EDE)

Este documento detalla la estructura del modelo `app/models/mineduc.py` alineado con el estándar **EDE (Estándar de Datos de Educación - MINEDUC)**. 

---

## 1. Mapeo de Tablas y Columnas por Módulo

---

### Módulo 1: Identidad y Contacto de Personas

#### 1.1 `Person`
* **Propósito de la tabla:** Registra la identidad básica indivisible de cada individuo en la comunidad educativa (Estudiantes, Apoderados, Profesores, Directivos, Personal Administrativo).

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonId` | `Integer` | **Sí (PK)** | Identificador único interno autoincremental de la persona. |
| `FirstName` | `String(100)` | **Sí** | Primer nombre de la persona. |
| `MiddleName` | `String(100)` | No | Segundo nombre o nombres adicionales. |
| `LastName` | `String(100)` | **Sí** | Primer apellido (Apellido Paterno). |
| `SecondLastName` | `String(100)` | No | Segundo apellido (Apellido Materno). |
| `RefSexId` | `Integer` | No | Identificador de sexo según catálogo MINEDUC (ej. Femenino, Masculino). |
| `Birthdate` | `Date` | No | Fecha de nacimiento (`YYYY-MM-DD`). |
| `RefTribalAffiliationId` | `Integer` | No | Pertenencia o afinidad a pueblos originarios/etnias reconocidas. |

---

#### 1.2 `PersonIdentifier`
* **Propósito de la tabla:** Almacena todos los documentos e identificadores oficiales de una persona (RUT, IPE, Número de lista, Número de matrícula, etc.).

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonId` | `Integer` | **Sí (PK, FK)** | ID de la persona (`Person.PersonId`). |
| `Identifier` | `String(50)` | **Sí (PK)** | El valor o cadena del documento (ej. `"12.345.678-9"`, `"123"`, `"5"`). |
| `RefPersonIdentificationSystemId` | `Integer` | **Sí** | **Tipo de identificador:**<br>• `51`: RUN/RUT Chileno<br>• `52`: IPE (Identificador Provisorio Escolar)<br>• `54`: Número de Lista en el curso<br>• `55`: Número correlativo de Matrícula<br>• `43`: Registro/Ficha Escolar |

---

#### 1.3 `PersonAddress`
* **Propósito de la tabla:** Dirección geográfica de residencia de la persona[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonAddressId` | `Integer` | **Sí (PK)** | ID único del registro de dirección. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona asociada. |
| `StreetNumberAndName` | `String(255)` | No | Nombre de la calle, número, block/departamento. |
| `RefCountyId` | `Integer` | No | Código de la Comuna de residencia según el catálogo territorial MINEDUC/INE. |

---

#### 1.4 `PersonTelephone`
* **Propósito de la tabla:** Números telefónicos de contacto[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonTelephoneId` | `Integer` | **Sí (PK)** | ID único del registro telefónico. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona asociada. |
| `TelephoneNumber` | `String(50)` | No | Número de teléfono de red fija o celular. |

---

#### 1.5 `PersonEmailAddress`
* **Propósito de la tabla:** Correos electrónicos de contacto[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonEmailAddressId` | `Integer` | **Sí (PK)** | ID único del registro de email. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona asociada. |
| `EmailAddress` | `String(255)` | No | Dirección de correo electrónico. |

---

#### 1.6 `PersonBirthplace`
* **Propósito de la tabla:** Lugar y país de origen/nacimiento[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonBirthplaceId` | `Integer` | **Sí (PK)** | ID único del registro. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona asociada. |
| `RefCountryId` | `Integer` | No | Código del país de nacimiento según catálogo MINEDUC (ej. Chile, Venezuela, etc.). |

---

### Módulo 2: Relaciones, Estado y Salud de Personas

#### 2.1 `PersonRelationship`
* **Propósito de la tabla:** Establece los vínculos familiares y legales entre personas (ej. Apoderado y Estudiante)[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonRelationshipId` | `Integer` | **Sí (PK)** | ID único de la relación. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona principal (normalmente el **Estudiante**). |
| `RelatedPersonId` | `Integer` | **Sí (FK)** | ID de la persona relacionada (normalmente el **Apoderado/Padre/Madre**). |
| `RefPersonRelationshipId` | `Integer` | **Sí** | Tipo de parentesco/relación:<br>• `31`: Apoderado / Tutor legal. |

---

#### 2.2 `PersonStatus`
* **Propósito de la tabla:** Historial de estados académicos del estudiante (Matriculado, Retirado, Transfiriendo de curso, Suspendido)[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonStatusId` | `Integer` | **Sí (PK)** | ID único del estado. |
| `PersonId` | `Integer` | **Sí (FK)** | ID del estudiante. |
| `RefPersonStatusTypeId` | `Integer` | No | Código del tipo de estado (ej. Activo, Retirado, Cambio de Curso = `32`). |
| `StatusStartDate` | `Date` | No | Fecha de inicio de la condición/estado. |
| `StatusEndDate` | `Date` | No | Fecha de término de la condición/estado. |
| `Description` | `Text` | No | Motivo de retiro, justificación o comentarios del cambio de estado. |
| `docNumber` | `String(100)` | No | Número de documento oficial, resolución o acta administrativa asociada. |
| `fileScanBase64` | `Text` | No | Documento/solicitud firmado codificado en Base64. |
| `recordEndDateTime` | `Date` | No | Fecha y hora exacta en que se cerró/archivó el registro de estado. |

---

#### 2.3 `PersonHealth`
* **Propósito de la tabla:** Antecedentes de salud y necesidades médicas generales[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonHealthId` | `Integer` | **Sí (PK)** | ID único del registro de salud. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona (estudiante). |
| `Description` | `Text` | No | Descripción de condiciones de salud, enfermedades crónicas o cuidados especiales. |

---

#### 2.4 `PersonAllergy`
* **Propósito de la tabla:** Alergias médicas o alimentarias[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonAllergyId` | `Integer` | **Sí (PK)** | ID único del registro de alergia. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona. |
| `AllergyDescription` | `String(255)` | No | Detalle de alergias (medicamentos, alimentos, picaduras, etc.). |

---

#### 2.5 `PersonDegreeOrCertificate`
* **Propósito de la tabla:** Nivel de escolaridad/estudios alcanzados (utilizado principalmente para Apoderados o Docentes)[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `PersonDegreeOrCertificateId` | `Integer` | **Sí (PK)** | ID único del nivel educativo. |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona. |
| `RefDegreeOrCertificateTypeId` | `Integer` | No | Código del nivel educacional según tabla oficial MINEDUC (Básica completa, Media, Universitaria, etc.). |

---

### Módulo 3: Estructura Organizacional Escolar (RBD, Cursos y Asignaturas)

#### 3.1 `Organization`
* **Propósito de la tabla:** Representa cualquier nodo de la estructura educativa (Colegio/RBD, Modalidades, Jornadas, Niveles, Grados, Cursos, Asignaturas)[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `OrganizationId` | `Integer` | **Sí (PK)** | ID único de la entidad organizacional. |
| `Name` | `String(255)` | **Sí** | Nombre completo (ej. `"Liceo Bicentenario"`, `"1° Medio A"`, `"Matemática"`). |
| `ShortName` | `String(50)` | No | Sigla o nombre corto (ej. `"RBD 12345"`, `"1MA"`). |
| `RefOrganizationTypeId` | `Integer` | **Sí** | **Tipo de estructura:**<br>• `10`: Colegio / Establecimiento (k12School)<br>• `38`: Modalidad<br>• `39`: Jornada<br>• `40`: Nivel Educativo<br>• `46`: Grado<br>• `21`: Curso / Letra<br>• `22`: Asignatura / Subsector |

---

#### 3.2 `OrganizationRelationship`
* **Propósito de la tabla:** Jerarquía padre-hijo que conecta la estructura del colegio[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `OrganizationRelationshipId` | `Integer` | **Sí (PK)** | ID único de la relación. |
| `OrganizationId` | `Integer` | **Sí (FK)** | ID del nodo **Hijo** (ej. la Asignatura o el Curso). |
| `ParentOrganizationId` | `Integer` | **Sí (FK)** | ID del nodo **Padre** (ej. el Grado o el Nivel). |

---

#### 3.3 `OrganizationIdentifier`
* **Propósito de la tabla:** Identificadores oficiales de la institución escolar (ej. Número de RBD)[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `OrganizationIdentifierId` | `Integer` | **Sí (PK)** | ID único del identificador. |
| `OrganizationId` | `Integer` | **Sí (FK)** | ID de la organización asociada. |
| `Identifier` | `String(50)` | **Sí** | Valor del identificador (ej. `"12345"` para el RBD). |
| `RefOrganizationIdentificationSystemId` | `Integer` | **Sí** | Sistema de identificación oficial. |
| `RefOrganizationIdentifierTypeId` | `Integer` | No | Tipo de identificador de la organización. |

---

#### 3.4 `OrganizationPersonRole`
* **Propósito de la tabla:** Vincula una `Person` con una `Organization` (Curso o Asignatura) asignándole un rol específico. Es la tabla clave de matriculación e inscripción de asignaturas[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `OrganizationPersonRoleId` | `Integer` | **Sí (PK)** | ID único de la asignación. |
| `OrganizationId` | `Integer` | **Sí (FK)** | ID de la organización (Curso o Asignatura). |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona (Estudiante o Profesor). |
| `RoleId` | `Integer` | **Sí** | Rol que desempeña en esa organización:<br>• `6`: Estudiante<br>• `3`: Profesor / Docente |
| `EntryDate` | `Date` | No | Fecha de inicio/inscripción en el curso o asignatura. |
| `ExitDate` | `Date` | No | Fecha de retiro o cierre de participación en el curso. |
| `EsProfesorJefe` | `Boolean` | **Sí** | `True` si el docente es el Profesor Jefe asignado a este curso. |

---

### Módulo 4: Asistencia y Leccionario Oficial

#### 4.1 `RoleAttendanceEvent`
* **Propósito de la tabla:** Registro oficial de asistencia y/o inasistencia diaria y por asignatura[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `RoleAttendanceEventId` | `Integer` | **Sí (PK)** | ID único del evento de asistencia. |
| `OrganizationPersonRoleId` | `Integer` | **Sí (FK)** | ID de la matrícula/inscripción del estudiante (`OrganizationPersonRole.OrganizationPersonRoleId`). |
| `Date` | `Date` | **Sí** | Fecha de la asistencia (`YYYY-MM-DD`). |
| `RefAttendanceEventTypeId` | `Integer` | **Sí** | Tipo de evento (diaria, por bloque de asignatura). |
| `RefAttendanceStatusId` | `Integer` | **Sí** | Estado de la asistencia (Presente, Ausente, Atrasado). |
| `RefAbsentAttendanceCategoryId` | `Integer` | No | Categoría/justificación de inasistencia (Médica, Familiar, etc.). |
| `RefPresentAttendanceCategoryId` | `Integer` | No | Categoría de presencia/modalidad. |
| `VirtualIndicator` | `Boolean` | No | `True` si la asistencia fue en modalidad telepresencial/remota. |
| `fileScanBase64` | `Text` | No | Firma o documento de justificación escaneado en Base64. |
| `digitalRandomKey` | `Text` | No | Clave aleatoria / hash de validación e identidad digital. |
| `Observaciones` | `Text` | No | Comentarios o notas sobre la asistencia/atraso. |

---

#### 4.2 `OrganizationCalendarSession`
* **Propósito de la tabla:** Leccionario Oficial de Clases. Guarda las actividades pedagógicas, temas tratados y planificación por sesión[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `OrganizationCalendarSessionId` | `Integer` | **Sí (PK)** | ID único del registro del leccionario. |
| `OrganizationId` | `Integer` | **Sí (FK)** | ID de la Asignatura/Curso correspondiente. |
| `BeginDate` | `String(10)` | **Sí** | Fecha de inicio de la clase (`YYYY-MM-DD`). |
| `EndDate` | `String(10)` | **Sí** | Fecha de término de la clase (`YYYY-MM-DD`). |
| `SessionStartTime` | `String(8)` | No | Hora de inicio de la clase (`HH:MM:SS`). |
| `SessionEndTime` | `String(8)` | No | Hora de término de la clase (`HH:MM:SS`). |
| `Description` | `Text` | No | Contenido pedagógico impartido, actividades realizadas y observaciones de la clase. |
| `MarkingTermIndicator` | `Boolean` | No | `True` si marca un hito/término de periodo evaluativo. |
| `SchedulingTermIndicator` | `Boolean` | No | `True` si corresponde a una sesión programada en calendario. |
| `PlanId` | `Integer` | No (FK) | Vinculación opcional con el plan curricular Edugest. |

---

### Módulo 5: Evaluaciones y Calificaciones Oficiales

#### 5.1 `AssessmentResult`
* **Propósito de la tabla:** Acta y registro de calificaciones/notas oficiales para la promoción del estudiante[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `AssessmentResultId` | `Integer` | **Sí (PK)** | ID único de la nota/resultado. |
| `OrganizationPersonRoleId` | `Integer` | **Sí (FK)** | ID de la inscripción asignatura-estudiante (`OrganizationPersonRole.OrganizationPersonRoleId`). |
| `ScoreValue` | `String(20)` | **Sí** | Valor de la calificación obtenida (ej. `"6.5"`, `"7.0"`, `"MB"`). |

---

### Módulo 6: Convivencia Escolar, Incidentes y Medidas Disciplinarias

#### 6.1 `Incident`
* **Propósito de la tabla:** Anotaciones de convivencia, citaciones, reuniones de apoderados e incidentes escolares[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `IncidentId` | `Integer` | **Sí (PK)** | ID único del incidente/reunión. |
| `OrganizationId` | `Integer` | No (FK) | Curso o establecimiento donde ocurrió el evento. |
| `IncidentDate` | `Date` | No | Fecha del suceso o reunión (`YYYY-MM-DD`). |
| `IncidentTime` | `Time` | No | Hora del suceso (`HH:MM:SS`). |
| `IncidentDescription` | `Text` | No | Detalle de la anotación de convivencia, temario o acuerdos alcanzados. |
| `RefIncidentBehaviorId` | `Integer` | No | **Tipo de evento/conducta:**<br>• `32`: Temario / Reunión de Apoderados<br>• Otros códigos: Anotación positiva, leve, grave, gravísima. |

---

#### 6.2 `IncidentPerson`
* **Propósito de la tabla:** Personas involucradas en una anotación, reunión o incidente (Estudiante, Apoderado, Docente que registra)[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `IncidentPersonId` | `Integer` | **Sí (PK)** | ID único del registro de participación. |
| `IncidentId` | `Integer` | **Sí (FK)** | ID del incidente (`Incident.IncidentId`). |
| `PersonId` | `Integer` | **Sí (FK)** | ID de la persona involucrada (`Person.PersonId`). |
| `RefIncidentPersonRoleTypeId` | `Integer` | No | Rol de la persona en el evento (ej. Autor, Victima, Apoderado asistente). |
| `fileScanBase64` | `Text` | No | Escaneo de la hoja de firma o acta de reunión en Base64. |
| `digitalRandomKey` | `String(255)` | No | Clave/Hash de verificación de identidad digital. |
| `Date` | `Date` | No | Fecha de firma/registro del participante. |

---

#### 6.3 `K12StudentDiscipline`
* **Propósito de la tabla:** Medidas disciplinarias formales aplicadas al estudiante derivadas de un incidente[cite: 5, 6].

| Columna | Tipo de Dato | Requerido | Descripción / Dato que almacena |
| :--- | :--- | :--- | :--- |
| `K12StudentDisciplineId` | `Integer` | **Sí (PK)** | ID único de la medida disciplinaria. |
| `IncidentId` | `Integer` | **Sí (FK)** | ID del incidente relacionado (`Incident.IncidentId`). |
| `OrganizationPersonRoleId` | `Integer` | No (FK) | ID de la inscripción del estudiante sancionado (`OrganizationPersonRole.OrganizationPersonRoleId`). |

---

## 2. Resumen de Códigos de Referencia (`Ref*`) Importantes

Para evitar que los datos queden vacíos o mal clasificados durante la sincronización con MINEDUC, se deben utilizar los siguientes ID numéricos de referencia oficial[cite: 5, 6]:

* **Sistemas de Identificación de Personas (`RefPersonIdentificationSystemId`):**
  * `51`: RUN / RUT Chileno[cite: 6]
  * `52`: IPE (Identificador Provisorio Escolar)[cite: 6]
  * `54`: Número de Lista en el curso[cite: 6]
  * `55`: Número correlativo de Matrícula[cite: 6]
  * `43`: Identificador del Registro / Colegio[cite: 6]

* **Tipos de Organización (`RefOrganizationTypeId`):**
  * `10`: Colegio / Escuela (k12School)[cite: 6]
  * `38`: Modalidad[cite: 6]
  * `39`: Jornada[cite: 6]
  * `40`: Nivel Educativo[cite: 6]
  * `46`: Grado[cite: 6]
  * `21`: Curso / Letra[cite: 6]
  * `22`: Asignatura / Subsector[cite: 6]

* **Relaciones entre Personas (`RefPersonRelationshipId`):**
  * `31`: Apoderado / Tutor Legal[cite: 6]

* **Roles en la Organización (`RoleId`):**
  * `3`: Profesor / Docente[cite: 6]
  * `6`: Estudiante[cite: 6]

* **Estados del Estudiante (`RefPersonStatusTypeId`):**
  * `32`: Retiro / Salida / Cambio de curso[cite: 6]