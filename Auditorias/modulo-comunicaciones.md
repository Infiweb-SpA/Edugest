## Analisis del Archivo 7 (comunicacion): `contacto_detalle.html`



### Proposito
Template Jinja2 que extiende `base.html`. Ficha detallada del estudiante con datos personales, apoderado, contactos de emergencia, informacion medica, y datos de matricula.

### Datos del backend

| Variable | Contenido |
|----------|-----------|
| `estudiante` | Objeto `Person` del estudiante |
| `curso` | Objeto `Organization` del curso actual con `.grado_nombre` |
| `run` | String: RUN del estudiante |
| `ipe` | String: IPE del estudiante |
| `telefono_estudiante` | String: telefono del estudiante |
| `email_estudiante` | String: email del estudiante |
| `apoderado` | Objeto `Person` del apoderado |
| `telefono_apoderado` | String: telefono del apoderado |
| `email_apoderado` | String: email del apoderado |
| `direccion_apoderado` | String: direccion del apoderado |
| `detalle_apoderado` | Objeto `EdugestPersonRelationshipDetail` (Parentesco, ProfesionOcupacion, LugarTrabajo) |
| `wa_link` | String: enlace WhatsApp normalizado |
| `contactos_emergencia` | Lista de `EdugestEmergencyContact` |
| `health` | Objeto `EdugestStudentHealth` |
| `enrollment` | Objeto `EdugestStudentEnrollment` |

### Estructura

1. **Tarjeta Estudiante** (azul): Avatar, nombre completo, curso, RUN, IPE, fecha nacimiento, telefono, email.

2. **Tarjeta Apoderado** (verde): Avatar, nombre completo, parentesco, telefono, email, profesion, lugar trabajo, direccion, boton WhatsApp, boton Chat. Si no hay apoderado, muestra estado vacio.

3. **Contactos de Emergencia** (rojo): Grid de tarjetas con numero de orden, nombre, parentesco, RUN, telefono (con link WhatsApp inline), telefono alternativo, email, profesion, nivel educacional (decodificado: 1-9).

4. **Informacion Medica** (rosa): Datos basicos (grupo sanguineo, sistema salud, centro salud, medico tratante, telefono medico). Condiciones importantes con alertas visuales (alergias-rojo, enfermedades-naranja, medicamentos-amarillo, restricciones alimentarias-amber, necesidades especiales-purpura, observaciones-gris).

5. **Informacion Adicional** (indigo): Nacionalidad, pais origen, comuna, region, email, telefono estudiante. SEP flags (Alumno Prioritario, Alumno Preferente, Beneficiario SEP) con badges Si/No.

### Permisos en template

No hay verificaciones de permisos adicionales. La proteccion viene del backend (`@permiso_requerido('Comunicaciones', nivel=2)`).

### Endpoints referenciados

| Endpoint | Proposito |
|----------|-----------|
| `comunicacion.contactos` | Volver al listado |
| `comunicacion.chat_conversacion(contacto_id)` | Chat con apoderado |

### Observaciones para la auditoria

1. **Link WhatsApp inline para contactos de emergencia**: `'https://wa.me/' + contacto.TelefonoPrincipal|replace(' ', '')|replace('-', '')|replace('+', '')`. Normalizacion basica en template, diferente a la normalizacion robusta en el helper `generar_wa_link()`. Podria generar enlaces incorrectos para numeros con formato no estandar.

2. **Nivel educacional decodificado en template**: 9 niveles hardcodeados con if/elif. Duplica logica que podria estar en el modelo o backend.

3. **Boton WhatsApp con `rel="noopener noreferrer"`**: Patron correcto para links externos con `target="_blank"`.

4. **Informacion medica sensible visible**: Alergias, enfermedades, medicamentos. Sin capa adicional de proteccion mas alla del nivel 2 del decorador. Un usuario con permiso nivel 2 podria ver informacion medica de cualquier estudiante.

5. **Link volver con `curso_id`**: `url_for('comunicacion.contactos', curso_id=curso.OrganizationId if curso else '')`. Si no hay curso, pasa string vacio. Correcto.

6. **Campos opcionales manejados con `{% if %}`**: Cada campo se muestra solo si existe. Patron consistente.

7. **SEP badges con ring**: `ring-1 ring-green-600/20` para badges positivos. Detalle visual refinado.

8. **Contactos de emergencia con nombre flexible**: `contacto.FirstName` o `contacto.NombreCompleto` como fallback. Indica que el modelo `EdugestEmergencyContact` tiene ambos campos.

9. **Enrollment con multiples campos**: Nacionalidad, pais origen, comuna, region. Informacion demografica extensa.

