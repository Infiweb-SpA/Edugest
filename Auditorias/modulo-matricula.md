Perfecto, entonces ya tenemos el modulo completo analizado. Son 4 archivos:

1. `formulario.html` — Formulario de matricula
2. `listar.html` — Listado de estudiantes
3. `ver.html` — Ficha individual del estudiante
4. `routes.py` — Backend/logica de negocio

---

Aqui va el documento completo de auditoria para el `.md`:

---

```markdown
# Auditoría del Módulo: Matrícula

## 1. Resumen General

El módulo de Matrícula es un sistema de registro y gestión de estudiantes para un establecimiento educacional chileno. Permite crear, listar y visualizar la ficha completa de estudiantes matriculados, incluyendo datos personales, apoderados, información médica, PIE, socioeconómica, autorizaciones y documentación.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/matricula/__init__.py` | Python | Paquete vacío (estructura) |
| `app/modules/matricula/routes.py` | Python | Backend: rutas, helpers, lógica de negocio |
| `app/templates/matricula/formulario.html` | Jinja2/HTML | Formulario de alta/edición de estudiante |
| `app/templates/matricula/listar.html` | Jinja2/HTML | Listado de estudiantes matriculados |
| `app/templates/matricula/ver.html` | Jinja2/HTML | Ficha individual de solo lectura |

**Tecnologías:** Flask, Jinja2, SQLAlchemy ORM, Flask-Login, HTML/CSS/JS vanilla.

**Prefijo de rutas:** `/matricula`

---

## 2. Modelo de Datos

### 2.1 Tablas MINEDUC (app.models.mineduc)

| Modelo | Uso en el módulo |
|--------|-----------------|
| `Person` | Entidad central (estudiantes y apoderados) |
| `PersonIdentifier` | Identificadores: RUT (sys 51), IPE (sys 52), N° lista (sys 54), N° matrícula (sys 55) |
| `Organization` | Niveles (type 40), Grados (type 46), Cursos (type 21) |
| `OrganizationRelationship` | Jerarquía padre-hijo entre organizaciones |
| `OrganizationPersonRole` | Rol del estudiante (RoleId=6) en un curso |
| `PersonAddress` | Dirección/residencia |
| `PersonTelephone` | Teléfonos |
| `PersonRelationship` | Relación estudiante-apoderado (RefPersonRelationshipId=31) |
| `PersonDegreeOrCertificate` | Nivel educacional (de apoderados) |
| `PersonEmailAddress` | Correos electrónicos |

### 2.2 Tablas EDUGEST (app.models.edugest)

| Modelo | Uso |
|--------|-----|
| `EdugestModule` | Control de módulo habilitado/deshabilitado |
| `EdugestRolePermission` | Permisos por rol (0=sin acceso, 1=lectura, 2=lectura+escritura) |
| `EdugestStudentEnrollment` | Datos extendidos de matrícula (~50 campos) |
| `EdugestEmergencyContact` | Contactos de emergencia (máx 2, ordenados por `Orden`) |
| `EdugestStudentHealth` | Datos médicos |
| `EdugestStudentPIE` | Datos PIE |
| `EdugestPersonRelationshipDetail` | Detalles adicionales de la relación apoderado-estudiante |

### 2.3 Constantes de referencia

| Constante | Significado |
|-----------|-------------|
| `RoleId = 6` | Rol de estudiante |
| `RefPersonRelationshipId = 31` | Relación estudiante-apoderado |
| `RefOrganizationTypeId = 40` | Nivel educativo |
| `RefOrganizationTypeId = 46` | Grado |
| `RefOrganizationTypeId = 21` | Curso (letra) |
| `RefPersonIdentificationSystemId = 51` | RUT |
| `RefPersonIdentificationSystemId = 52` | IPE |
| `RefPersonIdentificationSystemId = 54` | N° lista |
| `RefPersonIdentificationSystemId = 55` | N° matrícula |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Permiso requerido | Descripción |
|------|--------|---------|-------------------|-------------|
| `/matricula/` | GET | `listar_estudiantes` | ≥1 (lectura) | Listado de estudiantes matriculados |
| `/matricula/nuevo` | GET, POST | `nuevo_estudiante` | ≥2 (escritura) | Formulario y creación de estudiante |
| `/matricula/<person_id>` | GET | `ver_estudiante` | ≥1 (lectura) | Ficha detalle de estudiante |
| `/matricula/ajax/grados/<nivel_id>` | GET | `ajax_grados` | Solo verifica módulo | Grados de un nivel (AJAX) |
| `/matricula/ajax/cursos/<grado_id>` | GET | `ajax_cursos` | Solo verifica módulo | Cursos de un grado (AJAX) |
| `/matricula/ajax/buscar_estudiante` | GET | `ajax_buscar_estudiante` | Solo verifica módulo | Búsqueda por nombre/RUT (AJAX) |
| `/matricula/ajax/estudiante/<person_id>` | GET | `ajax_datos_estudiante` | Solo verifica módulo | Datos completos para precarga (AJAX) |

