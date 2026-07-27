## Analisis del Archivo 7 (reportes): `notas_sumativas.html`



### Proposito
Template Jinja2 que extiende `base.html`. Tabla de calificaciones por asignatura con columnas dinamicas para evaluaciones sumativas y calificativas, checkboxes AJAX para seleccionar sumativas, y recalculo en tiempo real de promedios via JavaScript. Es el template mas complejo del modulo reportes.

### Datos del backend

| Variable | Contenido |
|----------|-----------|
| `asignatura` | Objeto `Organization` (`.Name`, `.OrganizationId`) |
| `estudiantes` | Lista de dicts: `.opr_id`, `.alumno`, `.rut`, `.notas_sumativas`, `.notas_calificativas`, `.promedio_sum_sel`, `.promedio_calificativas`, `.nota_final`, `.cant_sum_sel`, `.cant_calif`, `.grado_id` |
| `todas_sumativas` | Lista de `EdugestAssessmentInstrument` (con `.Seleccionada`) |
| `calificativas` | Lista de `EdugestAssessmentInstrument` |
| `sumativas_seleccionadas` | Lista de instrumentos seleccionados |
| `sumativas_no_seleccionadas` | Lista de instrumentos no seleccionados |
| `puede_configurar` | Bool: si puede modificar seleccion de sumativas |

### Estructura

1. **Cabecera**: Link "Volver a Reportes", nombre asignatura, conteos (estudiantes, sumativas, calificativas), boton "Configurar Sumativas" (solo si `puede_configurar`).

2. **Leyenda de colores**: Verde=sumativa seleccionada, Gris=sumativa no seleccionada, Azul=calificativa, Amber=promedio sum. seleccionadas, Indigo=nota final.

3. **Tabla de calificaciones**:
   - **Header fila 1**: RUT, Estudiante (sticky), colspan Sumativas, colspan Calificativas, Nota Final.
   - **Header fila 2**: Nombres de evaluaciones + checkboxes AJAX (solo si `puede_configurar`), promedio sum. seleccionadas, promedio calificativas.
   - **Body**: Filas por estudiante con celdas sticky (RUT, Nombre), notas sumativas (verde/gris segun seleccionada), promedio sum. seleccionadas, notas calificativas, nota final (indigo).
   - **Footer**: Promedios del curso calculados via JS.

4. **Resumen inferior**: 4 cards (Total Estudiantes, Sumativas Seleccionadas, Calificativas, Promedio Curso Final).

### JavaScript (complejo)

| Funcion | Proposito |
|---------|-----------|
| `guardarSeleccionSumativa(checkbox)` | AJAX POST a `/reportes/api/guardar-sumativa/{id}` para toggle de sumativa |
| `actualizarEstilosSumativa(instrumentId, seleccionada)` | Actualiza CSS de header y celdas al cambiar seleccion |
| `recalcularTodo()` | Recalcula promedio sum. seleccionadas y nota final de cada estudiante en el navegador |
| `calcularPromediosFooter()` | Calcula promedios del footer por columna |
| `calcularResumen()` | Actualiza promedio curso en resumen inferior |
| `mostrarToast(mensaje)` | Toast de confirmacion |

### Permisos en template

| Elemento | Condicion |
|----------|-----------|
| Boton "Configurar Sumativas" | `puede_configurar` |
| Checkboxes de seleccion | `puede_configurar` |
| Texto "Seleccionada/No seleccionada" (sin checkbox) | `not puede_configurar` |

### Endpoints referenciados

| Endpoint | Metodo | Proposito |
|----------|--------|-----------|
| `reportes.index` | GET | Volver al panel |
| `reportes.configurar_sumativas(org_id)` | GET | Configurar sumativas |
| `reportes.api.guardar_sumativa_ajax(instrument_id)` | POST | Toggle AJAX de sumativa |

### Observaciones para la auditoria