10. **Sin CSRF**: No hay forms POST en este template, por lo que no aplica.

---

### Modulo comunicacion: Resumen

| # | Archivo | Hallazgos clave |
|---|---------|-----------------|
| 1 | `routes.py` | 8 rutas, anuncios+contactos+chat, sin CSRF, sin verificacion de acceso en chat, sender de anuncio no es current_user, N+1 masivo, polling AJAX |
| 2 | `__init__.py` | **VACIO** |
| 3 | `anuncios.html` | Vista unificada anuncios+contactos, form sin CSRF, expand/contraer con JS |
| 4 | `chat_lista.html` | Bandeja de entrada, contactos disponibles, badge no leidos |
| 5 | `chat_conversacion.html` | Chat con burbujas, polling 8s, XSS via innerHTML, sin CSRF |
| 6 | `contactos.html` | Directorio alumnos/funcionarios, tabs, filtro curso, links chat |
| 7 | `contacto_detalle.html` | Ficha completa: datos, apoderado, emergencia, medica, SEP |

---

Aqui va el `.md`:

```markdown
# Auditoría del Módulo: Comunicaciones

## 1. Resumen General

El módulo Comunicaciones es el sistema de comunicación interna del establecimiento. Gestiona anuncios dirigidos a cursos, un directorio de contactos (apoderados y funcionarios) con fichas detalladas, y un sistema de chat bidireccional con mensajería en tiempo real via polling AJAX. Es el módulo con más modelos cruzados (15+ modelos de ambas bases de datos) y la lógica de negocio más compleja del sistema.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/comunicacion/__init__.py` | Python | **Vacío** |
| `app/modules/comunicacion/routes.py` | Python | Backend: 8 rutas, anuncios, contactos, chat |
| `app/templates/comunicacion/anuncios.html` | Jinja2/HTML | Vista unificada: anuncios + contactos |
| `app/templates/comunicacion/chat_lista.html` | Jinja2/HTML | Bandeja de entrada del chat |
| `app/templates/comunicacion/chat_conversacion.html` | Jinja2/HTML | Conversación individual con polling |
| `app/templates/comunicacion/contactos.html` | Jinja2/HTML | Directorio de contactos (alumnos/funcionarios) |
| `app/templates/comunicacion/contacto_detalle.html` | Jinja2/HTML | Ficha detallada del estudiante |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2, pytz, fetch API (AJAX polling).

**Prefijo de rutas:** `/comunicacion`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas (15+ modelos)

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `EdugestAnnouncement` | Edugest | Anuncios (SenderPersonId, TargetOrganizationId, Title, Content, CreatedAt) |
| `EdugestChatMessage` | Edugest | Mensajes de chat (SenderPersonId, ReceiverPersonId, MessageText, SentAt, IsRead) |
| `EdugestUser` | Edugest | Usuarios (PersonId, RoleId, IsActive) |
| `EdugestEmergencyContact` | Edugest | Contactos de emergencia |
| `EdugestStudentHealth` | Edugest | Información médica |
| `EdugestStudentEnrollment` | Edugest | Matricula/datos demográficos |
| `EdugestPersonRelationshipDetail` | Edugest | Detalle de relación apoderado |
| `EdugestModule` | Edugest | Verificación de permisos inline |
| `EdugestRolePermission` | Edugest | Verificación de permisos inline |
| `Person` | Mineduc | Datos personales |
| `Organization` | Mineduc | Grados, cursos, establecimientos |
| `OrganizationPersonRole` | Mineduc | Vinculación persona-organización |
| `PersonRelationship` | Mineduc | Relaciones familiares (RefPersonRelationshipId=31) |
| `PersonTelephone` | Mineduc | Teléfonos |
| `PersonEmailAddress` | Mineduc | Emails |
| `PersonAddress` | Mineduc | Direcciones |
| `PersonIdentifier` | Mineduc | RUN (Id=51), IPE (Id=52) |
| `OrganizationRelationship` | Mineduc | Jerarquía organizacional |

### 2.2 Helpers

