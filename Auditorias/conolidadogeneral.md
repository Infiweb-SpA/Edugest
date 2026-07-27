Perfecto, tengo todos los documentos. Aqui va el consolidado completo:

---

```markdown
# CONSOLIDADO DE AUDITORÍA DE SEGURIDAD — Sistema Edugest
## Fecha: Julio 2026
## Alcance: Auditoría completa de los 12 módulos del sistema

---

## 1. RESUMEN EJECUTIVO

El sistema Edugest es una plataforma de gestión educativa construida con Flask + SQLite que implementa el estándar MINEDUC (EDE) con extensiones propias. La auditoría cubrió **12 módulos**, **86 archivos** (routes, templates, modelos, configuración) y **72 rutas HTTP**.

### Estado general del sistema

| Dimensión | Evaluación |
|-----------|------------|
| **Autenticación** | DEFICIENTE — Rutas críticas sin @login_required (Reportes, Admin) |
| **Autorización** | DEFICIENTE — Sistema de permisos fragmentado en 7+ implementaciones |
| **Protección de datos** | CRÍTICA — PDFs, CSVs y APIs exponen datos sensibles sin autenticación |
| **CSRF** | AUSENTE — Ningún formulario POST del sistema incluye token CSRF |
| **XSS** | VULNERABLE — innerHTML en chat de comunicaciones |
| **Integridad de datos** | MEDIA — Validaciones inconsistentes (RUT sin dígito verificador) |
| **Rendimiento** | MEDIO — N+1 queries generalizado, sin paginación |
| **Mantenibilidad** | MEDIA — Código duplicado, lógica de negocio fragmentada |

### Hallazgos consolidados por severidad

| Severidad | Cantidad | Requiere acción inmediata |
|-----------|----------|--------------------------|
| **CRÍTICO** | 7 | SÍ — Explotables sin autenticación |
| **ALTO** | 20 | SÍ — Riesgo significativo de seguridad |
| **MEDIO** | 30 | Planificada |
| **BAJO** | 35+ | Mejoras de mantenibilidad |
| **TOTAL** | **92+** | — |

---

## 2. HALLAZGOS CRÍTICOS (7) — Acción inmediata requerida

Estos hallazgos permiten acceso no autenticado a datos sensibles o ejecución de código malicioso.

### C1 — Sin @login_required en módulo Reportes (todas las rutas)
- **Módulo:** reportes
- **Archivo:** `reportes/routes.py`
- **Descripción:** Las 10 rutas del módulo carecen de `@login_required`. Cualquier persona conoce la URL puede acceder a: reportes de curso, reportes de grado, calificaciones por asignatura, gráficos de asistencia, CSV con RUTs y nombres, e **informes PDF individuales con datos médicos, anotaciones y RUTs**.
- **Datos expuestos:** RUT, nombre completo, calificaciones, asistencia, anotaciones disciplinarias, información médica, comentarios del establecimiento.
- **Ruta más sensible:** `GET /reportes/curso/<curso_id>/informe_notas/<rol_id>` genera PDF institucional con toda la información del estudiante.

### C2 — Rutas Admin sin ninguna protección de acceso
- **Módulo:** admin
- **Archivo:** `admin/routes.py`
- **Descripción:** `/admin/` (dashboard) y `/admin/toggle-module/<module_id>` (habilitar/deshabilitar módulos) son completamente públicas. No usan `@login_required`, `@permiso_requerido`, ni verificación manual.
- **Impacto:** Cualquier usuario no autenticado puede ver el panel de administración y modificar qué módulos están habilitados en el sistema.

### C3 — Credenciales admin por defecto expuestas en template
- **Módulo:** admin
- **Archivo:** `admin/login.html`
- **Descripción:** El template muestra literalmente "Usuario por defecto: admin / admin123". Combinado con C2, cualquier persona puede acceder al panel de administración.
- **Credencial:** Username=`admin`, Password=`admin123` (hardcoded en `permissions.py`).

### C4 — XSS via innerHTML en chat de comunicaciones
- **Módulo:** comunicacion
- **Archivo:** `chat_conversacion.html`
- **Descripción:** El polling AJAX de mensajes nuevos inserta contenido via `bubble.innerHTML = '<p>' + m.texto + '</p>'`. Si el backend no sanitiza el texto, un mensaje con `<img src=x onerror=alert(1)>` ejecuta JavaScript en el navegador del receptor.
- **Vector:** Cualquier usuario autenticado con acceso al chat puede enviar un mensaje malicioso.

### C5 — Resetear contraseña accesible via GET
- **Módulo:** gestion_usuarios
- **Archivo:** `gestion_usuarios/routes.py`
- **Descripción:** `resetear_password` acepta GET (`methods=['GET', 'POST']`). El botón en el template es un `<a href="...">`. Un atacante podría forzar el reseteo de cualquier contraseña si el admin hace clic en un link manipulado (CSRF via GET, trivial de explotar).
- **Agravante:** La nueva contraseña temporal se muestra en un flash message visible en pantalla.

### C6 — Endpoints AJAX de matrícula sin validación de permisos
- **Módulo:** matricula
- **Archivo:** `matricula/routes.py`
- **Descripción:** Los 4 endpoints AJAX (`ajax_grados`, `ajax_cursos`, `ajax_buscar_estudiante`, `ajax_datos_estudiante`) solo verifican que el módulo esté habilitado, pero NO verifican el nivel de permiso. Un usuario con nivel 0 (sin acceso) puede llamar a estos endpoints.
- **Ruta más sensible:** `ajax_datos_estudiante` expone TODA la información de un estudiante (datos médicos, PIE, contactos de emergencia, apoderados).

### C7 — Exposición de datos sensibles de matrícula sin autorización
- **Módulo:** matricula
- **Archivo:** `matricula/routes.py`, función `_serialize_estudiante`
- **Descripción:** `ajax_datos_estudiante` serializa y retorna toda la información de un estudiante sin verificar permisos de lectura. Datos médicos, PIE, contactos de emergencia, y datos de apoderados son accesibles para cualquier usuario autenticado.

---

## 3. HALLAZGOS ALTOS (20) — Riesgo significativo

### Autenticación y Sesión

| ID | Hallazgo | Módulo | Descripción |
|----|----------|--------|-------------|
| A1 | `remember=True` hardcodeado | auth | `login_user(usuario, remember=True)` siempre recuerda la sesión. En entornos compartidos, la sesión persiste indefinidamente. |
| A2 | Open Redirect via parámetro `next` | auth | La redirección post-login usa `request.args.get('next')` sin validar que sea URL interna. |
| A3 | Sin rate limiting en login | auth | No hay limitación de intentos en `/auth/login`. Permite fuerza bruta. |
| A4 | Sin gestión de contraseñas | auth | No hay rutas para cambio, recuperación, reseteo ni expiración de contraseñas. |
| A5 | Contraseña temporal visible en flash | gestion_usuarios | La contraseña generada en `resetear_password` se muestra via `flash()` visible en pantalla. |

### CSRF (Ausente en todo el sistema)

| ID | Hallazgo | Módulos afectados |
|----|----------|-------------------|
| A6 | **Sin protección CSRF en ningún módulo** | **TODOS** — auth, admin, matricula, calendario, comunicacion, evaluaciones, biblioteca, libro_digital, gestion_usuarios, gestion_roles, reportes |

**Detalle por módulo:**

| Módulo | Forms POST sin CSRF |
|--------|---------------------|
| auth | Login |
| admin | Toggle módulos, guardar permisos, crear/editar rol, crear/editar usuario, toggle usuario, eliminar usuario |
| matricula | Crear estudiante |
| calendario | Crear evento, eliminar evento |
| comunicacion | Nuevo anuncio, enviar mensaje chat |
| evaluaciones | Crear evaluación, crear pregunta, rendir examen, nota manual, eliminar nota, cambiar visibilidad |
| biblioteca | Nuevo/editar libro, eliminar libro, nuevo préstamo, devolver, renovar |
| libro_digital | Actualizar grado, crear asignatura, crear unidad/clase, registrar asistencia, crear anotación |
| gestion_usuarios | Crear/editar usuario, toggle activo, resetear contraseña |
| gestion_roles | Crear rol, editar permisos |
| reportes | Configurar sumativas |

### Autorización

| ID | Hallazgo | Módulo | Descripción |
|----|----------|--------|-------------|
| A7 | Sin verificación de acceso en chat | comunicacion | `chat_conversacion` y `chat_enviar` no verifican que `contacto_id` esté en la lista de contactos permitidos. Un usuario puede chatear con cualquier PersonId. |
| A8 | Sin verificación de acceso por organización | reportes | `reporte_curso(curso_id)` y `reporte_grado(grado_id)` no verifican que el usuario tenga acceso a esa organización. |
| A9 | Sin validación de acceso por profesor asignado | libro_digital | Cualquier usuario con permisos puede registrar asistencia y ver estudiantes de CUALQUIER asignatura/grado. No hay verificación de asignación. |
| A10 | 8 de 10 rutas de reportes sin permisos | reportes | Solo `index`, `configurar_sumativas` y `guardar_sumativa_ajax` verifican permisos. Las 7 restantes son completamente abiertas. |
| A11 | 3 rutas de libro_digital sin permisos | libro_digital | `listar_grados`, `asignaturas_por_grado`, `registrar_clase_get` solo tienen `@login_required`. Exponen datos de estudiantes. |
| A12 | 4 rutas de evaluaciones sin permisos | evaluaciones | `asignaturas_por_grado`, `unidades_asignatura`, `rendir`, `resultados` sin `@permiso_requerido`. |

### Sistemas Duplicados y Fragmentados

| ID | Hallazgo | Módulos | Descripción |
|----|----------|---------|-------------|
| A13 | Sistema de autenticación duplicado | admin, auth | `permissions.py` usa `session['user_id']` + `EdugestSystemUser`. `auth` usa Flask-Login + `EdugestUser`. Dos sistemas paralelos. |
| A14 | Dos sistemas de permisos paralelos | admin, gestion_roles, auth | Sistema A (`EdugestRolePermission`, niveles 0/1/2) usado por la mayoría de módulos. Sistema B (`EdugestFeaturePermission`, CanView/Edit/Delete) definido en `admin/permissions.py` pero nunca usado activamente. |
| A15 | 12 endpoints referenciados en templates pero no implementados | admin | Templates de admin referencian endpoints CRUD que no existen en `admin/routes.py`. |
| A16 | Upload de imágenes sin validación de contenido | evaluaciones | `disenar_preguntas_post` acepta extensiones png/jpg/jpeg/gif pero no valida MIME type ni tamaño máximo. |
| A17 | PDF con datos sensibles sin autenticación | reportes | `informe_notas_pdf` genera PDF con nombre, RUT, calificaciones, asistencia, anotaciones, info médica. Accesible sin login. |
| A18 | CSV de asistencia sin autenticación | reportes | `exportar_asistencia` genera CSV con nombres y RUTs de todos los alumnos. Sin protección. |
| A19 | Eliminar evento sin verificación de propiedad | calendario | Cualquier usuario nivel 2 puede eliminar cualquier evento, incluyendo evaluaciones de otros profesores. |
| A20 | Política de contraseña débil | gestion_usuarios | Contraseña mínima de 4 caracteres. `secrets.token_hex(4)` genera solo 8 caracteres hexadecimales. |

---

## 4. HALLAZGOS MEDIOS (30)

### Autenticación y Sesión

| ID | Hallazgo | Módulo |
|----|----------|--------|
| M1 | Verificación de permisos inline inconsistente | comunicacion |
| M2 | Sender de anuncio no es `current_user` | comunicacion |
| M3 | Resetear contraseña sin forzar cambio en primer login | gestion_usuarios |
| M4 | Verificación de rol profesor por nombre (frágil) | gestion_usuarios |
| M5 | RoleId sin validación de rango máximo | gestion_roles |

### Validación de Datos

| ID | Hallazgo | Módulo |
|----|----------|--------|
| M6 | RUT sin validación de dígito verificador | matricula |
| M7 | Regex de RUT no bloquea envío (solo warning) | matricula |
| M8 | Sin validación backend de pertenencia curso→grado | gestion_usuarios |
| M9 | Búsqueda de persona para préstamo usa `.first()` (rol arbitrario) | biblioteca |
| M10 | RoleId 21 inusual para profesores | biblioteca |
| M11 | Renovación de préstamo sin límite | biblioteca |
| M12 | Eliminación de libro puede perder historial | biblioteca |
| M13 | Sin validación hora inicio < hora término | libro_digital |
| M14 | Inconsistencia de zona horaria (datetime.now vs obtener_hora_chile) | libro_digital |
| M15 | Verificación de permisos incorrecta para evaluaciones en libro_digital | libro_digital |
| M16 | Error silencioso en fecha de calendario | evaluaciones |
| M17 | Re-rendir evaluación sin confirmación ni auditoría | evaluaciones |
| M18 | Toggle de usuario sin verificación de permisos en template | admin |
| M19 | Rendir evaluación sin confirmación de envío | evaluaciones |

### Arquitectura de Permisos

| ID | Hallazgo | Módulos |
|----|----------|---------|
| M20 | `_get_org_ids_for_user()` duplicada en 2+ módulos | portada, calendario |
| M21 | `get_permiso_modulo()` duplicada en 2+ módulos | matricula, reportes |
| M22 | Al menos 5 implementaciones distintas del chequeo de permisos | múltiples |
| M23 | Decorador `permiso_requerido()` subutilizado | auth (definido pero poco usado) |
| M24 | Verificación redundante después de decorador | comunicacion |
| M25 | Delete-all + re-insert en permisos (sin transacción) | gestion_roles |
| M26 | Permisos inconsistentes entre rutas del mismo módulo | libro_digital |
| M27 | Sin filtro de acceso por organización en reportes | reportes |

### Rendimiento

| ID | Hallazgo | Módulos |
|----|----------|---------|
| M28 | N+1 queries en módulos principales | matricula, reportes, comunicacion, evaluaciones, libro_digital, gestion_usuarios, calendario, biblioteca |
| M29 | `chat_lista` carga TODOS los mensajes sin paginación | comunicacion |
| M30 | Polling cada 8 segundos genera carga con muchos usuarios | comunicacion |

---

## 5. HALLAZGOS BAJOS (35+)

### Arquitectura y Mantenibilidad

| ID | Hallazgo | Módulo |
|----|----------|--------|
| B1 | Lógica de visibilidad de eventos duplicada | portada, calendario |
| B2 | Links vacíos en acceso rápido (`href="#"`) | portada |
| B3 | Rol nombre para condicionales en template (frágil) | portada |
| B4 | Año académico hardcoded en reglamento | portada |
| B5 | Sin filtro de tipo en relaciones de apoderado | portada |
| B6 | `pytz` vs `ZoneInfo` inconsistentes | comunicacion |
| B7 | `EdugestChatMessage.SentAt` usa UTC en vez de hora Chile | comunicacion |
| B8 | `crear_instrumento` redirect hardcoded a grado_id=1 | evaluaciones |
| B9 | Líneas en blanco entre decoradores y defs (decorador removido) | libro_digital |
| B10 | Roles 2,3,4,5 no se crean en `EdugestRole` en seed | seed |
| B11 | Sistema B de permisos (muerto) coexiste con Sistema A | admin |
| B12 | Login duplicado (admin/login.html + auth/login.html) | admin |
| B13 | Badges hardcodeados por RoleId (inconsistencia RoleId=6) | múltiples |
| B14 | Select de roles sin filtro de activos | admin |
| B15 | Sin campo de Person en formulario de usuario (admin) | admin |
| B16 | Permisos por defecto solo insertan, no actualizan | admin |
| B17 | Template `historial.html` vacío | biblioteca |
| B18 | ISBN no editable en modo edición | biblioteca |
| B19 | Link de descarga sin validación de URL | biblioteca |
| B20 | Dos formularios de crear evaluación | evaluaciones |
| B21 | Template `index.html` posiblemente obsoleto | evaluaciones |
| B22 | Upload de imagen deshabilitado en frontend pero habilitado en backend | evaluaciones |
| B23 | Sin eliminación de evaluaciones, preguntas, anuncios, mensajes | múltiples |
| B24 | Funciones duplicadas en routes.py (3 funciones definidas 2 veces) | gestion_usuarios |
| B25 | Sin ruta de edición directa de estudiante | matricula |
| B26 | Lógica de apoderados por posición (slot) frágil | matricula |
| B27 | Badges "Activo" hardcodeados en ver.html | matricula |
| B28 | Lógica de promedios duplicada en 3 funciones + JS | reportes |
| B29 | Filtro de fecha duplicado en curso.html | reportes |
| B30 | Ciudad hardcoded en PDF ("Temuco") | reportes |
| B31 | Profesor jefe = primer profesor del curso (.first()) | reportes |
| B32 | Botón "Subir Material" no funcional | libro_digital |
| B33 | `javascript:history.back()` para navegación | libro_digital |
| B34 | Permisos cruzados en "Volver" (usa "Evaluaciones" en vez de "Libro Digital") | libro_digital |

### Frontend

| ID | Hallazgo | Módulo |
|----|----------|--------|
| B35 | Tailwind via CDN (versión desarrollo) en producción | auth, evaluaciones |
| B36 | Encoding corrupto en múltiples archivos | múltiples |
| B37 | Botón "Volver al Panel" siempre a admin.dashboard | auth |
| B38 | Categorías flash inconsistentes | auth |
| B39 | Inconsistencia en letras del abecedario (minúsculas vs mayúsculas) | evaluaciones |
| B40 | Completar depende de `[___]` literal | evaluaciones |

---

## 6. HALLAZGOS SISTÉMICOS (Cross-Cutting)

Estos problemas afectan a TODOS o la mayoría de los módulos y requieren soluciones centralizadas.

### S1 — Sin protección CSRF (CRÍTICO SISTÉMICO)

**Módulos afectados:** TODOS (11 de 12 módulos tienen forms POST sin CSRF).

El sistema no implementa `Flask-WTF` ni ningún middleware CSRF. Esto significa que cualquier formulario POST en todo el sistema puede ser enviado por un sitio malicioso si el usuario está autenticado.

**Implementación recomendada:**
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

### S2 — Sistema de permisos fragmentado (ALTO SISTÉMICO)

Existen **al menos 7 implementaciones distintas** del chequeo de permisos:

| # | Implementación | Ubicación | Mecanismo |
|---|----------------|-----------|-----------|
| 1 | `permiso_requerido()` | auth/routes.py | Decorador principal |
| 2 | `verificar_escritura()` | auth/routes.py | Helper para POST |
| 3 | `get_permiso_modulo()` | matricula/routes.py | Helper local |
| 4 | `get_permiso_modulo()` | reportes/routes.py | Copia exacta de #3 |
| 5 | `_get_nivel_permiso()` | calendario/routes.py | Helper local |
| 6 | `_es_nivel_2_evaluaciones()` | evaluaciones/routes.py | Helper local |
| 7 | `check_permission()` | admin/permissions.py | Sistema B (muerto) |
| 8 | `if current_user.RoleId == 1` | múltiples | Inline manual |

**Tablas involucradas:** `EdugestRolePermission` (sistema activo), `EdugestFeaturePermission` (sistema muerto).

### S3 — N+1 queries generalizado (MEDIO SISTÉMICO)

Módulos con N+1 queries documentado: matricula, reportes, comunicacion, evaluaciones, libro_digital, gestion_usuarios, calendario, biblioteca. Prácticamente todo el sistema carga relaciones de forma lazy.

### S4 — Sin paginación (MEDIO SISTÉMICO)

Ningún módulo implementa paginación server-side (biblioteca es la excepción parcial con `per_page=12` en catálogo y `per_page=20` en historial).

### S5 — RoleId=6 inconsistente (MEDIO SISTÉMICO)

| Ubicación | RoleId=6 representa |
|-----------|---------------------|
| auth/routes.py | Apoderado/Estudiante (redirect a portada) |
| auth/usuarios.html | "Apoderado" |
| portada/routes.py | Estudiante (RoleId=6) |
| comunicacion | Estudiante (bloquea crear anuncios) |
| matricula | Estudiante en OrganizationPersonRole |
| seed.py | Nunca crea usuario con RoleId=5 para apoderado |

No hay claridad documentada sobre si RoleId=6 es Estudiante o Apoderado.

### S6 — Inconsistencia de permisos entre rutas del mismo módulo (ALTO SISTÉMICO)

| Módulo | Rutas con permisos | Rutas sin permisos |
|--------|-------------------|-------------------|
| reportes | 3/10 (verif. inline) | 7/10 |
| evaluaciones | 6/15 (@permiso_requerido) | 4/15 (solo @login_required) + 5 con bloqueos manuales |
| libro_digital | 7/11 (@permiso_requerido) | 4/11 (solo @login_required) |
| admin | 0/2 | 2/2 (NINGUNA protección) |
| portada | 0/2 | 2/2 (solo @login_required) |

---

## 7. RESUMEN POR MÓDULO

| # | Módulo | Rutas | Crítico | Alto | Medio | Bajo | Estado general |
|---|--------|-------|---------|------|-------|------|---------------|
| 1 | auth | 3 | 0 | 2 | 4 | 8 | MEDIO |
| 2 | admin | 2 (+12 no implementados) | 2 | 4 | 2 | 10 | **CRÍTICO** |
| 3 | portada | 2 | 0 | 0 | 1 | 4 | BAJO |
| 4 | matricula | 7 | 2 | 1 | 4 | 8 | **CRÍTICO** |
| 5 | calendario | 3 | 0 | 1 | 2 | 3 | MEDIO |
| 6 | comunicacion | 8 | 1 | 3 | 5 | 4 | **CRÍTICO** |
| 7 | evaluaciones | 15 | 0 | 2 | 5 | 7 | MEDIO-ALTO |
| 8 | biblioteca | 11 | 0 | 1 | 5 | 4 | MEDIO |
| 9 | libro_digital | 11 | 0 | 3 | 4 | 7 | ALTO |
| 10 | gestion_usuarios | 6 | 1 | 3 | 4 | 4 | **CRÍTICO** |
| 11 | gestion_roles | 5 | 0 | 1 | 3 | 5 | MEDIO |
| 12 | reportes | 10 | 1 | 4 | 3 | 6 | **CRÍTICO** |

### Módulos en estado CRÍTICO (5):
1. **reportes** — 10 rutas sin @login_required, PDF/CSV expuestos
2. **admin** — Rutas públicas, credenciales expuestas, sistemas duplicados
3. **matricula** — AJAX sin permisos, datos sensibles expuestos
4. **comunicacion** — XSS, chat sin verificación de acceso
5. **gestion_usuarios** — Reset de contraseña via GET

---

## 8. MAPEO DE COBERTURA DE PERMISOS

### Rutas protegidas vs sin protección

| Categoría | Cantidad | % |
|-----------|----------|---|
| Con `@login_required` + `@permiso_requerido` | 28 | 39% |
| Con `@login_required` solo | 21 | 29% |
| Con verificación inline (manual) | 8 | 11% |
| **Sin ninguna protección** | **15** | **21%** |
| **Total** | **72** | **100%** |

### Rutas sin ninguna protección (las más peligrosas)

| Módulo | Ruta | Datos expuestos |
|--------|------|-----------------|
| admin | `GET /admin/` | Panel de administración |
| admin | `POST /admin/toggle-module/<id>` | Modificar módulos del sistema |
| reportes | `GET /reportes/curso/<id>` | Reporte completo de curso |
| reportes | `GET /reportes/grado/<id>` | Reporte completo de grado |
| reportes | `GET /reportes/asignatura/<id>` | Calificaciones por asignatura |
| reportes | `GET /reportes/curso/<id>/grafico_asistencia` | Gráfico de asistencia |
| reportes | `GET /reportes/curso/<id>/exportar_asistencia` | CSV con RUTs y nombres |
| reportes | `GET /reportes/curso/<id>/informe_notas/<rol_id>` | PDF con datos médicos |
| reportes | `GET /reportes/grado/<id>/grafico` | Gráfico del grado |

---

## 9. DEPENDENCIAS ENTRE MÓDULOS

```
┌─────────────────────────────────────────────────────┐
│                    FLASK APP                         │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │   auth   │  │  admin   │  │  gestion_roles   │  │
│  │ (login,  │  │ (panel,  │  │  (CRUD roles,    │  │
│  │ permisos)│  │ toggle)  │  │   permisos)      │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                  │            │
│  ┌────┴──────────────┴──────────────────┴─────────┐ │
│  │           Sistema de Permisos (fragmentado)     │ │
│  │  EdugestRolePermission (niveles 0/1/2)         │ │
│  │  EdugestFeaturePermission (CanView/Edit/Delete)│ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  matricula │  │gestion_usr  │  │   portada   │  │
│  │ (estudiantes│  │ (CRUD users)│  │ (bienvenida)│  │
│  └──────┬─────┘  └─────────────┘  └──────┬──────┘  │
│         │                                │         │
│  ┌──────┴────────────────────────────────┴──────┐  │
│  │              Organization (Mineduc)          │  │
│  │  Person, OrganizationPersonRole, etc.        │  │
│  └──────┬────────────────────────────────┬──────┘  │
│         │                                │         │
│  ┌──────┴──────┐  ┌──────────┐  ┌───────┴───────┐  │
│  │libro_digital│  │evaluac.  │  │   reportes    │  │
│  │(asistencia, │←→│(examenes,│←→│ (reportes,    │  │
│  │ planificac.)│  │ notas)   │  │  PDF, CSV)    │  │
│  └──────┬──────┘  └────┬─────┘  └───────────────┘  │
│         │              │                            │
│  ┌──────┴──────────────┴─────────┐                 │
│  │        calendario              │                 │
│  │ (eventos, integración evals.)  │                 │
│  └────────────────────────────────┘                 │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐                 │
│  │ comunicacion │  │ biblioteca   │                 │
│  │ (chat,anunc.)│  │ (libros,     │                 │
│  │              │  │  préstamos)  │                 │
│  └──────────────┘  └──────────────┘                 │
└─────────────────────────────────────────────────────┘
```

---

## 10. PLAN DE REMEDIACIÓN PRIORIZADO

### Fase 0 — Emergencia (1-2 días)
Estos hallazgos son explotables ahora mismo sin autenticación.

| Prioridad | Acción | Hallazgos | Módulos |
|-----------|--------|-----------|---------|
| 0.1 | Agregar `@login_required` a TODAS las rutas de reportes | C1 | reportes |
| 0.2 | Agregar `@login_required` + verificación de admin a rutas de admin | C2, C3 | admin |
| 0.3 | Eliminar credenciales del template `admin/login.html` | C3 | admin |
| 0.4 | Cambiar contraseña admin por defecto en `init_default_admin_user()` | C3 | admin |

### Fase 1 — Crítico (1 semana)

| Prioridad | Acción | Hallazgos | Módulos |
|-----------|--------|-----------|---------|
| 1.1 | Implementar `Flask-WTF` CSRFProtect global | A6, S1 | TODOS |
| 1.2 | Corregir XSS en chat: usar `textContent` en vez de `innerHTML` | C4 | comunicacion |
| 1.3 | Cambiar `resetear_password` a solo POST | C5 | gestion_usuarios |
| 1.4 | Agregar verificación de permisos a endpoints AJAX de matrícula | C6, C7 | matricula |
| 1.5 | Agregar `@permiso_requerido` a rutas desprotegidas de reportes | A10, A17, A18 | reportes |
| 1.6 | Verificar acceso de chat por lista de contactos permitidos | A7 | comunicacion |

### Fase 2 — Alto (2-3 semanas)

| Prioridad | Acción | Hallazgos | Módulos |
|-----------|--------|-----------|---------|
| 2.1 | Unificar sistema de permisos (eliminar Sistema B muerto) | A13, A14, A15 | admin, gestion_roles |
| 2.2 | Agregar `@permiso_requerido` a rutas desprotegidas de evaluaciones | A12 | evaluaciones |
| 2.3 | Agregar `@permiso_requerido` a rutas desprotegidas de libro_digital | A11 | libro_digital |
| 2.4 | Implementar rate limiting en login | A3 | auth |
| 2.5 | Validar parámetro `next` en login (URL interna) | A2 | auth |
| 2.6 | Validar MIME type y tamaño en upload de imágenes | A16 | evaluaciones |
| 2.7 | Verificar acceso por organización en reportes | A8 | reportes |
| 2.8 | Verificar profesor asignado en libro_digital | A9 | libro_digital |
| 2.9 | Implementar gestión de contraseñas (cambio, recuperación) | A4 | auth |

### Fase 3 — Medio (1 mes)

| Prioridad | Acción | Hallazgos |
|-----------|--------|-----------|
| 3.1 | Extraer helpers de permisos a módulo compartido | M20-M26 |
| 3.2 | Implementar paginación server-side en módulos principales | M28, M29 |
| 3.3 | Resolver N+1 queries con `joinedload` o queries agregadas | M28 |
| 3.4 | Validar dígito verificador de RUT | M6, M7 |
| 3.5 | Clarificar semántica de RoleId=6 | S5 |
| 3.6 | Implementar WebSocket o SSE para reemplazar polling de chat | M30 |

---

## 11. MÉTRICAS DE COBERTURA

| Métrica | Valor actual | Valor recomendado |
|---------|-------------|-------------------|
| Rutas con `@login_required` | 79% | 100% |
| Rutas con `@permiso_requerido` | 39% | 80%+ |
| Rutas sin ninguna protección | 21% | 0% |
| Módulos con CSRF | 0/12 | 12/12 |
| Implementaciones de permisos | 7+ | 1 |
| Módulos con paginación | 1/12 | 12/12 |
| Templates con sanitización XSS | Parcial | 100% |

---

## 12. ARCHIVOS REVISADOS

| Módulo | Archivos | Rutas | Templates |
|--------|----------|-------|-----------|
| auth | 5 | 3 | 3 |
| admin | 9 | 2 | 7 |
| portada | 4 | 2 | 2 |
| matricula | 5 | 7 | 3 |
| calendario | 3 | 3 | 1 |
| comunicacion | 7 | 8 | 5 |
| evaluaciones | 11 | 15 | 10 |
| biblioteca | 10 | 11 | 8 |
| libro_digital | 7 | 11 | 6 |
| gestion_usuarios | 4 | 6 | 2 |
| gestion_roles | 5 | 5 | 3 |
| reportes | 7 | 10 | 6 |
| **TOTAL** | **~86** | **72** | **~56** |

---

*Consolidado generado a partir de la auditoría completa de los 12 módulos del sistema Edugest.*
*Fecha de auditoría: Julio 2026.*
```

---
