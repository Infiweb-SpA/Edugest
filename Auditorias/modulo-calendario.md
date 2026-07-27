## Analisis del Archivo 3 (calendario): `index.html`



### Proposito
Template Jinja2 que extiende `base.html`. Calendario academico mensual con grilla interactiva (Alpine.js), leyenda de tipos, panel de detalle por dia, y formulario de creacion de eventos.

### Datos del backend

| Variable | Contenido |
|----------|-----------|
| `year`, `month` | Integer: ano y mes actual |
| `month_name` | String: nombre del mes en espanol |
| `cal` | Lista de semanas (de `calendar.monthcalendar`) |
| `events_by_day` | Dict: dia → lista de eventos |
| `event_types` | Dict: tipo → configuracion de color |
| `nivel_permiso` | Integer: nivel de permiso Calendario |
| `hoy` | Date: fecha actual |
| `prev_year`, `prev_month` | Integer: mes anterior |
| `next_year`, `next_month` | Integer: mes siguiente |
| `grados` | Lista de grados (solo nivel 2) |
| `asignaturas` | Lista de asignaturas (solo nivel 2) |

### Estructura

1. **Navegacion mensual**: Flechas anterior/siguiente + titulo del mes + boton "Nuevo Evento" (solo nivel 2).

2. **Leyenda de tipos**: Puntos de colores con labels para cada tipo de evento.

3. **Grilla del calendario**: 7 columnas (Lun-Dom), celdas clickeables con Alpine.js (`selectedDay`), max 3 eventos por dia con "+N mas", highlight del dia actual (circulo indigo), highlight del dia seleccionado (ring indigo).

4. **Panel de detalle**: Se muestra al hacer click en un dia. Lista eventos con colores por tipo, descripcion, link a evaluacion (si tiene InstrumentId), boton eliminar (solo nivel 2). Mensaje "sin eventos" si el dia no tiene eventos.

5. **Formulario crear evento** (solo nivel 2): Titulo, fecha, tipo de evento, organizacion destino (grados + asignaturas con optgroup), descripcion. Toggle con Alpine.js (`showForm`).

### Alpine.js

```javascript
x-data="{ selectedDay: null, showForm: false, eventDays: {{ events_by_day.keys()|list }} }"
```

- `selectedDay`: Dia seleccionado en la grilla.
- `showForm`: Toggle del formulario de creacion.
- `eventDays`: Lista de dias con eventos (para mostrar "sin eventos").

### Permisos en template

| Elemento | Condicion |
|----------|-----------|
| Boton "Nuevo Evento" | `nivel_permiso >= 2` |
| Boton eliminar evento | `nivel_permiso >= 2` |
| Formulario crear evento | `nivel_permiso >= 2` |

### Endpoints referenciados

| Endpoint | Metodo | Proposito |
|----------|--------|-----------|
| `calendario.index` | GET | Navegacion mes anterior/siguiente |
| `calendario.crear_evento` | POST | Crear evento |
| `calendario.eliminar_evento(event_id)` | POST | Eliminar evento |
| `evaluaciones.resultados(inst_id)` | GET | Ver evaluacion vinculada |

### Observaciones para la auditoria

1. **Sin CSRF en form POST**: Tanto crear como eliminar eventos son forms POST sin token CSRF.

2. **Eliminar con confirmacion**: `onsubmit="return confirm('¿Eliminar este evento?')"`. Patron correcto.

3. **Link a evaluacion**: Si el evento tiene `InstrumentId`, muestra link "Ver evaluacion →". Integracion cross-modulo con evaluaciones.

4. **Select de organizacion destino con optgroup**: Separa grados y asignaturas visualmente. UX clara.

5. **Max 3 eventos visibles por dia**: `events_by_day.get(day, [])[:3]`. Si hay mas, muestra "+N mas". Evita saturacion visual.

6. **Dia actual resaltado**: Circulo indigo con texto blanco. Patron visual claro.

7. **Alpine.js con `x-cloak`**: Oculta panel de detalle y formulario hasta que Alpine.js inicializa. Evita flash de contenido.

8. **Eventos renderizados por dia en el panel de detalle**: Genera un `x-show` por cada dia con eventos. Con muchos dias con eventos, el HTML podria ser extenso.

---

### Modulo calendario: Resumen

| # | Archivo | Hallazgos clave |
|---|---------|-----------------|
| 1 | `__init__.py` | Importa Blueprint desde routes.py |
| 2 | `routes.py` | 3 rutas, visibilidad compleja por rol, integracion evaluaciones, sin CSRF, sin edicion, caracteres corruptos |
| 3 | `index.html` | Calendario Alpine.js, grilla interactiva, panel detalle, form crear, sin CSRF |

---

Aqui va el `.md`:

```markdown
# Auditoría del Módulo: Calendario

## 1. Resumen General

El módulo Calendario proporciona un calendario académico institucional con vista mensual. Permite crear y eliminar eventos de diferentes tipos (Evaluación, Vacunación, Taller, etc.), con filtrado automático de visibilidad según el rol del usuario y su relación con las organizaciones del establecimiento. Integra eventos de evaluaciones del módulo Evaluaciones, ocultando aquellos que no están publicados.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/calendario/__init__.py` | Python | Importa `calendario_bp` desde routes.py |
| `app/modules/calendario/routes.py` | Python | Backend: 3 rutas, lógica de visibilidad |
| `app/templates/calendario/index.html` | Jinja2/HTML | Calendario mensual con Alpine.js |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2, Alpine.js, Python `calendar`.