---

## 4. Análisis por Archivo

### 4.1 routes.py — Backend

#### Funcionalidades principales

- **Listado con deduplicación por RUT**: Muestra solo la matrícula más reciente por estudiante (por `EntryDate`). Si no tiene RUT, usa `ID_{PersonId}` como clave.
- **Creación con detección de duplicados**: Al crear, busca si ya existe una persona con el mismo RUT. Si existe, cierra roles anteriores (`ExitDate`) y crea uno nuevo (re-matrícula).
- **Precarga con validación de `person_id_precargado`**: Valida que el RUT del estudiante precargado coincida con el RUT enviado en el formulario. Si no coincide, ignora la precarga.
- **Apoderados por posición (slot)**: Usa la posición (0, 1, 2) en la lista ordenada de relaciones para determinar titular/suplente1/suplente2. Incluye lógica de 4 pasos: leer datos, determinar slot, buscar existente o crear nuevo.
- **UPSERT generalizado**: Todos los datos complementarios (enrollment, salud, PIE, contactos) usan patrón buscar-si-existe-actualizar-sino-crear.
- **Control de acceso por módulo**: Verifica si el módulo "Matrícula" está habilitado y obtiene el nivel de permiso del usuario actual.
- **Normalización de RUT**: Limpia y formatea a `xx.xxx.xxx-x`. **No valida dígito verificador.**

#### Helpers

| Función | Descripción |
|---------|-------------|
| `_parse_date(campo)` | Parsea fecha `YYYY-MM-DD` del formulario |
| `_parse_int(campo)` | Parsea entero del formulario |
| `_parse_bool(campo)` | Retorna `True` si valor es `'1'` |
| `normalizar_rut(rut)` | Formatea RUT a `xx.xxx.xxx-x` (sin validación de dígito) |
| `verificar_modulo_habilitado()` | Verifica si el módulo está habilitado |
| `obtener_jerarquia_curso(curso_id)` | Recorre jerarquía hacia arriba para obtener nivel/grado/letra |
| `get_permiso_modulo(module_name)` | Retorna nivel de permiso (0/1/2) del usuario actual |
| `obtener_apoderados_estudiante(person_id)` | Retorna lista de apoderados con datos enriquecidos |
| `crear_apoderado_estudiante(...)` | Lógica completa de crear/actualizar apoderado |
| `_serialize_estudiante(person_id)` | Serializa todos los datos para precarga AJAX |

### 4.2 formulario.html — Formulario de Matrícula

#### Estructura

18 secciones con navegación sticky numerada y barra de progreso:

| # | Sección | Obligatoriedad |
|---|---------|----------------|
| 0 | Precarga desde matrícula anterior | — |
| 1 | Datos Personales | Parcial (nombre, apellido paterno) |
| 1b | Datos Adicionales | Ninguno |
| 2 | Identificadores MINEDUC | RUT obligatorio |
| 3 | Residencia y Matrícula | Dirección, nivel, grado, curso, fecha matrícula |
| 4 | Apoderado Titular | Todos los campos críticos |
| 5 | Apoderado Suplente 1 | Opcional |
| 6 | Apoderado Suplente 2 | Opcional |
| 7 | Contactos de Emergencia (×2) | Ninguno |
| 8 | Información Médica | Solo alergias |
| 9 | Programa PIE | Ninguno |
| 10 | Información Académica | Ninguno |
| 11 | Información Socioeconómica | Ninguno |
| 12 | Información SEP | Ninguno |
| 13 | Información Cultural | Opcional |
| 14 | Transporte Escolar | Opcional |
| 15 | Autorizaciones | Ninguno |
| 16 | Documentación Entregada | Ninguno |

#### Funcionalidades JavaScript

- **Cascada AJAX Nivel → Grado → Curso** con endpoints `/matricula/ajax/grados/{id}` y `/matricula/ajax/cursos/{id}`.
- **Campos condicionales** con transiciones CSS: IPE para extranjeros, cantidad de computadores, colegio de procedencia.
- **Dirección sincronizada** entre estudiante y apoderado titular.
- **Navegación activa al scroll** con resaltado de sección actual.
- **Barra de progreso** que calcula porcentaje de campos obligatorios completados.
- **Autocomplete de matrícula anterior** con búsqueda AJAX (min 3 caracteres, debounce 300ms).
- **Precarga de apoderados suplentes** con opción de mantener o no.