1. **CSRF en AJAX**: `const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || ''`. Intenta leer CSRF de un meta tag, pero el template base probablemente no lo incluye. Si no existe el meta tag, envia token vacio.

2. **Recalculo en cliente**: Los promedios y nota final se recalculan en JavaScript al cambiar checkboxes. Patron correcto para UX reactiva, pero los datos mostrados inicialmente vienen del backend. Si el JS falla, los datos del backend son la fuente de verdad.

3. **Columnas sticky**: RUT y Estudiante tienen `sticky left-0` y `sticky left-[140px]`. Permite scroll horizontal manteniendo nombres visibles. Buen UX para tablas anchas.

4. **RUT visible**: Columna sticky con RUT en `font-mono`. Informacion sensible.

5. **Truncate en titulos**: `{{ s.Title|truncate(20, True) }}`. Limita titulos largos en headers.

6. **Footer calculado via JS**: Los promedios del footer no vienen del backend. Se calculan al cargar la pagina y al cambiar checkboxes. Si JS esta deshabilitado, el footer muestra "—".

7. **Colores condicionales consistentes**: Mismos umbrales que `curso.html` (>=4.0 verde/azul, >=3.0 amber, <3.0 rojo).

8. **Toast no intrusivo**: Aparece abajo a la derecha, desaparece en 2 segundos. UX refinada.

9. **Sin paginacion**: Todos los estudiantes se cargan en una sola tabla. Con muchos estudiantes, la tabla podria ser muy alta.

---

### Modulo reportes: Resumen

| # | Archivo | Hallazgos clave |
|---|---------|-----------------|
| 1 | `routes.py` | 10 rutas, SIN `@login_required`, SIN `@permiso_requerido`, PDF/CSV/graficos sin proteccion, N+1 masivo, logica de promedios duplicada |
| 2 | `index.html` | Panel de seleccion, asignaturas, sin verificacion de permisos en template |
| 3 | `apoderado_hijos.html` | Seleccion de hijo, RUT visible, sin proteccion en links |
| 4 | `configurar_sumativas.html` | Checkboxes para seleccionar sumativas, sin CSRF |
| 5 | `curso.html` | Reporte consolidado con filtros, tabla expandible, link PDF sin proteccion, campo fecha duplicado |
| 6 | `grado.html` | Reporte consolidado por grado, grafico PNG, calculos en Jinja2 |
| 7 | `notas_sumativas.html` | Tabla compleja con columnas dinamicas, AJAX para toggle, recalculo JS, CSRF intentado pero probablemente inefectivo |

---

Aqui va el `.md`:

```markdown
# Auditoría del Módulo: Reportes

## 1. Resumen General

El módulo Reportes es el sistema de análisis académico del establecimiento. Proporciona reportes consolidados de curso y grado (asistencia, calificaciones, anotaciones), calificaciones por asignatura con separación Sumativa/Calificativa, graficos de asistencia (matplotlib), exportación CSV, e informes individuales en PDF (ReportLab) con formato ISETT. Es el módulo con las dependencias más pesadas (matplotlib, reportlab) y la lógica de negocio más compleja después de Libro Digital.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/reportes/routes.py` | Python | Backend: 10 rutas, reportes, graficos, CSV, PDF |
| `app/templates/reportes/index.html` | Jinja2/HTML | Panel de selección de cursos |
| `app/templates/reportes/apoderado_hijos.html` | Jinja2/HTML | Selección de hijo para apoderados |
| `app/templates/reportes/configurar_sumativas.html` | Jinja2/HTML | Configurar evaluaciones sumativas |
| `app/templates/reportes/curso.html` | Jinja2/HTML | Reporte consolidado de curso |
| `app/templates/reportes/grado.html` | Jinja2/HTML | Reporte consolidado de grado |
| `app/templates/reportes/notas_sumativas.html` | Jinja2/HTML | Calificaciones por asignatura con AJAX |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2, matplotlib, ReportLab, fetch API (AJAX).

**Dependencias externas:** `matplotlib` (graficos), `reportlab` (PDF), `csv`/`StringIO` (CSV).

