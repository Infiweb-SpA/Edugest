```markdown
# Auditoría del Módulo: Evaluaciones

## 1. Resumen General

El módulo Evaluaciones es el segundo componente más grande del sistema Edugest (después de Libro Digital). Gestiona el ciclo de vida completo de evaluaciones: creación de instrumentos, diseño de preguntas (5 tipos), rendición online por alumnos, calificación automática en escala 1.0-7.0, gestión de notas manuales, publicación con integración al calendario, e impresión en formato A4.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/evaluaciones/routes.py` | Python | Backend: 15 rutas, lógica de negocio completa |
| `app/templates/evaluaciones/index.html` | Jinja2/HTML | Panel principal (posiblemente obsoleto) |
| `app/templates/evaluaciones/grados.html` | Jinja2/HTML | Selector de grado |
| `app/templates/evaluaciones/asignaturas.html` | Jinja2/HTML | Selector de asignatura |
| `app/templates/evaluaciones/unidades.html` | Jinja2/HTML | Unidades con evaluaciones vinculadas |
| `app/templates/evaluaciones/crear_evaluacion.html` | Jinja2/HTML | Formulario crear evaluación (flujo principal) |
| `app/templates/evaluaciones/crear_instrumento.html` | Jinja2/HTML | Formulario crear evaluación (alternativo, simplificado) |
| `app/templates/evaluaciones/disenar_preguntas.html` | Jinja2/HTML | Diseñador de preguntas (5 tipos) |
| `app/templates/evaluaciones/resultados.html` | Jinja2/HTML | Consolidado de calificaciones con notas manuales |
| `app/templates/evaluaciones/rendir.html` | Jinja2/HTML | Entorno de examen virtual |
| `app/templates/evaluaciones/imprimir.html` | HTML standalone | Vista imprimible A4 |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Werkzeug (secure_filename), Jinja2, Tailwind CDN (imprimir).

**Prefijo de rutas:** `/evaluaciones`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `EdugestAssessmentInstrument` | Edugest | Instrumento de evaluación (título, tipo, visibilidad, digital) |
| `EdugestAssessmentQuestion` | Edugest | Preguntas del instrumento |
| `EdugestQuestionOption` | Edugest | Opciones de respuesta (con MatchText para Relación Columnas) |
| `EdugestStudentResponse` | Edugest | Respuestas de alumnos |
| `EdugestManualGrade` | Edugest | Calificaciones (automáticas o manuales) |
| `EdugestCurriculumPlan` | Edugest | Plan/clase vinculada |
| `EdugestCalendarEvent` | Edugest | Eventos de calendario |
| `EdugestModule` | Edugest | Para verificación de permisos |
| `EdugestRolePermission` | Edugest | Nivel de permiso del usuario |
| `Organization` | Mineduc | Grados, cursos, asignaturas |
| `OrganizationRelationship` | Mineduc | Jerarquía organizacional |
| `OrganizationPersonRole` | Mineduc | Matrícula de estudiantes |
| `Person` / `PersonIdentifier` | Mineduc | Datos personales |

### 2.2 Tipos de pregunta soportados

| Tipo | Opciones | Calificación | Campos |
|------|----------|-------------|--------|
| `Alternativa` | 4 opciones, 1 correcta | Automática | `opcion_1..4`, `correcta` |
| `VerdaderoFalso` | 2 opciones (V/F) | Automática | `vf_correcta` |
| `Desarrollo` | Texto libre | Manual (`ScoreEarned=None`) | Textarea |
| `RelacionColumnas` | Hasta 3 pares izq-der | Parcial automática | `rel_izq_1..3`, `rel_der_1..3` |
| `Completar` | Hasta 3 respuestas | Parcial automática | `comp_resp_1..3` |

### 2.3 Tipos de evaluación

| Tipo | AssessmentTypeId | Notas |
|------|-----------------|-------|
| Sumativa | 1 | Se promedia automáticamente, `Seleccionada=True` |
| Calificativa | 2 | Valor por defecto |
| Formativa | 2 | — |
| Diagnóstica | 2 | — |
| Otra | 2 | — |

### 2.4 Fórmula de calificación

```
nota = 1 + (puntaje_obtenido / puntaje_maximo) * 6
```