### 4.3 listar.html — Listado de Estudiantes

#### Estructura

- **Encabezado** con contador de estudiantes y botón "Nuevo Estudiante" (condicional a permisos).
- **Barra de búsqueda** con filtrado en tiempo real del lado del cliente.
- **Vista dual responsiva**: tabla desktop (lg+) y tarjetas móvil (<lg).
- **Botón sticky móvil** con contador y botón "Nuevo".
- **Estados vacíos**: sin estudiantes y sin resultados de búsqueda.

#### Funcionalidades JavaScript

- **Filtrado client-side** por nombre, RUT, curso y nivel.
- **Atajos de teclado**: `Ctrl+K` o `/` para enfocar búsqueda.
- **Contadores dinámicos** de resultados visibles.

#### Badges de nivel educativo

| Condición | Color |
|-----------|-------|
| Parvularia/Preescolar | Púrpura |
| Básica | Azul |
| Media | Verde |
| Otro | Gris |

### 4.4 ver.html — Ficha Individual

#### Estructura

16 secciones de solo lectura con navegación sticky:

Identidad, Datos Personales, Residencia, Apoderados (titular + 2 suplentes), Contactos de Emergencia, Información Médica, PIE, Académica, Socioeconómica, SEP, Cultural, Transporte, Autorizaciones, Documentación, Observaciones, Matrículas.

#### Características

- **Secciones condicionales**: La mayoría solo se renderiza si hay datos (`{% if enrollment %}`, `{% if health %}`, etc.).
- **Estados booleanos visuales**: Clases `estado-positivo` (verde) y `estado-negativo` (rojo) para campos Sí/No, Autorizado/No autorizado, Entregado/Pendiente.
- **Información médica destacada**: Enfermedades/alergias en fondo rojo, medicamentos en amarillo, necesidades especiales en naranja.
- **Observaciones en 4 subcategorías**: Académicas, Médicas, Familiares, Establecimiento.
- **Historial de matrículas**: Muestra todas las matrículas (activas e inactivas) con fechas de ingreso y retiro.
- **Sin botón de edición visible** en la ficha.

---

## 5. Hallazgos de Auditoría

### 5.1 Seguridad — CRÍTICO

#### [S1] Sin protección CSRF
El formulario POST no incluye token CSRF. Cualquier sitio podría enviar un formulario malicioso en nombre del usuario autenticado.
- **Archivo:** `routes.py` (ruta `nuevo_estudiante`) + `formulario.html`
- **Riesgo:** Alto
- **Recomendación:** Implementar `Flask-WTF` o `flask_csrf_token` con `{{ csrf_token() }}` en el formulario.

#### [S2] Endpoints AJAX sin validación de permisos de usuario
Los 4 endpoints AJAX (`ajax_grados`, `ajax_cursos`, `ajax_buscar_estudiante`, `ajax_datos_estudiante`) solo verifican que el módulo esté habilitado, pero NO verifican el nivel de permiso del usuario (`get_permiso_modulo`). Un usuario con nivel 0 (sin acceso) podría llamar a estos endpoints.
- **Archivo:** `routes.py`
- **Riesgo:** Alto
- **Recomendación:** Agregar verificación de `get_permiso_modulo('Matrícula') >= 1` en cada endpoint AJAX.

#### [S3] Exposición de datos sensibles sin autorización
`ajax_datos_estudiante` expone toda la información de un estudiante (datos médicos, PIE, contactos de emergencia, apoderados) sin verificar permisos. Esto constituye una vulnerabilidad de acceso no autorizado a datos personales.
- **Archivo:** `routes.py`, función `_serialize_estudiante` y ruta `ajax_datos_estudiante`
- **Riesgo:** Alto
- **Recomendación:** Requerir permiso de lectura (nivel ≥ 1) como mínimo. Idealmente, restringir acceso a datos médicos/PIE a roles específicos.

#### [S4] Exposición de información interna en errores
El bloque `except Exception as e` muestra `str(e)` al usuario, lo cual podría filtrar información interna (nombres de tablas, stack traces, configuración de base de datos).
- **Archivo:** `routes.py`, función `nuevo_estudiante`
- **Riesgo:** Medio
- **Recomendación:** Registrar el error en log del servidor y mostrar mensaje genérico al usuario.

### 5.2 Seguridad — MEDIO