| Helper | Propósito |
|--------|-----------|
| `obtener_apoderado_estudiante(person_id)` | Busca apoderado principal con datos enriquecidos |
| `obtener_contactos_emergencia(person_id)` | Lista contactos de emergencia |
| `obtener_info_medica(person_id)` | Retorna tupla (health, enrollment) |
| `generar_wa_link(telefono)` | Genera enlace WhatsApp con normalización chilena |
| `enriquecer_cursos(cursos)` | Agrega nombre de grado padre |
| `obtener_contactos_para_chat()` | Contactos disponibles según rol (complejidad alta) |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/comunicacion/anuncios` | GET | `anuncios` | `@login_required` + permiso Com 1 | Vista unificada: anuncios + contactos |
| `/comunicacion/anuncios/nuevo` | POST | `nuevo_anuncio` | `@login_required` + permiso Com 2 | Crear anuncio |
| `/comunicacion/contactos` | GET | `contactos` | `@login_required` + permiso Com 1 | Directorio de contactos |
| `/comunicacion/contacto/<person_id>` | GET | `contacto_detalle` | `@login_required` + permiso Com 2 | Ficha del estudiante |
| `/comunicacion/chat` | GET | `chat_lista` | `@login_required` + permiso Com 1 | Bandeja de entrada |
| `/comunicacion/chat/<contacto_id>` | GET | `chat_conversacion` | `@login_required` + permiso Com 1 | Conversación |
| `/comunicacion/chat/<contacto_id>/enviar` | POST | `chat_enviar` | `@login_required` + permiso Com 1 + verif. inline | Enviar mensaje |
| `/comunicacion/chat/<contacto_id>/mensajes-nuevos` | GET | `chat_mensajes_nuevos` | `@login_required` + permiso Com 1 | API polling (JSON) |

---

## 4. Funcionalidades de Negocio

### 4.1 Anuncios
- Vista unificada con contactos en la misma página.
- Filtro por curso: muestra anuncios del curso o globales.
- `nuevo_anuncio`: Bloquea apoderados (RoleId=6). Busca primer usuario admin/director como sender (no usa `current_user`). Timezone Chile via pytz.

### 4.2 Contactos
- Dos vistas: Alumnos/Apoderados y Funcionarios.
- Vista alumnos: Lista estudiantes de un curso con apoderado y teléfono.
- Vista funcionarios: Lista staff (RoleId 1-4) con teléfono, email, cursos asignados.

### 4.3 Contacto Detalle
- Ficha completa: RUN, IPE, curso, teléfono, email.
- Apoderado con datos enriquecidos: parentesco, profesión, lugar trabajo, dirección, link WhatsApp.
- Contactos de emergencia con niveles educacionales decodificados.
- Información médica: grupo sanguíneo, alergias, enfermedades, medicamentos, restricciones.
- Datos SEP: Alumno Prioritario, Preferente, Beneficiario SEP.

### 4.4 Chat
- Bandeja de entrada con conversaciones agrupadas y mensajes no leidos.
- Conversación con burbujas, checkmarks (✓/✓✓), separadores de fecha.
- Polling AJAX cada 8 segundos para mensajes nuevos.
- Permisos de escritura verificados inline (no con decorador `nivel=2`).
- Contactos para chat: lógica compleja según rol:
  - Admin: todos los usuarios activos.
  - Profesor: apoderados de estudiantes de sus cursos.
  - Apoderado: profesores y funcionarios de cursos e instituciones de sus hijos.

---

## 5. Hallazgos de Auditoría

### 5.1 Seguridad — CRÍTICO

#### [S1] XSS via innerJS en polling de chat
`chat_conversacion.html` inserta mensajes via `bubble.innerHTML = '<p>' + m.texto + '</p>'`. Si el backend no sanitiza el texto del mensaje, un mensaje malicioso con `<script>` o `<img onerror>` podría ejecutar JavaScript en el navegador del receptor.
- **Archivo:** `chat_conversacion.html`, función `setInterval`
- **Riesgo:** CRÍTICO
- **Recomendación:** Usar `textContent` en lugar de `innerHTML`, o sanitizar en backend.

### 5.2 Seguridad — ALTO

#### [S2] Sin protección CSRF
`nuevo_anuncio` y `chat_enviar` son forms POST sin token CSRF.
- **Archivos:** `anuncios.html`, `chat_conversacion.html`
- **Riesgo:** ALTO

#### [S3] Sin verificación de acceso en chat
`chat_conversacion` y `chat_enviar` no verifican que `contacto_id` esté en la lista de contactos permitidos por `obtener_contactos_para_chat()`. Un usuario autenticado podría chatear con cualquier persona si conoce su `PersonId`.
- **Archivos:** `routes.py`, funciones `chat_conversacion`, `chat_enviar`
- **Riesgo:** ALTO

### 5.3 Seguridad — MEDIO

#### [S4] Sender de anuncio no es `current_user`
`nuevo_anuncio` busca el primer usuario con RoleId 1 o 2 como sender. Si el usuario actual es profesor (RoleId=3) con permiso Com 2, el anuncio se atribuye a un admin/director aleatorio.
- **Archivo:** `routes.py`, función `nuevo_anuncio`
- **Riesgo:** MEDIO

#### [S5] Verificación de permisos inline inconsistente
`chat_enviar` y `chat_conversacion` verifican permisos de escritura consultando la BD directamente en lugar de usar el decorador `@permiso_requerido` o el helper `permiso_requerido`. Replica la lógica del decorador.
- **Archivo:** `routes.py`
- **Riesgo:** MEDIO

### 5.4 Rendimiento

#### [P1] N+1 queries masivo en `obtener_contactos_para_chat()`
Para apoderados: itera hijos → cursos → profesores → usuarios. Para cada combinación ejecuta queries separadas. Potencialmente cientos de queries.
- **Riesgo:** ALTO

#### [P2] `chat_lista` carga TODOS los mensajes del usuario
Sin paginación, sin límite. Agrupa por contacto en Python.
- **Riesgo:** MEDIO

#### [P3] N+1 en anuncios
`a.sender` y `a.curso` se cargan via `db.session.get()` por cada anuncio.
- **Riesgo:** MEDIO

#### [P4] Polling cada 8 segundos
Cada usuario activo genera requests automáticos cada 8s. Con muchos usuarios, carga significativa en el servidor.
- **Riesgo:** MEDIO

### 5.5 Arquitectura

#### [A1] `__init__.py` vacío
El Blueprint se define en `routes.py` (patrón estándar del proyecto, no como biblioteca).

#### [A2] `anuncios` es vista unificada compleja
Combina anuncios y contactos en una sola ruta con dos filtros independientes. Funcional pero difícil de mantener.

#### [A3] `contactos` duplica lógica de `anuncios`
La consulta de cursos y la carga de contactos por curso están duplicadas entre `anuncios` y `contactos`.

#### [A4] Nivel educacional decodificado en template
9 niveles hardcodeados con if/elif en `contacto_detalle.html`. Debería estar en el modelo o backend.

#### [A5] Sin eliminación de mensajes o anuncios
No hay rutas para eliminar anuncios, mensajes, ni editarlos.

#### [A6] Integración con módulo biblioteca (ninguna)
A pesar de compartir modelos de Person, no hay integración directa.

---

## 6. Resumen de Hallazgos por Severidad

### Crítico (1)
- [S1] XSS via innerHTML en polling de chat

### Alto (3)
- [S2] Sin protección CSRF
- [S3] Sin verificación de acceso en chat (chat con cualquier PersonId)
- [P1] N+1 queries masivo en contactos para chat

### Medio (5)
- [S4] Sender de anuncio no es `current_user`
- [S5] Verificación de permisos inline inconsistente
- [P2] `chat_lista` carga todos los mensajes sin paginación
- [P3] N+1 en anuncios (sender y curso)
- [P4] Polling cada 8s genera carga con muchos usuarios

### Bajo (4)
- [A2] Vista unificada `anuncios` compleja
- [A3] Lógica duplicada entre `anuncios` y `contactos`
- [A4] Nivel educacional decodificado en template
- [A5] Sin eliminación de mensajes o anuncios

---

## 7. Endpoint Map Visual

```
GET  /comunicacion/anuncios                          → anuncios()              (permiso Com 1)
POST /comunicacion/anuncios/nuevo                    → nuevo_anuncio()         (permiso Com 2)
GET  /comunicacion/contactos                         → contactos()             (permiso Com 1)
GET  /comunicacion/contacto/<person_id>              → contacto_detalle()      (permiso Com 2)
GET  /comunicacion/chat                              → chat_lista()            (permiso Com 1)
GET  /comunicacion/chat/<contacto_id>                → chat_conversacion()     (permiso Com 1)
POST /comunicacion/chat/<contacto_id>/enviar         → chat_enviar()           (permiso Com 1 + verif.)
GET  /comunicacion/chat/<contacto_id>/mensajes-nuevos → chat_mensajes_nuevos() (permiso Com 1)
```

---

## 8. Diagrama de Flujo del Chat

```
Chat Lista (chat_lista)
  ├── Conversaciones activas (agrupadas por contacto)
  │   └── Badge de no leídos
  ├── Contactos disponibles (sin conversación)
  │   └── Según rol: admin→todos, prof→apoderados, apod→staff
  └── Chat Conversación (chat_conversacion)
      ├── Marca mensajes como leídos
      ├── Verifica permisos de escritura inline
      ├── Muestra burbujas (enviado/recibido)
      ├── Polling cada 8s (chat_mensajes_nuevos)
      └── Enviar mensaje (chat_enviar)
          ├── Verifica permisos inline
          ├── Valida texto no vacío, max 5000 chars
          └── Crea EdugestChatMessage
```

---

*Auditoría generada a partir del análisis de los 7 archivos del módulo comunicaciones (1 routes.py + 1 __init__.py vacío + 5 templates).*
```

---