**Prefijo de rutas:** `/reportes`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `EdugestSessionAttendance` | Edugest | Asistencias (StatusId: 1=Presente, 2=Ausente, 3=Atrasado) |
| `EdugestStudentObservation` | Edugest | Anotaciones (Tipo: Positiva, Negativa, Otra) |
| `EdugestManualGrade` | Edugest | Calificaciones (Score, IsManual, InstrumentId) |
| `EdugestAssessmentInstrument` | Edugest | Instrumentos (AssessmentTypeId, Seleccionada) |
| `EdugestModule` / `EdugestRolePermission` | Edugest | Permisos |
| `EdugestStudentEnrollment` | Edugest | ComentariosEstablecimiento |
| `OrganizationCalendarSession` | Edugest | Total sesiones |
| `Organization` | Mineduc | Grados (46), cursos (21), asignaturas (22), colegio (10) |
| `OrganizationRelationship` | Mineduc | Jerarquía |
| `OrganizationPersonRole` | Mineduc | Matrícula |
| `Person` / `PersonIdentifier` | Mineduc | Datos personales |
| `PersonRelationship` | Mineduc | Relación apoderado-hijo |

### 2.2 Constantes

| Constante | Valor | Uso |
|-----------|-------|-----|
| `TIPO_SUMATIVA` | 1 | AssessmentTypeId para evaluaciones sumativas |
| `TIPO_CALIFICATIVA` | 2 | AssessmentTypeId para evaluaciones calificativas |

### 2.3 Helpers

