```markdown
# Auditoría del Módulo: Libro Digital

## 1. Resumen General

El módulo Libro Digital es el componente central y más grande del sistema Edugest. Gestiona grados académicos, asignaturas, unidades curriculares, planificación de clases, registro diario de asistencia, exportación CSV de listas, y bitácora de observaciones de estudiantes. Integra datos de los modelos Mineduc (Organization, OrganizationPersonRole) y Edugest (CurriculumPlan, SessionAttendance, AssessmentInstrument, StudentObservation).

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/libro_digital/routes.py` | Python | Backend: 11 rutas, lógica de negocio completa |
| `app/templates/libro_digital/grados.html` | Jinja2/HTML | Listado de grados con toggle de habilitación |
| `app/templates/libro_digital/asignaturas.html` | Jinja2/HTML | Panel de asignaturas por grado con modal de creación |
| `app/templates/libro_digital/unidades.html` | Jinja2/HTML | Planificación: unidades curriculares y clases |
| `app/templates/libro_digital/lista_curso.html` | Jinja2/HTML | Libro de clases: asistencia diaria por curso |
| `app/templates/libro_digital/anotaciones.html` | Jinja2/HTML | Bitácora de observaciones de estudiantes |
| `app/templates/libro_digital/registrar_clase.html` | Jinja2/HTML | Template no referenciado por el backend (posiblemente obsoleto) |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2, CSV (stdlib).

**Prefijo de rutas:** `/libro-digital`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `Organization` | Mineduc | Grados (TypeId=46), Cursos (TypeId=21), Asignaturas (TypeId=22) |
| `OrganizationRelationship` | Mineduc | Jerarquía grado→curso, grado→asignatura |
| `OrganizationPersonRole` | Mineduc | Estudiantes en cursos (RoleId=6), profesores |
| `OrganizationCalendarSession` | Mineduc | Sesiones de clase |
| `Person` | Mineduc | Datos personales de estudiantes |
| `PersonIdentifier` | Mineduc | RUT (RefPersonIdentificationSystemId=51) |
| `EdugestOrganizationConfig` | Edugest | Configuración de grados (IsActive) |
| `EdugestCurriculumPlan` | Edugest | Planificación: unidades y clases |
| `EdugestSessionAttendance` | Edugest | Asistencia por sesión |
| `EdugestAssessmentInstrument` | Edugest | Evaluaciones vinculadas a planes |
| `EdugestStudentObservation` | Edugest | Anotaciones/observaciones de estudiantes |
| `EdugestModule` | Edugest | Para verificación de permisos |
| `EdugestRolePermission` | Edugest | Nivel de permiso del usuario |

### 2.2 Jerarquía organizacional Mineduc

```
Organization (TypeId=46) ── Grado
  └── OrganizationRelationship (ParentOrganizationId)
      ├── Organization (TypeId=21) ── Curso (ej: "A", "B")
      │   └── OrganizationPersonRole (RoleId=6) ── Estudiante
      └── Organization (TypeId=22) ── Asignatura
          └── EdugestCurriculumPlan ── Unidad/Clase
              └── EdugestAssessmentInstrument ── Evaluación
```

### 2.3 Estados de asistencia

| AttendanceStatusId | Estado | Color |
|--------------------|--------|-------|
| 1 | Presente | Verde (emerald) |
| 2 | Ausente | Rojo (rose) |
| 3 | Atrasado | Ámbar (amber) |

### 2.4 Tipos de observación