#### [S5] RUT sin validación de dígito verificador
`normalizar_rut()` solo formatea el RUT pero no calcula ni verifica el dígito verificador. Un RUT con dígito incorrecto pasaría la validación.
- **Archivo:** `routes.py`
- **Riesgo:** Medio
- **Recomendación:** Implementar validación de dígito verificador con algoritmo módulo 11.

#### [S6] Regex de RUT no bloquea envío
La validación de formato de RUT (`^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$`) solo genera un `flash("warning")` pero no detiene el proceso. Un RUT mal formateado se guarda igualmente.
- **Archivo:** `routes.py`, función `nuevo_estudiante`
- **Riesgo:** Medio
- **Recomendación:** Convertir warning en error que bloquee el guardado.

### 5.3 Rendimiento

#### [P1] Consulta ineficiente en `ajax_grados`
`OrganizationRelationship.query.all()` carga TODAS las relaciones de organización en memoria y construye un árbol completo para cada request AJAX.
- **Archivo:** `routes.py`, función `ajax_grados`
- **Riesgo:** Medio (depende del volumen de organizaciones)
- **Recomendación:** Usar una consulta recursiva o filtrar directamente por jerarquía padre-hijo.

#### [P2] Sin paginación en listado
Carga todos los roles activos de una sola vez, sin paginación server-side ni client-side.
- **Archivo:** `routes.py` + `listar.html`
- **Riesgo:** Bajo-Medio (depende del volumen de estudiantes)
- **Recomendación:** Implementar paginación server-side con parámetros `page` y `per_page`.

#### [P3] Deduplicación en memoria para listado
La deduplicación por RUT se hace iterando todos los roles en Python, no en la consulta SQL.
- **Archivo:** `routes.py`, función `listar_estudiantes`
- **Riesgo:** Bajo
- **Recomendación:** Mover la lógica de deduplicación a la consulta SQL con `GROUP BY` o subconsulta.

### 5.4 Arquitectura y Mantenibilidad

#### [A1] Sin ruta de edición directa
No existe una ruta `/editar/<person_id>`. Para editar un estudiante, el usuario debería usar `/nuevo` con precarga, lo cual crearía una nueva matrícula en lugar de editar la existente.
- **Archivo:** `routes.py`
- **Recomendación:** Crear ruta `/editar/<person_id>` que reutilice el formulario con datos precargados y actualice en lugar de crear.

#### [A2] Lógica de apoderados por posición (slot)
La identificación de titular/suplente1/suplente2 depende de la posición en la lista ordenada de relaciones. Si se elimina el apoderado titular, el suplente1 pasaría a ser tratado como titular.
- **Archivo:** `routes.py`, función `crear_apoderado_estudiante`
- **Recomendación:** Almacenar el tipo de apoderado (titular/suplente) como atributo explícito en la relación o en `EdugestPersonRelationshipDetail`.

#### [A3] Sin funcionalidad de eliminación
No hay rutas para eliminar estudiantes, apoderados, registros de salud, PIE ni contactos de emergencia.
- **Archivo:** `routes.py`
- **Recomendación:** Evaluar si se necesita eliminación (podría ser una restricción de negocio intencional por auditoría).

#### [A4] Duplicación de código Jinja
Los filtros `selectattr` para extraer `num_lista` y `rut` se repiten idénticamente en las secciones desktop y móvil de `listar.html`.
- **Archivo:** `listar.html`
- **Recomendación:** Extraer a una macro Jinja2 o definir las variables una sola vez antes del bloque condicional.

#### [A5] Badges "Activo" hardcodeados en ver.html
El badge de estado "Activo" en la sección de matrículas siempre se muestra como verde sin condición, lo que sugiere que la consulta podría no filtrar correctamente matrículas inactivas, o que el badge no refleja el estado real.
- **Archivo:** `ver.html`
- **Recomendación:** Condicionar el badge al `ExitDate`: si es `None` → "Activo" (verde), si tiene fecha → "Retirado" (gris/rojo).

### 5.5 Frontend

#### [F1] Caracteres corruptos por encoding
Los templates `ver.html` y `routes.py` presentan caracteres corruptos (`贸`, `铆`, `脫`, `驴`, `镁`) que indican problemas de encoding UTF-8. No afecta funcionalidad pero indica un problema en el pipeline de desarrollo.
- **Archivos:** `ver.html`, `routes.py`
- **Recomendación:** Re-guardar todos los archivos con encoding UTF-8 sin BOM.

#### [F2] Espacio residual en acciones de listar.html
Se observa un espacio vacío después del botón "Ver" en la tabla desktop y "Ver ficha" en las tarjetas móvil, indicando que se eliminó un botón (posiblemente "Editar" o "Eliminar") sin limpiar el contenedor.
- **Archivo:** `listar.html`
- **Recomendación:** Limpiar el HTML residual.