**Prefijo de rutas:** `/calendario`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `EdugestCalendarEvent` | Edugest | Eventos (Title, Description, EventDate, EventType, TargetOrganizationId, CreatedBy, InstrumentId) |
| `EdugestAssessmentInstrument` | Edugest | Verificar publicación de evaluaciones (IsVisible) |
| `EdugestModule` | Edugest | Verificación de permisos |
| `EdugestRolePermission` | Edugest | Nivel de permiso |
| `Organization` | Mineduc | Grados (TypeId=46), asignaturas (TypeId=22), cursos (TypeId=21) |
| `OrganizationRelationship` | Mineduc | Jerarquía organizacional |
| `OrganizationPersonRole` | Mineduc | Matrícula y roles activos |
| `PersonRelationship` | Mineduc | Relación apoderado-hijo |

### 2.2 Tipos de evento

| Tipo | Label | Color |
|------|-------|-------|
| `Evaluacion` | Evaluación | Azul |
| `Vacunacion` | Vacunación | Rosa |
| `Taller` | Taller | Verde |
| `ActividadExtracurricular` | Actividad Extracurricular | Púrpura |
| `Reunion` | Reunión | Naranja |
| `Feriado` | Feriado | Gris |
| `Otro` | Otro | Slate |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/calendario/` | GET | `index` | `@login_required` + permiso Cal 1 | Vista mensual |
| `/calendario/evento` | POST | `crear_evento` | `@login_required` + permiso Cal 2 | Crear evento |
| `/calendario/evento/<id>/eliminar` | POST | `eliminar_evento` | `@login_required` + permiso Cal 2 | Eliminar evento |

---

## 4. Sistema de Permisos y Visibilidad

### 4.1 Helpers de permisos

| Helper | Propósito |
|--------|-----------|
| `_get_nivel_permiso()` | Nivel de permiso para Calendario |
| `_get_nivel_permiso_evaluaciones()` | Nivel de permiso para Evaluaciones |
| `_get_org_ids_for_user()` | OrganizationIds visibles según rol |

### 4.2 Visibilidad por rol

| Rol | Organizaciones visibles |
|-----|------------------------|
| Admin (RoleId=1) | `None` (ve todo) |
| Estudiante (RoleId=6) | Curso + grado + asignaturas del grado |
| Apoderado (RoleId=5) | Cursos de sus hijos + grados + asignaturas |
| Otros | Organizaciones donde tiene rol + padre + hermanas |

### 4.3 Integración con Evaluaciones

Eventos de tipo 'Evaluación' con `InstrumentId` se ocultan si el instrumento tiene `IsVisible=False` y el usuario tiene permiso de Evaluaciones < 2. Consulta batch para eficiencia.

---

## 5. Hallazgos de Auditoría

### 5.1 Seguridad — ALTO

#### [S1] Sin protección CSRF
`crear_evento` y `eliminar_evento` son forms POST sin token CSRF.
- **Archivos:** `index.html`
- **Riesgo:** ALTO

### 5.2 Seguridad — MEDIO

#### [S2] Eliminar evento sin verificación de propiedad
Cualquier usuario nivel 2 puede eliminar cualquier evento, incluyendo eventos de evaluaciones de otros profesores.
- **Riesgo:** MEDIO

### 5.3 Rendimiento

#### [P1] N+1 queries en `_get_org_ids_for_user()`
Consultas secuenciales para estudiantes, apoderados, y profesores. Potencialmente muchas queries.
- **Riesgo:** MEDIO

#### [P2] Panel de detalle genera HTML extenso
Un `x-show` por cada día con eventos. Con muchos días, el HTML crece significativamente.
- **Riesgo:** BAJO

### 5.4 Arquitectura

#### [A1] Sin edición de eventos
Solo crear y eliminar. No hay ruta para modificar un evento existente.

#### [A2] Caracteres corruptos en comentarios
Múltiples comentarios tienen caracteres UTF-8 mal codificados (ej: `CONFIGURACI脫N`, `Reuni贸n`).
- **Riesgo:** BAJO (no afecta funcionalidad)

#### [A3] Verificación de permisos duplicada
`_get_nivel_permiso()` replica la lógica de `permiso_requerido`. Patrón consistente con otros módulos pero duplicado.

---

## 6. Resumen de Hallazgos por Severidad

### Crítico (0)
Ninguno.

### Alto (1)
- [S1] Sin protección CSRF

### Medio (2)
- [S2] Eliminar evento sin verificación de propiedad
- [P1] N+1 queries en visibilidad

### Bajo (3)
- [P2] Panel de detalle con HTML extenso
- [A1] Sin edición de eventos
- [A2] Caracteres corruptos en comentarios

---

## 7. Endpoint Map Visual

```
GET  /calendario/                      → index()            (permiso Cal 1)
POST /calendario/evento                → crear_evento()     (permiso Cal 2)
POST /calendario/evento/<id>/eliminar  → eliminar_evento()  (permiso Cal 2)
```

---

## 8. Integración Cross-Módulo

| Módulo | Integración |
|--------|-------------|
| `evaluaciones` | Eventos de evaluación se ocultan si no publicadas. Link "Ver evaluación" en panel de detalle. |
| `evaluaciones` | `cambiar_visibilidad()` en evaluaciones crea/elimina eventos en este calendario. |

---

*Auditoría generada a partir del análisis de los 3 archivos del módulo calendario.*
```

---