Escala chilena: 1.0 (mínimo) a 7.0 (máximo). Nota de aprobación: ≥ 4.0.

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/evaluaciones/` | GET | `index` | `@login_required` | Redirect a `listar_grados` |
| `/evaluaciones/grados` | GET | `listar_grados` | `@login_required` + permiso Eval 1 | Listar grados con conteo evaluaciones |
| `/evaluaciones/grado/<grado_id>/asignaturas` | GET | `asignaturas_por_grado` | `@login_required` | Listar asignaturas con conteo evals |
| `/evaluaciones/asignatura/<org_id>/unidades` | GET | `unidades_asignatura` | `@login_required` | Ver unidades con evaluaciones |
| `/evaluaciones/asignatura/<org_id>/nuevo` | GET, POST | `crear_instrumento` | `@login_required` + permiso Eval 1 | **Redirect hardcoded a grado_id=1** |
| `/evaluaciones/clase/<plan_id>/nueva-evaluacion` | GET | `crear_evaluacion_clase` | `@login_required` + permiso Eval 1 | Formulario nueva evaluación |
| `/evaluaciones/clase/<plan_id>/nueva-evaluacion` | POST | `crear_evaluacion_clase_post` | `@login_required` + permiso Eval 2 | Crear evaluación + evento calendario |
| `/evaluaciones/disenar_preguntas/<inst_id>` | GET | `disenar_preguntas` | `@login_required` + permiso Eval 1 | Ver preguntas del instrumento |
| `/evaluaciones/disenar_preguntas/<inst_id>/crear` | POST | `disenar_preguntas_post` | `@login_required` + permiso Eval 2 | Crear pregunta con opciones |
| `/evaluaciones/rendir/<inst_id>/<alumno_id>` | GET, POST | `rendir` | `@login_required` | Rendir evaluación (3 bloqueos manuales) |
| `/evaluaciones/instrumento/<inst_id>/resultados` | GET | `resultados` | `@login_required` | Ver resultados |
| `/evaluaciones/instrumento/<inst_id>/nota-manual` | POST | `guardar_nota_manual` | `@login_required` + permiso Eval 2 | Guardar notas manuales |
| `/evaluaciones/instrumento/<inst_id>/eliminar-nota-manual/<opr_id>` | POST | `eliminar_nota_manual` | `@login_required` + permiso Eval 2 | Eliminar nota manual |
| `/evaluaciones/instrumento/<inst_id>/visibilidad` | POST | `cambiar_visibilidad` | `@login_required` + permiso Eval 2 | Publicar/ocultar + gestión calendario |
| `/evaluaciones/instrumento/<inst_id>/imprimir` | GET | `imprimir_evaluacion` | `@login_required` + permiso Eval 1 | Vista imprimible A4 |

---

## 4. Sistema de Permisos

### 4.1 Decoradores utilizados

| Decorador | Fuente | Uso |
|-----------|--------|-----|
| `@login_required` | Flask-Login | Todas las rutas |
| `@permiso_requerido('Evaluaciones', nivel)` | `auth/routes.py` | Rutas de lectura (nivel 1) y escritura (nivel 2) |
| Verificación manual en `rendir()` | — | 3 bloqueos de seguridad inline |

### 4.2 Helper `_es_nivel_2_evaluaciones()`

Retorna `True` si el usuario tiene `RoleId=1` (admin) o `PermissionLevel >= 2` en el módulo "Evaluaciones". Replica la lógica de `permiso_requerido` pero retorna bool en lugar de abortar.

### 4.3 Permisos en templates

| Elemento | Condición | Template |
|----------|-----------|----------|
| Botón "+ Nueva Evaluación" | `user_permisos.get('Evaluaciones', 0) >= 2` | `unidades.html` |
| Botón "Preguntas" | `user_permisos.get('Evaluaciones', 0) >= 2` | `unidades.html` |
| Botón "Publicar/Ocultar" | `user_permisos.get('Evaluaciones', 0) >= 2` | `unidades.html` |
| Botón "Resultados" | Siempre visible | `unidades.html` |
| Botón "Guardar Notas Manuales" | `user_permisos.get('Evaluaciones', 0) >= 2` | `resultados.html` |
| Checkbox nota manual | `user_permisos.get('Evaluaciones', 0) >= 2` | `resultados.html` |
| Columna "Simulación Rápida" | `user_permisos.get('Evaluaciones', 0) >= 2` + `IsDigital` | `resultados.html` |
| Botón "Re-rendir" | `user_permisos.get('Evaluaciones', 0) >= 2` | `resultados.html` |
| Link "Rendir Test" | `r.alumno.PersonId == current_user.PersonId` | `resultados.html` |

---

## 5. Funcionalidades de Negocio

### 5.1 Listar grados
- Consulta `Organization` con `RefOrganizationTypeId=46`.
- Para cada grado cuenta evaluaciones totales via join a asignaturas e instrumentos.

### 5.2 Asignaturas por grado
- Busca asignaturas (TypeId=22) hijas del grado.
- Cuenta evaluaciones por asignatura.

### 5.3 Unidades por asignatura
- Carga `EdugestCurriculumPlan` agrupados por `UnitTitle`.
- Determina nivel de permisos (Admin=2, sino consulta `EdugestRolePermission` para "Evaluaciones").
- Nivel 2 ve todas las evaluaciones, nivel 1 solo las visibles (`IsVisible=True`).

### 5.4 Crear evaluación (flujo principal)
- Campos: título, tipo (Sumativa/Formativa/Diagnóstica/Calificativa/Otra), clase vinculada, fecha opcional, digital (checked por defecto).
- Crea `EdugestAssessmentInstrument` con `IsVisible=False` (borrador).
- Si se proporciona fecha, crea `EdugestCalendarEvent`.

### 5.5 Crear evaluación (flujo alternativo desde `index.html`)
- Formulario simplificado sin tipo ni fecha.
- Endpoint `crear_instrumento` redirige hardcoded a `grado_id=1`.

### 5.6 Diseñar preguntas
- Soporta 5 tipos: Alternativa, Verdadero/Falso, Desarrollo, Relación de Columnas, Completar.
- Upload de imágenes habilitado en backend (valida extensión, guarda en `app/static/uploads/preguntas/`) pero deshabilitado en frontend.
- Preguntas se crean con `db.session.flush()` para obtener ID antes de crear opciones.

### 5.7 Rendir evaluación (3 bloqueos de seguridad)
1. **Visibilidad**: Si `IsVisible=False`, solo nivel 2 puede acceder.
2. **Digital**: Si `IsDigital=False`, solo nivel 2 puede acceder (presencial).
3. **Identidad**: Solo el propio alumno puede rendir su examen (admins exceptuados).

Busca matrícula en cursos (TypeId=21) del grado padre, no en la asignatura directamente.

**Calificación automática:**
- Alternativa/V-F: puntos si la opción es correcta.
- Relación de Columnas: puntos parciales por emparejamiento correcto.
- Completar: puntos parciales por respuesta correcta (case-insensitive).
- Desarrollo: `ScoreEarned=None` (corrección manual).
- Fórmula: `nota = 1 + (puntaje_obtenido / puntaje_maximo) * 6`.

### 5.8 Resultados
- **Nivel 2**: Ve todos los cursos del grado, todos los alumnos.
- **Nivel 1 (alumno)**: Solo ve su propio curso y compañeros.
- Deduplicación por `PersonId` para evitar duplicados.
- Muestra nota automática y nota manual (si existe).

### 5.9 Notas manuales
- `guardar_nota_manual`: Procesa campos `nota_manual_{opr_id}` y `eliminar_nota_{opr_id}`. Valida rango 1.0-7.0.
- `eliminar_nota_manual`: Elimina registro manual, revierte a automática.

### 5.10 Publicar/ocultar + calendario
- **Publicar**: Crea `EdugestCalendarEvent` si no existe uno para el instrumento. Apunta al grado padre como `TargetOrganizationId`.
- **Ocultar**: Elimina el evento del calendario vinculado.

### 5.11 Imprimir
- Template standalone (no hereda `base.html`).
- Formato A4 simulado (210mm x 297mm).
- Cabecera institucional, campos para datos del estudiante (a llenar a mano).
- Page break cada 3 preguntas, `avoid-break` para no cortar preguntas.

---

## 6. Análisis por Archivo

### 6.1 `routes.py` — Backend

Archivo extenso (~400 líneas) con 15 rutas y 4 helpers. Segundo módulo más grande del sistema.

### 6.2 `index.html` — Panel Principal

Panel alternativo con lista de asignaturas para crear instrumento y banco de instrumentos. Posiblemente obsoleto o en desuso.

### 6.3 `grados.html` — Selector de Grado

Cards clickeables con conteo de evaluaciones. Grados deshabilitados con `opacity-50` pero siguen siendo links funcionales.

### 6.4 `asignaturas.html` — Selector de Asignatura

Grid de cards con nombre, código, conteo de evaluaciones, y botón "Ver Unidades y Clases".

### 6.5 `unidades.html` — Unidades con Evaluaciones

Accordion por unidad con clases y evaluaciones vinculadas. Botones según permisos: nueva evaluación, preguntas, resultados, publicar/ocultar.

### 6.6 `crear_evaluacion.html` — Formulario Crear Evaluación

Campos: título, tipo de evaluación, clase vinculada, fecha opcional, digital. Flujo principal.

### 6.7 `crear_instrumento.html` — Formulario Alternativo

Versión simplificada sin tipo ni fecha. Endpoint apunta a `crear_evaluacion_clase_post`. Posiblemente obsoleto.

### 6.8 `disenar_preguntas.html` — Diseñador de Preguntas

Layout 2 columnas. Formulario lateral con 5 tipos de pregunta (toggle via JS). Lista de preguntas guardadas con renderizado por tipo. Upload de imagen deshabilitado en frontend pero habilitado en backend.

### 6.9 `resultados.html` — Consolidado de Calificaciones

Tabla con estudiante, puntaje, nota final, estado, simulación rápida, nota manual. JS complejo para toggle de nota manual, actualización de estado, y botones guardar. Fila resaltada para notas manuales.

### 6.10 `rendir.html` — Entorno de Examen Virtual

Renderiza 5 tipos de pregunta. Header dark con nombre del estudiante. Botón "Finalizar y Enviar Examen" sin confirmación.

### 6.11 `imprimir.html` — Vista Imprimible A4

Standalone con Tailwind CDN. Formato carta institucional. Page break cada 3 preguntas. Circulos vacíos para alternativas, líneas para desarrollo, espacios inline para completar.

---

## 7. Hallazgos de Auditoría

### 7.1 Seguridad — ALTO

#### [S1] Sin protección CSRF
Ningún formulario POST incluye token CSRF. Afecta a: crear evaluación, crear pregunta, rendir evaluación (submit de respuestas), guardar nota manual, eliminar nota manual, cambiar visibilidad.
- **Archivos:** Todos los templates con forms POST
- **Riesgo:** ALTO
- **Recomendación:** Implementar protección CSRF global con `Flask-WTF`.

#### [S2] Upload de imágenes sin validación de contenido
`disenar_preguntas_post` acepta archivos con extensiones png/jpg/jpeg/gif pero no valida tipo MIME ni tamaño máximo. Un archivo malicioso con extensión cambiada podría subirse.
- **Archivo:** `routes.py`, función `disenar_preguntas_post`
- **Riesgo:** MEDIO-ALTO
- **Recomendación:** Validar MIME type, limitar tamaño (ej: 5MB), escanear contenido.

#### [S3] Rendir evaluación sin confirmación
El botón "Finalizar y Enviar Examen" envía el formulario inmediatamente sin dialogo de confirmación. Un click accidental envía todo.
- **Archivo:** `rendir.html`
- **Riesgo:** MEDIO
- **Recomendación:** Agregar `confirm()` de JavaScript.

### 7.2 Seguridad — MEDIO

#### [S4] Rutas sin `@permiso_requerido`
Las siguientes rutas solo tienen `@login_required`:
- `asignaturas_por_grado` (GET) — muestra asignaturas con conteo de evaluaciones
- `unidades_asignatura` (GET) — muestra unidades y evaluaciones (filtra visibles para nivel 1)
- `rendir` (GET, POST) — tiene 3 bloqueos manuales inline en lugar de decorador
- **Riesgo:** MEDIO

#### [S5] Re-rendir sin confirmación
Un profesor (nivel 2) puede re-rendir la evaluación de cualquier alumno, sobreescribiendo respuestas anteriores. No hay confirmación ni registro de auditoría.
- **Archivo:** `resultados.html`, `rendir()`
- **Riesgo:** MEDIO

#### [S6] Error silencioso en fecha de calendario
`except ValueError: pass` si la fecha del formulario es inválida.
- **Archivo:** `routes.py`, `crear_evaluacion_clase_post`
- **Riesgo:** BAJO

#### [S7] `crear_instrumento` redirect hardcoded a grado_id=1
`return redirect(url_for('evaluaciones.asignaturas_por_grado', grado_id=1))`. Código muerto/placeholder.
- **Archivo:** `routes.py`, `crear_instrumento`
- **Riesgo:** BAJO (no afecta funcionalidad principal)

### 7.3 Rendimiento

#### [P1] N+1 queries en múltiples funciones
- `listar_grados`: query adicional por cada grado.
- `asignaturas_por_grado`: query por cada asignatura.
- `unidades_asignatura`: queries por cada plan/clase.
- `rendir`: queries por cada pregunta y opción.
- `resultados`: queries por cada matrícula (Person, PersonIdentifier, StudentResponse).
- **Riesgo:** MEDIO
- **Recomendación:** Usar `joinedload` o queries agregadas.

#### [P2] Sin paginación
Todos los grados, asignaturas, preguntas y resultados se cargan sin paginación.
- **Riesgo:** BAJO-MEDIO

### 7.4 Arquitectura

#### [A1] Dos formularios de crear evaluación
`crear_evaluacion.html` (flujo principal con todos los campos) y `crear_instrumento.html` (simplificado sin tipo ni fecha). Confusión sobre cuál usar.

#### [A2] Template `index.html` posiblemente obsoleto
Muestra todas las asignaturas sin filtrar por grado, diferente al flujo principal.

#### [A3] Upload de imagen deshabilitado en frontend pero habilitado en backend
`disenar_preguntas.html` tiene `<input type="file" disabled>` pero el backend procesa archivos. Inconsistencia.

#### [A4] Campo `texto_completar` no procesado por backend
El textarea para texto con espacios en "Completar" se envía pero el backend no lo usa.

#### [A5] Verificación de permisos inconsistente
Algunas rutas usan `@permiso_requerido`, otras usan `_es_nivel_2_evaluaciones()`, `rendir` tiene bloqueos manuales inline. Tres patrones diferentes.

#### [A6] Integración con módulo calendario
`cambiar_visibilidad` crea/elimina `EdugestCalendarEvent` automáticamente. Integración cross-modulo.

#### [A7] Sin eliminación de evaluaciones o preguntas
No hay rutas para eliminar instrumentos, preguntas o respuestas. Solo crear y modificar visibilidad.

### 7.5 Frontend

#### [F1] Template `imprimir.html` standalone con Tailwind CDN
No hereda de `base.html`. Usa `cdn.tailwindcss.com` (versión desarrollo).

#### [F2] Inconsistencia en letras del abecedario
`rendir.html` usa minúsculas (`abcdefghijklmnopqrstuvwxyz`), `imprimir.html` usa mayúsculas (`ABCDEFGHIJKLMNOPQRSTUVWXYZ`).

#### [F3] JS complejo en `resultados.html`
Funciones `toggleManual`, `updateEstado`, `refreshGuardarBtn`, `updateContador` manejan la lógica de notas manuales. Complejo pero funcional.

#### [F4] Completar depende de `[___]` literal
Tanto en `disenar_preguntas.html` como en `rendir.html`, el template usa `texto.split('[___]')` para insertar campos. Variaciones como `[__]` o `[____]` no funcionarían.

---

## 8. Resumen de Hallazgos por Severidad

### Crítico (0)
Ninguno.

### Alto (2)
- [S1] Sin protección CSRF
- [S2] Upload de imágenes sin validación de contenido

### Medio (5)
- [S3] Rendir evaluación sin confirmación
- [S4] Rutas sin `@permiso_requerido` (3 rutas)
- [S5] Re-rendir sin confirmación ni auditoría
- [P1] N+1 queries en múltiples funciones
- [A5] Verificación de permisos inconsistente (3 patrones)

### Bajo (7)
- [S6] Error silencioso en fecha de calendario
- [S7] `crear_instrumento` redirect hardcoded a grado_id=1
- [P2] Sin paginación
- [A1] Dos formularios de crear evaluación
- [A2] Template `index.html` posiblemente obsoleto
- [A4] Campo `texto_completar` no procesado por backend
- [A7] Sin eliminación de evaluaciones o preguntas

---

## 9. Endpoint Map Visual

```
GET  /evaluaciones/                                              → index()                      (@login_required)
GET  /evaluaciones/grados                                        → listar_grados()              (permiso Eval 1)
GET  /evaluaciones/grado/<grado_id>/asignaturas                  → asignaturas_por_grado()      (SIN permiso requerido)
GET  /evaluaciones/asignatura/<org_id>/unidades                  → unidades_asignatura()        (SIN permiso requerido)
GET  /evaluaciones/asignatura/<org_id>/nuevo                     → crear_instrumento()          (permiso Eval 1) [REDIRECT]
POST /evaluaciones/asignatura/<org_id>/nuevo                     → crear_instrumento()          (permiso Eval 1) [REDIRECT]
GET  /evaluaciones/clase/<plan_id>/nueva-evaluacion              → crear_evaluacion_clase()     (permiso Eval 1)
POST /evaluaciones/clase/<plan_id>/nueva-evaluacion              → crear_evaluacion_clase_post() (permiso Eval 2)
GET  /evaluaciones/disenar_preguntas/<inst_id>                   → disenar_preguntas()          (permiso Eval 1)
POST /evaluaciones/disenar_preguntas/<inst_id>/crear             → disenar_preguntas_post()     (permiso Eval 2)
GET  /evaluaciones/rendir/<inst_id>/<alumno_id>                  → rendir()                     (@login_required + bloqueos manuales)
POST /evaluaciones/rendir/<inst_id>/<alumno_id>                  → rendir()                     (@login_required + bloqueos manuales)
GET  /evaluaciones/instrumento/<inst_id>/resultados              → resultados()                 (@login_required)
POST /evaluaciones/instrumento/<inst_id>/nota-manual             → guardar_nota_manual()        (permiso Eval 2)
POST /evaluaciones/instrumento/<inst_id>/eliminar-nota-manual/<opr_id> → eliminar_nota_manual() (permiso Eval 2)
POST /evaluaciones/instrumento/<inst_id>/visibilidad             → cambiar_visibilidad()        (permiso Eval 2)
GET  /evaluaciones/instrumento/<inst_id>/imprimir                → imprimir_evaluacion()        (permiso Eval 1)
```

---

## 10. Diagrama de Flujo Principal

```
Grados (listar_grados)
  └── Asignaturas (asignaturas_por_grado)
      └── Unidades (unidades_asignatura)
          ├── Crear Evaluación (crear_evaluacion_clase)
          │   └── → unidades_asignatura
          ├── Diseñar Preguntas (disenar_preguntas)
          │   └── Crear Pregunta (disenar_preguntas_post)
          ├── Resultados (resultados)
          │   ├── Guardar Nota Manual (guardar_nota_manual)
          │   ├── Eliminar Nota Manual (eliminar_nota_manual)
          │   └── Rendir/Re-rendir (rendir)
          ├── Publicar/Ocultar (cambiar_visibilidad)
          │   └── → crear/eliminar EdugestCalendarEvent
          └── Imprimir (imprimir_evaluacion)
```

---

## 11. Integración con Otros Módulos

| Módulo | Integración |
|--------|-------------|
| `libro_digital` | `libro_digital/unidades.html` referencia endpoints de evaluaciones (`disenar_preguntas`, `resultados`, `crear_evaluacion_clase`) |
| `calendario` | `cambiar_visibilidad` crea/elimina `EdugestCalendarEvent` al publicar/ocultar |
| `auth` | Usa `permiso_requerido` de `auth/routes.py` |
| `portada` | Link de fallback "Volver al Inicio" en `resultados.html` |

---

*Auditoría generada a partir del análisis de los 11 archivos del módulo evaluaciones (1 routes.py + 10 templates).*
```

---