| Helper | Propósito |
|--------|-----------|
| `get_permiso_modulo(module_name)` | Nivel de permiso del usuario para un módulo |
| `calcular_rango_fechas(fecha_base, periodo)` | Calcula inicio/fin según periodo (mes/semestre/anio) |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/reportes/` | GET | `index` | **Sin @login_required**, verif. inline | Panel de selección/redirección |
| `/reportes/curso/<curso_id>` | GET | `reporte_curso` | **SIN protección** | Reporte consolidado de curso |
| `/reportes/grado/<grado_id>` | GET | `reporte_grado` | **SIN protección** | Reporte consolidado de grado |
| `/reportes/asignatura/<org_id>` | GET | `reporte_notas_sumativas` | **SIN protección** | Calificaciones por asignatura |
| `/reportes/asignatura/<org_id>/configurar-sumativas` | GET, POST | `configurar_sumativas` | Verif. inline nivel >= 2 | Configurar sumativas |
| `/reportes/api/guardar-sumativa/<id>` | POST | `guardar_sumativa_ajax` | Verif. inline nivel >= 2 | API AJAX toggle sumativa |
| `/reportes/curso/<curso_id>/grafico_asistencia` | GET | `grafico_asistencia` | **SIN protección** | Grafico PNG |
| `/reportes/curso/<curso_id>/exportar_asistencia` | GET | `exportar_asistencia` | **SIN protección** | CSV |
| `/reportes/curso/<curso_id>/informe_notas/<rol_id>` | GET | `informe_notas_pdf` | **SIN protección** | PDF individual |
| `/reportes/grado/<grado_id>/grafico` | GET | `grafico_grado` | **SIN protección** | Grafico PNG del grado |

---

## 4. Funcionalidades de Negocio

### 4.1 Index
- **Nivel 0**: Redirige a `auth.unauthorized`.
- **Nivel 1 (alumno)**: Redirige a `reporte_curso` de su curso.
- **Nivel 1 (apoderado)**: Si un hijo, redirige directo. Si múltiples, muestra selección.
- **Nivel 2+**: Panel completo de grados, cursos, asignaturas.

### 4.2 Reporte de curso
- Asistencias agrupadas por alumno y estado.
- Notas separadas por tipo: sumativas y calificativas.
- **Promedio final**: Promedio de (calificativas individuales + promedio de sumativas seleccionadas).
- Anotaciones con conteo por tipo.
- Periodo configurable: mes, semestre, año.

### 4.3 Reporte de grado
- Consolidado de todos los cursos del grado.
- Asistencia, notas promedio, anotaciones por curso.

### 4.4 Notas sumativas
- Columnas individuales por evaluación.
- Checkboxes AJAX para seleccionar cuales sumativas "cuentan".
- Recálculo en tiempo real via JavaScript.
- Nota final = promedio de (calificativas + promedio sum. seleccionadas).

### 4.5 Informe PDF (ISETT)
- Formato institucional: logo, encabezado, datos narrativos, tabla dinámica de calificaciones, asistencia, anotaciones, comentarios, firmas.
- Columnas dinámicas según máximo de evaluaciones.
- Busca profesor jefe (RoleId=3) y director (RoleId=2).
- Ciudad hardcoded: "Temuco".

---

## 5. Hallazgos de Auditoría

### 5.1 Seguridad — CRÍTICO

#### [S1] Sin `@login_required` en ninguna ruta
Todas las rutas carecen del decorador `@login_required`. Un usuario no autenticado puede acceder a cualquier reporte si conoce la URL, incluyendo datos personales (RUT), calificaciones, asistencia, y PDFs con información médica.
- **Archivo:** `routes.py`, todas las funciones
- **Riesgo:** CRÍTICO

### 5.2 Seguridad — ALTO

#### [S2] Sin `@permiso_requerido` en 8 de 10 rutas
Solo `index`, `configurar_sumativas` y `guardar_sumativa_ajax` verifican permisos (inline). Las otras 7 rutas no tienen verificación alguna: `reporte_curso`, `reporte_grado`, `reporte_notas_sumativas`, `grafico_asistencia`, `exportar_asistencia`, `informe_notas_pdf`, `grafico_grado`.
- **Riesgo:** ALTO

#### [S3] Sin protección CSRF
`configurar_sumativas` es POST sin CSRF. `guardar_sumativa_ajax` envía JSON con intento de CSRF token (`meta[name="csrf-token"]`) pero el template base probablemente no incluye el meta tag.
- **Riesgo:** ALTO

#### [S4] Informe PDF con datos sensibles accesible sin autenticación
`informe_notas_pdf` genera un PDF con nombre completo, RUT, calificaciones, asistencia, anotaciones, información médica, y comentarios del establecimiento. Cualquiera puede descargarlo.
- **Riesgo:** ALTO

### 5.3 Seguridad — MEDIO

#### [S5] Sin filtro de acceso por organización
`reporte_curso(curso_id)` y `reporte_grado(grado_id)` no verifican que el usuario tenga acceso a esa organización. Un profesor del curso A puede ver el reporte del curso B.
- **Riesgo:** MEDIO-ALTO

#### [S6] CSV de asistencia sin protección
`exportar_asistencia` genera un CSV con nombres y RUTs de todos los alumnos de un curso. Sin autenticación.
- **Riesgo:** ALTO

### 5.4 Rendimiento

#### [P1] N+1 queries masivo
- `index`: Consulta asignaturas e instrumentos por cada curso.
- `reporte_curso`: Consulta Person, PersonIdentifier por cada alumno.
- `informe_notas_pdf`: Múltiples consultas por alumno.
- `reporte_grado`: Consultas por cada curso del grado.
- **Riesgo:** ALTO

#### [P2] Gráficos generados en cada request
matplotlib crea figuras en memoria. Sin cache. Cada visita regenera el gráfico.
- **Riesgo:** MEDIO

### 5.5 Arquitectura

#### [A1] Lógica de promedios duplicada
La fórmula (calificativas + promedio sum. seleccionadas) está implementada en 3 lugares: `reporte_curso`, `reporte_notas_sumativas`, `informe_notas_pdf`. Si se cambia la fórmula, hay que actualizar 3 funciones + JavaScript.
- **Riesgo:** MEDIO

#### [A2] Filtro de fecha duplicado en `curso.html`
`<input type="hidden" name="fecha">` + `<input type="date" name="fecha">`. Dos campos con el mismo nombre. Conflicto potencial.
- **Riesgo:** BAJO

#### [A3] Ciudad hardcoded en PDF
"Temuco" en el pie de página del PDF.
- **Riesgo:** BAJO

#### [A4] Profesor jefe = primer profesor del curso
`informe_notas_pdf` busca RoleId=3 y toma `.first()`. Si hay múltiples profesores, puede tomar el incorrecto.
- **Riesgo:** BAJO

#### [A5] Sin paginación en tablas
Todos los estudiantes se cargan sin paginación.
- **Riesgo:** BAJO-MEDIO

#### [A6] Asistencia en PDF sin filtro de periodo
`informe_notas_pdf` no filtra asistencia por periodo. Muestra acumulado total.
- **Riesgo:** BAJO

#### [A7] Fórmula de nota final calculada en backend Y frontend
El backend calcula la nota final al cargar la página. El JavaScript la recalcula al cambiar checkboxes. Si hay diferencias de redondeo, los valores podrían divergir.
- **Riesgo:** BAJO

---

## 6. Resumen de Hallazgos por Severidad

### Crítico (1)
- [S1] Sin `@login_required` en ninguna ruta

### Alto (4)
- [S2] Sin `@permiso_requerido` en 8/10 rutas
- [S3] Sin protección CSRF
- [S4] PDF con datos sensibles sin autenticación
- [S6] CSV sin protección

### Medio (3)
- [S5] Sin filtro de acceso por organización
- [P1] N+1 queries masivo
- [A1] Lógica de promedios duplicada

### Bajo (6)
- [P2] Gráficos sin cache
- [A2] Filtro de fecha duplicado
- [A3] Ciudad hardcoded en PDF
- [A4] Profesor jefe = primer profesor
- [A5] Sin paginación
- [A7] Nota final calculada en backend y frontend

---

## 7. Endpoint Map Visual

```
GET  /reportes/                                     → index()                    (verif. inline)
GET  /reportes/curso/<curso_id>                     → reporte_curso()            (SIN protección)
GET  /reportes/grado/<grado_id>                     → reporte_grado()            (SIN protección)
GET  /reportes/asignatura/<org_id>                  → reporte_notas_sumativas()  (SIN protección)
GET  /reportes/asignatura/<org_id>/configurar-sumativas → configurar_sumativas() (verif. inline)
POST /reportes/asignatura/<org_id>/configurar-sumativas → configurar_sumativas() (verif. inline)
POST /reportes/api/guardar-sumativa/<id>            → guardar_sumativa_ajax()    (verif. inline)
GET  /reportes/curso/<curso_id>/grafico_asistencia  → grafico_asistencia()       (SIN protección)
GET  /reportes/curso/<curso_id>/exportar_asistencia → exportar_asistencia()      (SIN protección)
GET  /reportes/curso/<curso_id>/informe_notas/<rol_id> → informe_notas_pdf()    (SIN protección)
GET  /reportes/grado/<grado_id>/grafico             → grafico_grado()            (SIN protección)
```

---

## 8. Integración Cross-Módulo

| Módulo | Integración |
|--------|-------------|
| `evaluaciones` | Usa `EdugestAssessmentInstrument` para calificaciones, `AssessmentTypeId` para separar sumativas/calificativas, `Seleccionada` para promedios |
| `libro_digital` | Usa `EdugestSessionAttendance` para asistencias, `EdugestStudentObservation` para anotaciones |
| `matricula` | Usa `EdugestStudentEnrollment.ComentariosEstablecimiento` en PDF |
| `auth` | Usa `EdugestRolePermission` para verificar permisos inline |
| `portada` | Link "Volver al Inicio" en selección de hijos |

---

*Auditoría generada a partir del análisis de los 7 archivos del módulo reportes (1 routes.py + 6 templates).*
```

---