| Tipo | Color |
|------|-------|
| Positiva | Verde (emerald) |
| Negativa | Rojo (rose) |
| Otra | Ámbar (amber) |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/libro-digital/grados` | GET | `listar_grados` | `@login_required` | Listar grados con estado y conteo estudiantes |
| `/libro-digital/grados/actualizar` | POST | `actualizar_grado` | `@login_required` + permiso Libro Digital nivel 2 | Toggle habilitar/deshabilitar grado |
| `/libro-digital/grados/<grado_id>/asignaturas` | GET | `asignaturas_por_grado` | `@login_required` | Listar asignaturas de un grado |
| `/libro-digital/grados/<grado_id>/asignaturas/crear` | POST | `crear_asignatura_manual` | `@login_required` + permiso Libro Digital nivel 2 | Crear asignatura manualmente |
| `/libro-digital/asignatura/<org_id>/unidades` | GET | `ver_unidades` | `@login_required` | Ver unidades curriculares con evaluaciones |
| `/libro-digital/asignatura/<org_id>/unidades` | POST | `crud_unidades_post` | `@login_required` + permiso Libro Digital nivel 2 | Crear unidad o clase |
| `/libro-digital/asignatura/<org_id>/clase` | GET | `registrar_clase_get` | `@login_required` | Listado de estudiantes para firma |
| `/libro-digital/asignatura/<org_id>/clase` | POST | `registrar_clase_post` | `@login_required` + permiso Libro Digital nivel 2 | Registrar asistencia |
| `/libro-digital/asignatura/<org_id>/exportar` | GET | `exportar_lista` | `@login_required` + permiso Libro Digital nivel 1 | Exportar lista a CSV |
| `/libro-digital/anotacion/<rol_id>/<asignatura_id>` | GET | `ver_anotacion` | `@login_required` + permiso Libro Digital nivel 1 | Ver historial anotaciones |
| `/libro-digital/anotacion/<rol_id>/<asignatura_id>/crear` | POST | `registrar_anotacion_post` | `@login_required` + permiso Libro Digital nivel 2 | Crear anotación |

---

## 4. Sistema de Permisos

### 4.1 Decoradores utilizados

| Decorador | Fuente | Uso |
|-----------|--------|-----|
| `@login_required` | Flask-Login | Todas las rutas |
| `@permiso_requerido('Libro Digital', nivel)` | `auth/routes.py` | Rutas de escritura (nivel 2) y lectura avanzada (nivel 1) |
| Verificación manual `current_user.RoleId == 1` | — | No presente (usa decorador) |

### 4.2 Permisos en templates

Este módulo usa `user_permisos` (diccionario de niveles por módulo) en lugar de `can()` de `permissions.py`. Pertenece al sistema antiguo de permisos por niveles (0/1/2).

| Elemento | Condición en template |
|----------|----------------------|
| Botón "Agregar Asignatura Manual" | `user_permisos.get('Libro Digital', 0) > 1` |
| Botón "+ Nueva Unidad" | `user_permisos.get('Libro Digital', 0) >= 2` |
| Botón "+ Registrar Clase" | `user_permisos.get('Libro Digital', 0) >= 2` |
| Botón "+ Nueva Evaluación" | `user_permisos.get('Libro Digital', 0) >= 2` |
| Formulario de asistencia completo | `user_permisos.get('Libro Digital', 0) >= 2` |
| Link "Volver a Asignaturas" | `user_permisos.get('Evaluaciones', 0) >= 2` |
| Link "Preguntas" (evaluación) | `user_permisos.get('Evaluaciones', 0) >= 2` |
| Link "Resultados" (evaluación) | Nivel 2 siempre, nivel 1 solo si `IsVisible` |

---

## 5. Funcionalidades de Negocio

### 5.1 Listar grados
- Consulta `Organization` con `RefOrganizationTypeId=46`.
- Para cada grado: obtiene `EdugestOrganizationConfig.IsActive` (default True si no existe), cuenta estudiantes via join a cursos (TypeId=21) con `PersonRole.RoleId=6` y `ExitDate=None`.

### 5.2 Actualizar grado
- Toggle `IsActive` en `EdugestOrganizationConfig`. Si no existe config, la crea.

### 5.3 Asignaturas por grado
- Busca `Organization` con `TypeId=22` hijos del grado via `OrganizationRelationship`.

### 5.4 Crear asignatura manual
- Valida nombre obligatorio, código opcional (default: primeras 3 letras).
- Verifica duplicados por nombre en el grado.
- Crea `Organization` + `OrganizationRelationship`.

### 5.5 Unidades curriculares (GET)
- Carga `EdugestCurriculumPlan` agrupados por `UnitTitle`.
- Determina nivel de permisos: Admin=2, sino consulta `EdugestRolePermission` para módulo "Evaluaciones".
- Nivel 2 ve todas las evaluaciones, nivel 1 solo las visibles (`IsVisible=True`).
- Solo muestra clases con contenido/objetivo/detalles.

### 5.6 Unidades curriculares (POST)
- `action='crear_unidad'`: Crea `EdugestCurriculumPlan` con solo `UnitTitle`.
- `action='crear_clase'`: Crea `EdugestCurriculumPlan` con contenido, actividad, detalles, objetivo.

### 5.7 Registrar clase (GET)
- Lista estudiantes de un curso específico (grado + letra).
- Muestra letras de curso disponibles para seleccionar.

### 5.8 Registrar clase (POST)
- Crea `OrganizationCalendarSession` con hora inicio/término.
- Para cada estudiante guarda `EdugestSessionAttendance` con estado (1/2/3).
- Usa `db.session.flush()` para obtener ID de sesión antes de crear asistencias.

### 5.9 Exportar CSV
- Genera CSV con delimitador `;` y encoding `utf-8-sig` (para Excel).
- Columnas: Asignatura, Curso, Letra, Fecha, Hora, RUT, Apellidos, Nombres, Estado.
- Si no hay sesiones hoy, exporta estudiantes con "Sin registro".
- Si hay sesiones, exporta asistencia por sesión por estudiante.

### 5.10 Anotaciones (GET)
- Muestra historial de anotaciones de un estudiante en una asignatura, ordenado por fecha descendente.

### 5.11 Anotaciones (POST)
- Crea nueva `EdugestStudentObservation` con tipo (Positiva/Negativa/Otra), detalle y fecha Chile (`obtener_hora_chile()`).

---

## 6. Análisis por Archivo

### 6.1 `routes.py` — Backend

Archivo extenso (~300 líneas) con 11 rutas. Principal lógica de negocio del sistema.

### 6.2 `grados.html` — Listado de Grados

Tabla con toggle switch por grado, conteo de estudiantes, y link "Ver Cursos". Flash messages inline.

### 6.3 `asignaturas.html` — Panel de Asignaturas

Grid de cards por asignatura con botones "Planificar" y "Abrir Libro". Modal para crear asignatura manualmente (nombre + código). Usa `user_permisos` para ocultar/mostrar botones de escritura.

### 6.4 `unidades.html` — Planificación

Accordion HTML `<details>` por unidad. Cada clase muestra objetivo, contenido, detalles, evaluaciones vinculadas (con badges Digital/Publicada/Borrador). Modales para crear unidad y registrar clase. Integra endpoints del módulo `evaluaciones`.

### 6.5 `lista_curso.html` — Libro de Clases

Selector de curso por letra con auto-submit. Dos vistas: nivel 2 (formulario completo de asistencia con radios Presente/Ausente/Atrasado + horas), nivel 1 (solo lectura). Link a anotaciones por estudiante. Botón exportar CSV.

### 6.6 `anotaciones.html` — Bitácora de Observaciones

Formulario nueva anotación (tipo Positiva/Negativa/Otra + detalle). Historial con cards coloreadas por tipo. Link "Volver" via `javascript:history.back()`.

---

## 7. Hallazgos de Auditoría

### 7.1 Seguridad — CRÍTICO

Ninguno.

### 7.2 Seguridad — ALTO

#### [S1] Tres rutas sin protección de permisos
Las siguientes rutas solo tienen `@login_required` sin `@permiso_requerido`:
- `listar_grados` (GET) — muestra grados y conteo de estudiantes
- `asignaturas_por_grado` (GET) — muestra asignaturas
- `registrar_clase_get` (GET) — muestra lista de estudiantes con RUT y datos personales

Cualquier usuario autenticado puede acceder a la lista de estudiantes de cualquier curso.
- **Riesgo:** ALTO
- **Recomendación:** Agregar `@permiso_requerido('Libro Digital', 1)` o verificar permisos.

#### [S2] Sin protección CSRF
Ningún formulario POST incluye token CSRF. Afecta a: actualizar grado, crear asignatura, crear unidad/clase, registrar asistencia, crear anotación.
- **Archivos:** Todos los templates con forms POST
- **Riesgo:** ALTO

#### [S3] Sin validación de acceso por profesor asignado
Cualquier usuario con permisos de Libro Digital puede registrar asistencia, crear clases, y ver estudiantes de CUALQUIER asignatura/grado. No hay verificación de que el profesor esté asignado a ese curso.
- **Riesgo:** ALTO
- **Recomendación:** Verificar que el profesor tenga un `OrganizationPersonRole` activo en el curso.

### 7.3 Seguridad — MEDIO

#### [S4] Verificación de permisos incorrecta para evaluaciones
En `ver_unidades`, la verificación consulta permisos del módulo "Evaluaciones", no "Libro Digital". Un usuario con permisos en Libro Digital pero sin permisos en Evaluaciones no podría ver evaluaciones, y viceversa.
- **Archivo:** `routes.py`, función `ver_unidades`
- **Riesgo:** MEDIO

#### [S5] Sin validación de hora inicio < hora término
Los campos de hora en `registrar_clase_post` no tienen validación de que inicio sea anterior a término.
- **Riesgo:** BAJO

#### [S6] AttendanceStatusId hardcodeado
Los IDs 1, 2, 3 (Presente, Ausente, Atrasado) se usan directamente sin verificar que existan en una tabla de referencia.
- **Riesgo:** BAJO

#### [S7] Fecha de sesión usa `datetime.now()` en lugar de `obtener_hora_chile()`
`registrar_clase_post` usa `datetime.now().strftime('%Y-%m-%d')` para la fecha de la sesión, pero las anotaciones usan `obtener_hora_chile()`. Inconsistencia potencial si el servidor no está en zona horaria Chile.
- **Archivo:** `routes.py`
- **Riesgo:** MEDIO

### 7.4 Rendimiento

#### [P1] N+1 queries en múltiples funciones
- `listar_grados`: query adicional por cada grado (config + count estudiantes).
- `registrar_clase_get/post`: queries por cada estudiante (Person + PersonIdentifier).
- `exportar_lista`: queries por cada estudiante en cada sesión.
- **Riesgo:** MEDIO
- **Recomendación:** Usar `joinedload` o queries agregadas.

#### [P2] Sin paginación
Todos los grados, asignaturas, unidades y estudiantes se cargan sin paginación.
- **Riesgo:** BAJO-MEDIO

### 7.5 Arquitectura

#### [A1] Permisos inconsistentes entre rutas
Algunas rutas tienen `@permiso_requerido`, otras no. No hay un patrón claro de qué rutas requieren protección.

#### [A2] Verificación de permisos en templates usa `user_permisos` en lugar de `can()`
`libro_digital` usa el sistema antiguo de niveles (0/1/2), mientras que `admin/permissions.py` define el RBAC granular. Dos sistemas operando simultáneamente.

#### [A3] Sin eliminación de datos
No hay rutas para eliminar unidades, clases, evaluaciones o anotaciones. Solo crear.

#### [A4] Cross-modulo con evaluaciones
`unidades.html` referencia endpoints de `evaluaciones` (`disenar_preguntas`, `resultados`, `crear_evaluacion_clase`). El módulo no es autónomo.

#### [A5] Template `registrar_clase.html` no referenciado
Existe en la estructura de carpetas pero el backend no lo usa. Posiblemente obsoleto.

#### [A6] Código de asignatura truncado
Si no se proporciona código, se usa `nombre[:3].upper()`. Podría generar códigos ambiguos.

#### [A7] Permisos cruzados en "Volver"
El link "Volver a Asignaturas" en `unidades.html` se muestra condicionalmente según permisos del módulo "Evaluaciones", no "Libro Digital". Error de lógica.

### 7.6 Frontend

#### [F1] Sin protección de permisos en algunas vistas
`listar_grados`, `asignaturas_por_grado` y `registrar_clase_get` no verifican permisos en template.

#### [F2] Flash messages manejados inline
Varios templates tienen su propio bloque de flash messages en lugar de usar el de `base.html`. Posibles mensajes duplicados.

#### [F3] Botón "Subir Material" no funcional
En `unidades.html`, el botón "Subir Material (PDF, PPT, Excel)" es un `<button type="button">` sin acción. No implementado.

#### [F4] `javascript:history.back()` para navegación
`anotaciones.html` usa JavaScript en lugar de endpoint de Flask para "Volver". No confiable si el usuario llegó por URL directa.

---

## 8. Resumen de Hallazgos por Severidad

### Crítico (0)
Ninguno.

### Alto (3)
- [S1] Tres rutas sin protección de permisos (expone datos de estudiantes)
- [S2] Sin protección CSRF
- [S3] Sin validación de acceso por profesor asignado

### Medio (4)
- [S4] Verificación de permisos incorrecta para evaluaciones (consulta módulo "Evaluaciones" en vez de "Libro Digital")
- [S7] Inconsistencia de zona horaria (`datetime.now()` vs `obtener_hora_chile()`)
- [P1] N+1 queries en múltiples funciones
- [A1] Permisos inconsistentes entre rutas

### Bajo (7)
- [S5] Sin validación hora inicio < término
- [S6] AttendanceStatusId hardcodeado
- [P2] Sin paginación
- [A3] Sin eliminación de datos
- [A6] Código de asignatura truncado
- [A7] Permisos cruzados en "Volver" (usa "Evaluaciones" en vez de "Libro Digital")
- [F3] Botón "Subir Material" no funcional

---

## 9. Endpoint Map Visual

```
GET  /libro-digital/grados                                  → listar_grados()            (SIN permiso requerido)
POST /libro-digital/grados/actualizar                       → actualizar_grado()         (permiso Libro Digital 2)
GET  /libro-digital/grados/<grado_id>/asignaturas            → asignaturas_por_grado()    (SIN permiso requerido)
POST /libro-digital/grados/<grado_id>/asignaturas/crear      → crear_asignatura_manual()  (permiso Libro Digital 2)
GET  /libro-digital/asignatura/<org_id>/unidades             → ver_unidades()             (SIN permiso requerido)
POST /libro-digital/asignatura/<org_id>/unidades             → crud_unidades_post()       (permiso Libro Digital 2)
GET  /libro-digital/asignatura/<org_id>/clase                → registrar_clase_get()      (SIN permiso requerido)
POST /libro-digital/asignatura/<org_id>/clase                → registrar_clase_post()     (permiso Libro Digital 2)
GET  /libro-digital/asignatura/<org_id>/exportar             → exportar_lista()           (permiso Libro Digital 1)
GET  /libro-digital/anotacion/<rol_id>/<asignatura_id>       → ver_anotacion()            (permiso Libro Digital 1)
POST /libro-digital/anotacion/<rol_id>/<asignatura_id>/crear → registrar_anotacion_post() (permiso Libro Digital 2)
```

---

## 10. Diagrama de Flujo Principal

```
Grados (listar_grados)
  └── Asignaturas (asignaturas_por_grado)
      ├── Planificar → Unidades (ver_unidades)
      │   ├── Crear Unidad (crud_unidades_post)
      │   ├── Registrar Clase (crud_unidades_post)
      │   ├── Nueva Evaluación → [evaluaciones module]
      │   └── Ver Resultados → [evaluaciones module]
      ├── Abrir Libro → Lista Curso (registrar_clase_get)
      │   ├── Firmar Asistencia (registrar_clase_post)
      │   ├── Exportar CSV (exportar_lista)
      │   └── Anotaciones (ver_anotacion)
      │       └── Crear Anotación (registrar_anotacion_post)
      └── Crear Asignatura Manual (crear_asignatura_manual)
```

---

## 11. Integración con Otros Módulos

| Módulo | Integración |
|--------|-------------|
| `evaluaciones` | `unidades.html` referencia `evaluaciones.disenar_preguntas`, `evaluaciones.resultados`, `evaluaciones.crear_evaluacion_clase` |
| `auth` | Usa `permiso_requerido` y `verificar_escritura` de `auth/routes.py` |
| `portada` | Link de fallback "Volver al Inicio" en `unidades.html` |

---

*Auditoría generada a partir del análisis de los 6 archivos del módulo libro_digital (1 routes.py + 5 templates). El template `registrar_clase.html` no fue analizado por no ser referenciado por el backend.*
```

---