#### [F3] Badge total no se actualiza al filtrar
El badge del encabezado (`badge-total`) muestra `{{ estudiantes | length }}` como total estático, pero los contadores dinámicos se actualizan con JS. Al filtrar, el badge del encabezado queda desincronizado.
- **Archivo:** `listar.html`
- **Recomendación:** Actualizar también `badge-total` en la función `filtrar()`.

#### [F4] Navegación inconsistente entre templates
El formulario tiene 18 links numerados con barra de progreso. La ficha tiene 14 links sin numeración. Las secciones no coinciden exactamente.
- **Archivos:** `formulario.html`, `ver.html`
- **Recomendación:** Unificar la estructura de secciones y la experiencia de navegación entre vistas.

#### [F5] CSS de nav-activo en bloque separado en ver.html
La clase `.nav-activo-ficha` está definida en un `<style>` al final del template, separada del bloque principal de estilos.
- **Archivo:** `ver.html`
- **Recomendación:** Consolidar en el bloque `<style>` principal.

#### [F6] Sin validación del lado del cliente más allá de HTML5 required
La validación del formulario es únicamente HTML5 `required`. No hay validación JavaScript adicional para formato de RUT, rangos de fechas, consistencia de datos, etc.
- **Archivo:** `formulario.html`
- **Recomendación:** Agregar validación JavaScript previa al envío, especialmente para RUT y fechas.

---

## 6. Resumen de Hallazgos por Severidad

### Crítico (3)
- [S1] Sin protección CSRF
- [S2] Endpoints AJAX sin validación de permisos
- [S3] Exposición de datos sensibles sin autorización

### Alto (1)
- [S4] Exposición de información interna en errores

### Medio (4)
- [S5] RUT sin validación de dígito verificador
- [S6] Regex de RUT no bloquea envío
- [P1] Consulta ineficiente en ajax_grados
- [A2] Lógica de apoderados por posición (fragil)

### Bajo (8)
- [P2] Sin paginación en listado
- [P3] Deduplicación en memoria
- [A1] Sin ruta de edición directa
- [A3] Sin funcionalidad de eliminación
- [A4] Duplicación de código Jinja
- [A5] Badges "Activo" hardcodeados
- [F1] Caracteres corruptos por encoding
- [F6] Sin validación JS adicional

---

## 7. Endpoint Map Visual

```
GET  /matricula/                          → listar_estudiantes    (permiso ≥1)
GET  /matricula/nuevo                     → nuevo_estudiante      (permiso ≥2, GET)
POST /matricula/nuevo                     → nuevo_estudiante      (permiso ≥2, POST)
GET  /matricula/<person_id>               → ver_estudiante        (permiso ≥1)
GET  /matricula/ajax/grados/<nivel_id>    → ajax_grados           (solo módulo)
GET  /matricula/ajax/cursos/<grado_id>    → ajax_cursos           (solo módulo)
GET  /matricula/ajax/buscar_estudiante    → ajax_buscar_estudiante (solo módulo)
GET  /matricula/ajax/estudiante/<id>      → ajax_datos_estudiante  (solo módulo)
```

---

## 8. Diagrama de Flujo de Creación

```
Usuario llena formulario
        │
        ▼
   POST /nuevo
        │
        ▼
  ¿Módulo habilitado? ──No──► Redirect dashboard
        │ Sí
        ▼
  ¿Permiso ≥2? ──No──► Redirect listar
        │ Sí
        ▼
  ¿Campos obligatorios completos? ──No──► Flash error, redirect
        │ Sí
        ▼
  ¿person_id_precargado válido?
     ├──Sí + RUT coincide ──► Re-matricula (misma persona)
     ├──Sí + RUT NO coincide ──► Busca por RUT o crea nueva
     └──No ──► Busca por RUT o crea nueva
        │
        ▼
  Cerrar roles anteriores (si re-matricula)
        │
        ▼
  UPSERT: Identificadores, Rol, Residencia
        │
        ▼
  UPSERT: Apoderados (titular, suplente1, suplente2)
        │
        ▼
  UPSERT: Enrollment (~50 campos)
        │
        ▼
  UPSERT: Contactos emergencia (×2)
        │
        ▼
  UPSERT: Salud (si hay datos)
        │
        ▼
  UPSERT: PIE (si pertenece)
        │
        ▼
  COMMIT → Flash éxito → Redirect listar
  (o ROLLBACK → Flash error en caso de excepción)
```

---

*Auditoría generada el análisis de los 4 archivos del módulo matrícula.*
```

---