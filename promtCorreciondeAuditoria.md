Aqui va el documento completo. Es largo pero esta diseñado para que cualquier LLM pueda ejecutarlo sin ambiguedades:

```markdown
# PLAN DE REMEDIACIÓN DE SEGURIDAD — Sistema Edugest
## Instrucciones de implementación para LLM

---

## CONTEXTO DEL SISTEMA

**Stack:** Python 3.x, Flask, SQLite, Flask-Login, SQLAlchemy ORM, Jinja2, Tailwind CSS, Alpine.js.

**Estructura de proyecto:**
```
app/
├── __init__.py          # Factory, registro de blueprints, semilla de módulos
├── config.py            # Configuración de BD
├── models/
│   ├── mineduc.py       # Modelos MINEDUC (Person, Organization, etc.)
│   ├── edugest.py       # Modelos Edugest (User, Module, Permission, etc.)
│   └── EdugestCalendar.py # Modelo calendario
├── modules/
│   ├── admin/           # Panel admin, permissions.py (Sistema B muerto)
│   ├── auth/            # Login, logout, decorador de permisos
│   ├── portada/         # Bienvenida personalizada
│   ├── matricula/       # Registro de estudiantes
│   ├── calendario/      # Calendario académico
│   ├── comunicacion/    # Chat, anuncios, contactos
│   ├── evaluaciones/    # Evaluaciones digitales
│   ├── biblioteca/      # Biblioteca CRA
│   ├── libro_digital/   # Libro de clases
│   ├── gestion_usuarios/ # CRUD usuarios
│   ├── gestion_roles/   # CRUD roles y permisos
│   └── reportes/        # Reportes, PDFs, CSV
└── templates/
    └── [cada módulo]/   # Templates Jinja2
```

**Sistema de autenticación actual:**
- Flask-Login con `EdugestUser` (tabla de usuarios).
- `current_user` tiene: `UserId`, `Username`, `PersonId`, `RoleId`, `IsActive`.
- Decorador `@login_required` de Flask-Login.
- Decorador `@permiso_requerido(module_name, nivel)` definido en `auth/routes.py`.

**Sistema de permisos actual (fragmentado):**
- **Sistema A (activo):** `EdugestModule` + `EdugestRolePermission` con niveles 0/1/2.
- **Sistema B (muerto):** `admin/permissions.py` con `EdugestFeaturePermission` + `FEATURE_CATALOG`. Nunca se usa activamente.
- `RoleId=1` = Admin, tiene bypass total en todos los chequeos de permisos.

**Blueprint de auth (referencia):**
```python
# auth/routes.py — Decorador actual
def permiso_requerido(module_name, nivel=1):
    def decorador(f):
        @wraps(f)
        @login_required
        def funcion_decorada(*args, **kwargs):
            if current_user.RoleId == 1:
                return f(*args, **kwargs)
            modulo = EdugestModule.query.filter_by(ModuleName=module_name).first()
            if not modulo:
                abort(403)
            permiso = EdugestRolePermission.query.filter_by(
                RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
            ).first()
            if not permiso or permiso.PermissionLevel < nivel:
                return render_template('auth/unauthorized.html',
                    mensaje=f'No tienes permisos para acceder a {module_name}'), 403
            return f(*args, **kwargs)
        return funcion_decorada
    return decorador

def verificar_escritura(module_name):
    if current_user.RoleId == 1:
        return
    modulo = EdugestModule.query.filter_by(ModuleName=module_name).first()
    if not modulo:
        abort(403)
    permiso = EdugestRolePermission.query.filter_by(
        RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
    ).first()
    if not permiso or permiso.PermissionLevel < 2:
        abort(403)
```

**Credenciales por defecto (actuales):** admin / admin123.

---

## GUÍA DE NOMENCLATURA

Para evitar ambigüedad, este documento usa:

- `NombreModulo` → Nombre exacto del módulo en `EdugestModule.ModuleName` (ej: "Libro Digital", "Evaluaciones", "Comunicaciones", "Biblioteca", "Matrícula", "Calendario", "Reportes").
- `Nivel 1` → Solo lectura.
- `Nivel 2` → Lectura y escritura.
- `@permiso_requerido(NombreModulo, nivel=N)` → Decorador existente en `auth/routes.py`.
- `@login_required` → Decorador de Flask-Login.
- `CSRFProtect` → Extensión Flask-WTF para protección CSRF global.

---

# PARTE I — CAMBIOS GENERALES (SISTEMA)

Estos cambios afectan a TODO el sistema y deben implementarse primero.

---

## G1. Implementar protección CSRF global con Flask-WTF

### Archivo: `app/__init__.py`

**Objetivo:** Agregar CSRFProtect a la aplicación Flask para que TODOS los forms POST estén protegidos automáticamente.

**Cambios:**

1. Agregar import al inicio del archivo:
```python
from flask_wtf.csrf import CSRFProtect
```

2. Después de crear la app (`app = Flask(__name__)`), agregar:
```python
csrf = CSRFProtect(app)
```

3. Si existe `app.config['SECRET_KEY']`, verificar que NO sea vacío. Si no existe, agregar:
```python
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cambiar-esta-clave-en-produccion')
```

### Archivo: `templates/base.html`

**Objetivo:** Inyectar el token CSRF en un meta tag para que el JavaScript pueda leerlo en peticiones AJAX.

**Cambios:** Dentro del bloque `<head>`, agregar:
```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

### Archivo: TODOS los templates con forms POST

**Objetivo:** Agregar campo hidden con token CSRF a cada formulario.

**Cambios:** Dentro de CADA `<form method="post">` o `<form method="POST">`, agregar como primer hijo:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

**Templates que requieren este cambio (lista completa):**

| Módulo | Template | Forms POST |
|--------|----------|------------|
| auth | `login.html` | 1 form |
| admin | `dashboard.html` | Toggle módulos |
| admin | `permisos.html` | Guardar permisos |
| admin | `rol_form.html` | Crear/editar rol |
| admin | `usuario_form.html` | Crear/editar usuario |
| admin | `usuarios.html` | Toggle usuario, eliminar usuario |
| matricula | `formulario.html` | Crear estudiante |
| calendario | `index.html` | Crear evento, eliminar evento |
| comunicacion | `anuncios.html` | Nuevo anuncio |
| comunicacion | `chat_conversacion.html` | Enviar mensaje |
| evaluaciones | `crear_evaluacion.html` | Crear evaluación |
| evaluaciones | `crear_instrumento.html` | Crear instrumento |
| evaluaciones | `disenar_preguntas.html` | Crear pregunta |
| evaluaciones | `rendir.html` | Enviar respuestas |
| evaluaciones | `resultados.html` | Nota manual, eliminar nota, visibilidad |
| biblioteca | `nuevo_libro.html` | Crear/editar libro |
| biblioteca | `catalogo.html` | Eliminar libro |
| biblioteca | `prestamos.html` | Devolver, renovar |
| biblioteca | `nuevo_prestamo.html` | Crear préstamo |
| libro_digital | `grados.html` | Actualizar grado |
| libro_digital | `asignaturas.html` | Crear asignatura |
| libro_digital | `unidades.html` | Crear unidad/clase |
| libro_digital | `lista_curso.html` | Registrar asistencia |
| libro_digital | `anotaciones.html` | Crear anotación |
| gestion_usuarios | `formulario.html` | Crear/editar usuario |
| gestion_usuarios | `listar.html` | Toggle activo |
| gestion_roles | `nuevo_rol.html` | Crear rol |
| gestion_roles | `editar_permisos.html` | Editar permisos |
| reportes | `curso.html` | Filtros de fecha |

### Peticiones AJAX con fetch

Para llamadas AJAX POST que usan `fetch()`, incluir el token CSRF en los headers:

```javascript
// Obtener token del meta tag
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

// En cada fetch POST, agregar header:
fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
})
```

**Archivos con fetch POST que necesitan este cambio:**
- `comunicacion/chat_conversacion.html` — polling de mensajes (si envía POST)
- `reportes/notas_sumativas.html` — toggle de sumativa
- `biblioteca/catalogo.html` — eliminar libro (si usa fetch)

### Excepciones

Si algún endpoint necesita estar exento de CSRF (por ejemplo, webhooks externos), usar:
```python
@csrf.exempt
def mi_endpoint():
    ...
```

En este sistema NO hay endpoints que necesiten exención.

### Dependencia

Agregar `flask-wtf` a `requirements.txt` si no existe:
```
flask-wtf>=1.2.0
```

---

## G2. Unificar sistema de permisos — Eliminar Sistema B muerto

### Archivo: `app/modules/admin/permissions.py`

**Objetivo:** Desactivar completamente el sistema RBAC muerto que importa modelos inexistentes.

**Cambios:**

Opción A (recomendada): Vaciar el archivo dejando solo comentarios:
```python
"""
Sistema RBAC antiguo desactivado.
El sistema de permisos activo usa EdugestRolePermission + EdugestModule
(definido en auth/routes.py con el decorador permiso_requerido).
Este archivo se mantiene como referencia histórica.
"""
```

Opción B: Eliminar el archivo completamente.

**Verificar que NINGÚN archivo importe desde `admin/permissions.py`:**
- Buscar: `from app.modules.admin.permissions import`
- Buscar: `from app.modules.admin import permissions`
- Si existen imports, eliminarlos.

### Archivos: Templates de admin que referencian `can()`

Los templates `admin/roles.html`, `admin/usuarios.html`, `admin/permisos.html` usan `can(feature, permission_type)` que proviene de `permissions.py` como context processor.

**Cambios:** Si se elimina `permissions.py`, estos templates deben migrar a usar `user_permisos`:
```jinja2
{# ANTES (Sistema B) #}
{% if can('admin_roles_crud', 'edit') %}

{# DESPUÉS (Sistema A) #}
{% if current_user.RoleId == 1 %}
```

**Nota:** Los templates de admin son solo accesibles por admins (una vez corregido G3), por lo que la verificación de permisos puede simplificarse a `current_user.RoleId == 1`.

---

## G3. Agregar verificación de admin a rutas de admin

### Archivo: `app/modules/admin/routes.py`

**Objetivo:** Proteger las 2 rutas existentes con autenticación y verificación de admin.

**Cambios:**

1. Agregar imports:
```python
from flask_login import login_required, current_user
from functools import wraps
```

2. Crear helper de admin (o importar desde auth):
```python
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.RoleId != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated
```

3. Agregar decorador a AMBAS rutas:
```python
@admin_bp.route('/')
@admin_required
def dashboard():
    # ... código existente sin cambios ...

@admin_bp.route('/toggle-module/<int:module_id>', methods=['POST'])
@admin_required
def toggle_module(module_id):
    # ... código existente sin cambios ...
```

---

## G4. Eliminar credenciales por defecto del template

### Archivo: `app/templates/admin/login.html`

**Objetivo:** Eliminar la exposición de credenciales admin/admin123.

**Cambios:**
- Buscar y eliminar cualquier texto que diga "Usuario por defecto: admin / admin123" o similar.
- Eliminar cualquier `<p>`, `<div>`, o `<span>` que muestre credenciales.

### Archivo: `app/modules/admin/permissions.py` (en `init_default_admin_user`)

**Objetivo:** Cambiar la contraseña por defecto a una más segura o forzar cambio.

**Cambios:** En la función `init_default_admin_user()`:
```python
# ANTES
admin_password = 'admin123'

# DESPUÉS — Generar contraseña aleatoria y mostrar en consola
import secrets
admin_password = secrets.token_urlsafe(16)
print(f"[SEED] Usuario admin creado. Contraseña temporal: {admin_password}")
print(f"[SEED] CAMBIE esta contraseña inmediatamente después del primer login.")
```

Alternativa conservadora (si no se quiere romper el flujo de setup):
```python
admin_password = 'admin123'  # ⚠️ CAMBIAR EN PRODUCCIÓN
# Agregar log de advertencia:
import logging
logging.warning("⚠️ Usando contraseña por defecto para admin. Cambiar inmediatamente.")
```

---

## G5. Crear módulo compartido de helpers de permisos

### Archivo nuevo: `app/utils/permisos.py`

**Objetivo:** Centralizar las funciones de permisos que están duplicadas en múltiples módulos.

**Contenido:**
```python
"""
Helpers centralizados de permisos.
Todas las funciones de verificación de permisos deben importarse desde aquí.
"""
from flask_login import current_user
from flask import abort
from app.models.edugest import EdugestModule, EdugestRolePermission


def get_permiso_modulo(module_name):
    """
    Retorna el nivel de permiso (0, 1, 2) del usuario actual para un módulo.
    Admin (RoleId=1) retorna 2 automáticamente.
    """
    if current_user.RoleId == 1:
        return 2
    modulo = EdugestModule.query.filter_by(ModuleName=module_name).first()
    if not modulo:
        return 0
    permiso = EdugestRolePermission.query.filter_by(
        RoleId=current_user.RoleId, ModuleId=modulo.ModuleId
    ).first()
    return permiso.PermissionLevel if permiso else 0
```

**Después de crear este archivo, actualizar los imports en:**
- `matricula/routes.py` → Eliminar `get_permiso_modulo()` local, importar de `app.utils.permisos`.
- `reportes/routes.py` → Eliminar `get_permiso_modulo()` local, importar de `app.utils.permisos`.
- `calendario/routes.py` → Eliminar `_get_nivel_permiso()` local, importar `get_permiso_modulo` de `app.utils.permisos` y usar `get_permiso_modulo('Calendario')`.
- `evaluaciones/routes.py` → Eliminar `_es_nivel_2_evaluaciones()` local, usar `get_permiso_modulo('Evaluaciones') >= 2`.

### Archivo nuevo: `app/utils/__init__.py`

Crear archivo vacío para hacer de `utils` un paquete Python.

---

## G6. Crear helper centralizado de visibilidad de organizaciones

### Archivo nuevo: `app/utils/organizaciones.py`

**Objetivo:** Eliminar la duplicación de `_get_org_ids_for_user()` entre portada y calendario.

**Contenido:**
```python
"""
Helpers centralizados para consultas de organizaciones.
"""
from flask_login import current_user
from app.models.mineduc import (
    Organization, OrganizationRelationship, OrganizationPersonRole, PersonRelationship
)


def get_org_ids_for_user():
    """
    Retorna la lista de OrganizationIds que el usuario actual puede ver.
    Admin retorna [] (significa "ve todo").
    """
    if current_user.RoleId == 1:
        return []  # Admin ve todo

    org_ids = []

    if current_user.RoleId == 6:
        # Estudiante: su curso, grado y asignaturas
        matriculas = OrganizationPersonRole.query.filter_by(
            PersonId=current_user.PersonId, RoleId=6, ExitDate=None
        ).all()
        for mat in matriculas:
            org = Organization.query.get(mat.OrganizationId)
            if org and org.RefOrganizationTypeId == 21:
                org_ids.append(org.OrganizationId)
                rel = OrganizationRelationship.query.filter_by(
                    OrganizationId=org.OrganizationId
                ).first()
                if rel:
                    org_ids.append(rel.ParentOrganizationId)
                    asigns = Organization.query.join(
                        OrganizationRelationship,
                        Organization.OrganizationId == OrganizationRelationship.OrganizationId
                    ).filter(
                        OrganizationRelationship.ParentOrganizationId == rel.ParentOrganizationId,
                        Organization.RefOrganizationTypeId == 22
                    ).all()
                    for asig in asigns:
                        org_ids.append(asig.OrganizationId)

    elif current_user.RoleId == 5:
        # Apoderado: organizaciones de sus hijos
        relaciones = PersonRelationship.query.filter_by(
            RelatedPersonId=current_user.PersonId
        ).all()
        for rel in relaciones:
            rol_hijo = OrganizationPersonRole.query.filter_by(
                PersonId=rel.PersonId, RoleId=6, ExitDate=None
            ).first()
            if rol_hijo:
                org_ids.append(rol_hijo.OrganizationId)
                org = Organization.query.get(rol_hijo.OrganizationId)
                if org:
                    org_rel = OrganizationRelationship.query.filter_by(
                        OrganizationId=org.OrganizationId
                    ).first()
                    if org_rel:
                        org_ids.append(org_rel.ParentOrganizationId)
                        asigns = Organization.query.join(
                            OrganizationRelationship,
                            Organization.OrganizationId == OrganizationRelationship.OrganizationId
                        ).filter(
                            OrganizationRelationship.ParentOrganizationId == org_rel.ParentOrganizationId,
                            Organization.RefOrganizationTypeId == 22
                        ).all()
                        for asig in asigns:
                            org_ids.append(asig.OrganizationId)

    else:
        # Profesor, Director, Inspector: organizaciones donde tiene rol + hermanas
        roles = OrganizationPersonRole.query.filter_by(
            PersonId=current_user.PersonId, ExitDate=None
        ).all()
        for rol in roles:
            org_ids.append(rol.OrganizationId)
            rel = OrganizationRelationship.query.filter_by(
                OrganizationId=rol.OrganizationId
            ).first()
            if rel:
                parent_id = rel.ParentOrganizationId
                org_ids.append(parent_id)
                hermanas = Organization.query.join(
                    OrganizationRelationship,
                    Organization.OrganizationId == OrganizationRelationship.OrganizationId
                ).filter(
                    OrganizationRelationship.ParentOrganizationId == parent_id
                ).all()
                for h in hermanas:
                    org_ids.append(h.OrganizationId)

    return list(set(org_ids)) if org_ids else []
```

**Después de crear este archivo, actualizar imports en:**
- `portada/routes.py` → Eliminar lógica inline de org_ids, importar de `app.utils.organizaciones`.
- `calendario/routes.py` → Eliminar `_get_org_ids_for_user()`, importar de `app.utils.organizaciones`.

---

# PARTE II — CAMBIOS POR MÓDULO

---

## MÓDULO: REPORTES (CRÍTICO — Prioridad 0)

### Problema central: 10 rutas sin @login_required, PDFs y CSVs accesibles sin autenticación.

### R2.1 — Agregar @login_required y @permiso_requerido a TODAS las rutas

**Archivo:** `app/modules/reportes/routes.py`

**Cambios por ruta:**

| Ruta actual | Decorador a agregar |
|-------------|-------------------|
| `index` | `@login_required` + verificación inline existente |
| `reporte_curso(curso_id)` | `@permiso_requerido('Reportes', nivel=1)` |
| `reporte_grado(grado_id)` | `@permiso_requerido('Reportes', nivel=1)` |
| `reporte_notas_sumativas(org_id)` | `@permiso_requerido('Reportes', nivel=1)` |
| `configurar_sumativas(org_id)` | `@permiso_requerido('Reportes', nivel=2)` |
| `guardar_sumativa_ajax(instrument_id)` | `@permiso_requerido('Reportes', nivel=2)` |
| `grafico_asistencia(curso_id)` | `@permiso_requerido('Reportes', nivel=1)` |
| `exportar_asistencia(curso_id)` | `@permiso_requerido('Reportes', nivel=1)` |
| `informe_notas_pdf(curso_id, rol_id)` | `@permiso_requerido('Reportes', nivel=1)` |
| `grafico_grado(grado_id)` | `@permiso_requerido('Reportes', nivel=1)` |

**Imports a agregar al inicio de routes.py:**
```python
from flask_login import login_required, current_user
from app.modules.auth.routes import permiso_requerido
```

**Patrón de aplicación:**
```python
# ANTES
@reportes_bp.route('/curso/<int:curso_id>')
def reporte_curso(curso_id):
    ...

# DESPUÉS
@reportes_bp.route('/curso/<int:curso_id>')
@permiso_requerido('Reportes', nivel=1)
def reporte_curso(curso_id):
    ...
```

**Para rutas con GET y POST (configurar_sumativas):**
```python
# ANTES
@reportes_bp.route('/asignatura/<int:org_id>/configurar-sumativas', methods=['GET', 'POST'])
def configurar_sumativas(org_id):
    if request.method == 'GET':
        # verificación inline de permisos
    ...

# DESPUÉS
@reportes_bp.route('/asignatura/<int:org_id>/configurar-sumativas', methods=['GET', 'POST'])
@permiso_requerido('Reportes', nivel=2)
def configurar_sumativas(org_id):
    # Eliminar verificación inline (el decorador ya lo hace)
    ...
```

### R2.2 — Eliminar helper `get_permiso_modulo` local

**Archivo:** `app/modules/reportes/routes.py`

**Cambios:** Eliminar la función `get_permiso_modulo()` definida localmente. Importar desde `app.utils.permisos` (ver G5).

### R2.3 — Agregar filtro de acceso por organización

**Archivo:** `app/modules/reportes/routes.py`

**Objetivo:** Verificar que el usuario tenga acceso a la organización solicitada.

**Patrón para `reporte_curso`:**
```python
from app.utils.organizaciones import get_org_ids_for_user

@reportes_bp.route('/curso/<int:curso_id>')
@permiso_requerido('Reportes', nivel=1)
def reporte_curso(curso_id):
    # Verificar acceso a la organización
    if current_user.RoleId != 1:
        org_ids = get_org_ids_for_user()
        if org_ids and curso_id not in org_ids:
            abort(403)
    # ... resto del código existente ...
```

**Aplicar el mismo patrón a:**
- `reporte_curso(curso_id)` — verificar `curso_id`
- `reporte_grado(grado_id)` — verificar que algún curso del grado esté en `org_ids`
- `reporte_notas_sumativas(org_id)` — verificar `org_id`
- `grafico_asistencia(curso_id)` — verificar `curso_id`
- `exportar_asistencia(curso_id)` — verificar `curso_id`
- `informe_notas_pdf(curso_id, rol_id)` — verificar `curso_id`
- `grafico_grado(grado_id)` — verificar grado

---

## MÓDULO: ADMIN (CRÍTICO — Prioridad 0)

### A2.1 — Proteger rutas (ya cubierto en G3)

### A2.2 — Eliminar credenciales de template (ya cubierto en G4)

### A2.3 — Desactivar Sistema B (ya cubierto en G2)

### A2.4 — Agregar CSRF a forms de admin

**Archivos:** `dashboard.html`, `permisos.html`, `rol_form.html`, `usuario_form.html`, `usuarios.html`

Ya cubierto por G1.

### A2.5 — Agregar verificación de permisos al toggle de usuario en template

**Archivo:** `app/templates/admin/usuarios.html`

**Cambios:** En el botón de toggle (activar/desactivar), agregar condición:
```html
{# ANTES #}
<button onclick="...">Desactivar</button>

{# DESPUÉS #}
{% if current_user.RoleId == 1 %}
<button onclick="...">Desactivar</button>
{% endif %}
```

---

## MÓDULO: COMUNICACIONES (CRÍTICO — Prioridad 1)

### C3.1 — Corregir XSS via innerHTML en chat

**Archivo:** `app/templates/comunicacion/chat_conversacion.html`

**Cambios:** En la función JavaScript que inserta mensajes via polling, reemplazar `innerHTML` por `textContent`.

**Buscar código similar a:**
```javascript
// ANTES (VULNERABLE)
bubble.innerHTML = '<p>' + m.texto + '</p>';
// o
bubble.innerHTML = m.texto;
```

**Reemplazar con:**
```javascript
// DESPUÉS (SEGURO)
const p = document.createElement('p');
p.textContent = m.texto;
bubble.appendChild(p);
```

**Si el mensaje necesita formato HTML legítimo (negritas, etc.):**
```javascript
// Alternativa: sanitizar
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
bubble.innerHTML = '<p>' + sanitizeHTML(m.texto) + '</p>';
```

**RECOMENDACIÓN:** Usar `textContent` que es más seguro. Si se necesita formato, crear un sistema de markdown simple en el backend.

### C3.2 — Verificar acceso en chat

**Archivo:** `app/modules/comunicacion/routes.py`

**Objetivo:** Verificar que el usuario tenga permiso para chatear con `contacto_id`.

**Cambios en `chat_conversacion` y `chat_enviar`:**

1. Importar o reutilizar `obtener_contactos_para_chat()` (ya existe en el archivo).

2. Al inicio de AMBAS funciones, agregar:
```python
# Después de @permiso_requerido('Comunicaciones', nivel=1)
contactos_permitidos = obtener_contactos_para_chat()
contactos_ids = [c['person_id'] for c in contactos_permitidos]

if contacto_id not in contactos_ids:
    flash('No tienes permiso para acceder a esta conversación.', 'danger')
    return redirect(url_for('comunicacion.chat_lista'))
```

### C3.3 — Corregir sender de anuncios

**Archivo:** `app/modules/comunicacion/routes.py`

**Objetivo:** Usar `current_user.PersonId` como sender del anuncio.

**Cambios en `nuevo_anuncio`:**
```python
# ANTES
sender = EdugestUser.query.filter(
    EdugestUser.RoleId.in_([1, 2])
).first()

# DESPUÉS
sender_person_id = current_user.PersonId
```

Y al crear el anuncio:
```python
# ANTES
anuncio = EdugestAnnouncement(
    SenderPersonId=sender.PersonId if sender else None,
    ...
)

# DESPUÉS
anuncio = EdugestAnnouncement(
    SenderPersonId=sender_person_id,
    ...
)
```

---

## MÓDULO: MATRÍCULA (CRÍTICO — Prioridad 1)

### M4.1 — Agregar verificación de permisos a endpoints AJAX

**Archivo:** `app/modules/matricula/routes.py`

**Objetivo:** Los 4 endpoints AJAX deben verificar que el usuario tenga permisos de lectura (nivel >= 1).

**Cambios:** Agregar al inicio de cada endpoint AJAX:

```python
@matricula_bp.route('/ajax/grados/<int:nivel_id>')
@login_required
def ajax_grados(nivel_id):
    # NUEVO: Verificar permisos
    permiso = get_permiso_modulo('Matrícula')
    if permiso < 1:
        return jsonify({'error': 'Sin permisos'}), 403
    # ... resto del código ...
```

**Aplicar a las 4 rutas:**
- `ajax_grados`
- `ajax_cursos`
- `ajax_buscar_estudiante`
- `ajax_datos_estudiante`

**Nota:** Usar `get_permiso_modulo` importado de `app.utils.permisos` (ver G5).

### M4.2 — Corregir RUT sin validación de dígito verificador

**Archivo:** `app/modules/matricula/routes.py`

**Objetivo:** Agregar validación de dígito verificador chileno.

**Cambios:** Agregar función helper:
```python
def validar_rut(rut_limpio):
    """
    Valida RUT chileno con algoritmo módulo 11.
    rut_limpio debe ser sin puntos, con guión: '12345678-9'
    Retorna True si el dígito verificador es correcto.
    """
    try:
        partes = rut_limpio.split('-')
        if len(partes) != 2:
            return False
        cuerpo = partes[0]
        dv = partes[1].upper()

        if not cuerpo.isdigit():
            return False

        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2

        resto = 11 - (suma % 11)
        if resto == 11:
            dv_esperado = '0'
        elif resto == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(resto)

        return dv == dv_esperado
    except (ValueError, IndexError):
        return False
```

**En la función `normalizar_rut`, después de formatear, agregar validación:**
```python
def normalizar_rut(rut):
    # ... código existente de limpieza y formato ...
    rut_formateado = f"{cuerpo}-{dv}"

    # NUEVO: Validar dígito verificador
    if not validar_rut(rut_formateado):
        return None  # RUT inválido

    return rut_formateado
```

**En `nuevo_estudiante`, usar la validación:**
```python
rut_normalizado = normalizar_rut(rut_raw)
if rut_normalizado is None:
    flash('El RUT ingresado no es válido. Verifique el dígito verificador.', 'danger')
    return redirect(url_for('matricula.nuevo_estudiante'))
```

### M4.3 — Convertir warning de RUT en error que bloquee

**Archivo:** `app/modules/matricula/routes.py`

**Cambios:** En la validación de formato de RUT:
```python
# ANTES
if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$', rut_normalizado):
    flash('Formato de RUT inválido', 'warning')  # No detiene

# DESPUÉS
if not re.match(r'^\d{1,2}\.\d{3}\.\d{3}-[\dKk]$', rut_normalizado):
    flash('Formato de RUT inválido. Use el formato: xx.xxx.xxx-x', 'danger')
    return redirect(url_for('matricula.nuevo_estudiante'))  # DETIENE el proceso
```

### M4.4 — No exponer información interna en errores

**Archivo:** `app/modules/matricula/routes.py`

**Cambios:** En el bloque `except` de `nuevo_estudiante`:
```python
# ANTES
except Exception as e:
    db.session.rollback()
    flash(f'Error al guardar: {str(e)}', 'danger')

# DESPUÉS
except Exception as e:
    db.session.rollback()
    import logging
    logging.error(f'Error al guardar matrícula: {str(e)}')
    flash('Ocurrió un error al guardar. Por favor, intente nuevamente.', 'danger')
```

---

## MÓDULO: EVALUACIONES (ALTO — Prioridad 2)

### E5.1 — Agregar @permiso_requerido a rutas desprotegidas

**Archivo:** `app/modules/evaluaciones/routes.py`

| Ruta | Decorador a agregar |
|------|-------------------|
| `asignaturas_por_grado(grado_id)` | `@permiso_requerido('Evaluaciones', nivel=1)` |
| `unidades_asignatura(org_id)` | `@permiso_requerido('Evaluaciones', nivel=1)` |
| `resultados(inst_id)` | `@permiso_requerido('Evaluaciones', nivel=1)` |
| `rendir(inst_id, alumno_id)` | `@login_required` (mantener bloqueos manuales existentes, son más granulares) |

### E5.2 — Agregar confirmación al enviar examen

**Archivo:** `app/templates/evaluaciones/rendir.html`

**Cambios:** En el botón de envío:
```html
{# ANTES #}
<button type="submit">Finalizar y Enviar Examen</button>

{# DESPUÉS #}
<button type="submit"
        onclick="return confirm('¿Estás seguro de enviar tu examen? No podrás modificar tus respuestas después de enviarlo.')">
    Finalizar y Enviar Examen
</button>
```

### E5.3 — Validar MIME type en upload de imágenes

**Archivo:** `app/modules/evaluaciones/routes.py`

**Cambios en `disenar_preguntas_post`:**
```python
import imghdr

# Después de obtener el archivo
if imagen and imagen.filename:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB

    # Verificar extensión
    ext = imagen.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash('Formato de imagen no permitido.', 'danger')
        return redirect(...)

    # Verificar tamaño
    imagen.seek(0, 2)  # Ir al final
    size = imagen.tell()
    imagen.seek(0)  # Volver al inicio
    if size > MAX_SIZE:
        flash('La imagen no puede superar 5MB.', 'danger')
        return redirect(...)

    # Verificar MIME type real
    header = imagen.read(512)
    imagen.seek(0)
    mime = imghdr.what(None, h=header)
    if mime not in ('png', 'jpeg', 'gif'):
        flash('El archivo no es una imagen válida.', 'danger')
        return redirect(...)

    # Procesar imagen (código existente)
    ...
```

### E5.4 — Eliminar helper `_es_nivel_2_evaluaciones` local

**Archivo:** `app/modules/evaluaciones/routes.py`

Reemplazar con `get_permiso_modulo('Evaluaciones') >= 2` importado de `app.utils.permisos`.

---

## MÓDULO: LIBRO DIGITAL (ALTO — Prioridad 2)

### L6.1 — Agregar @permiso_requerido a rutas desprotegidas

**Archivo:** `app/modules/libro_digital/routes.py`

| Ruta | Decorador a agregar |
|------|-------------------|
| `listar_grados()` | `@permiso_requerido('Libro Digital', nivel=1)` |
| `asignaturas_por_grado(grado_id)` | `@permiso_requerido('Libro Digital', nivel=1)` |
| `ver_unidades(org_id)` | `@permiso_requerido('Libro Digital', nivel=1)` |
| `registrar_clase_get(org_id)` | `@permiso_requerido('Libro Digital', nivel=1)` |

### L6.2 — Corregir verificación de permisos incorrecta para evaluaciones

**Archivo:** `app/modules/libro_digital/routes.py`, función `ver_unidades`

**Cambios:**
```python
# ANTES (INCORRECTO)
nivel_eval = get_permiso_modulo('Evaluaciones')

# DESPUÉS (CORRECTO — mantiene la lógica de filtrar evaluaciones por permiso de evaluaciones,
# pero la verificación base es del módulo correcto)
# La función ver_unidades consulta permisos de "Evaluaciones" para decidir
# si mostrar evaluaciones no publicadas. Esto es CORRECTO en intención
# pero el helper debe importarse de app.utils.permisos.
```

**Nota:** La lógica actual consulta permisos de "Evaluaciones" para filtrar visibilidad de evaluaciones dentro de libro digital. Esto es correcto conceptualmente (un profesor con permisos de evaluaciones puede ver evaluaciones no publicadas). Solo cambiar el import del helper.

### L6.3 — Corregir permisos cruzados en "Volver"

**Archivo:** `app/templates/libro_digital/unidades.html`

**Cambios:**
```html
{# ANTES (INCORRECTO — usa permisos de Evaluaciones para link de Libro Digital) #}
{% if user_permisos.get('Evaluaciones', 0) >= 2 %}
<a href="{{ url_for('libro_digital.asignaturas_por_grado', ...) }}">Volver a Asignaturas</a>
{% endif %}

{# DESPUÉS (CORRECTO — usa permisos de Libro Digital) #}
{% if user_permisos.get('Libro Digital', 0) >= 1 %}
<a href="{{ url_for('libro_digital.asignaturas_por_grado', ...) }}">Volver a Asignaturas</a>
{% endif %}
```

---

## MÓDULO: GESTIÓN DE USUARIOS (CRÍTICO — Prioridad 1)

### U7.1 — Cambiar resetear_password a solo POST

**Archivo:** `app/modules/gestion_usuarios/routes.py`

**Cambios:**
```python
# ANTES
@gestion_usuarios_bp.route('/<int:user_id>/resetear-password', methods=['GET', 'POST'])
@login_required
def resetear_password(user_id):
    ...

# DESPUÉS
@gestion_usuarios_bp.route('/<int:user_id>/resetear-password', methods=['POST'])
@login_required
def resetear_password(user_id):
    ...
```

### U7.2 — Cambiar el botón de link a form

**Archivo:** `app/templates/gestion_usuarios/formulario.html`

**Cambios:**
```html
{# ANTES (vulnerable a CSRF via GET) #}
<a href="{{ url_for('gestion_usuarios.resetear_password', user_id=usuario.UserId) }}"
   class="...">
    Resetear Contraseña
</a>

{# DESPUÉS (form POST con CSRF) #}
<form method="POST"
      action="{{ url_for('gestion_usuarios.resetear_password', user_id=usuario.UserId) }}"
      onsubmit="return confirm('¿Estás seguro de resetear la contraseña? Se generará una nueva contraseña temporal.')">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button type="submit" class="...">
        Resetear Contraseña
    </button>
</form>
```

### U7.3 — No mostrar contraseña temporal en flash

**Archivo:** `app/modules/gestion_usuarios/routes.py`

**Cambios:**
```python
# ANTES
flash(f'Contraseña de {usuario.Username} reseteada. Nueva contraseña temporal: {nueva_pass}', 'success')

# DESPUÉS — Mostrar contraseña en template dedicado (más seguro)
# Opción A: Mostrar solo una vez en un template que advierta al admin
flash(f'Contraseña de {usuario.Username} reseteada exitosamente. '
      f'Nueva contraseña temporal: {nueva_pass}. '
      f'Guárdela y compártela por un canal seguro. '
      f'El usuario debería cambiarla en su próximo inicio de sesión.', 'warning')
```

**Alternativa más segura (recomendada):** Crear un template que muestre la contraseña con botón de copiar y advertencia de seguridad, en lugar de flash message.

### U7.4 — Eliminar funciones duplicadas

**Archivo:** `app/modules/gestion_usuarios/routes.py`

**Cambios:** Las funciones `_es_profesor_rol()`, `_obtener_grados_con_cursos()` y `_obtener_profesor_jefe()` están definidas DOS veces (al inicio y al final del archivo). Eliminar las definiciones duplicadas, conservar una sola copia de cada una.

---

## MÓDULO: GESTIÓN DE ROLES (MEDIO — Prioridad 2)

### R8.1 — Validar nivel de permiso en backend

**Archivo:** `app/modules/gestion_roles/routes.py`

**Cambios en `editar_permisos`:**
```python
# Después de obtener los valores del formulario
for modulo in modulos:
    nivel = request.form.get(f'permiso_{modulo.ModuleId}', '0')
    try:
        nivel = int(nivel)
    except ValueError:
        nivel = 0

    # NUEVO: Validar rango
    nivel = max(0, min(2, nivel))  # Clamp entre 0 y 2

    permisos_data.append((modulo.ModuleId, nivel))
```

### R8.2 — Validar RoleId en crear_rol

**Archivo:** `app/modules/gestion_roles/routes.py`

**Cambios en `crear_rol`:**
```python
# Después de obtener role_id del formulario
try:
    role_id = int(request.form.get('role_id', 0))
except ValueError:
    flash('ID de rol inválido.', 'danger')
    return redirect(...)

# NUEVO: Validar rango
if role_id < 1 or role_id > 99:
    flash('El ID del rol debe estar entre 1 y 99.', 'danger')
    return redirect(...)
```

---

## MÓDULO: CALENDARIO (MEDIO — Prioridad 2)

### CA9.1 — Usar helper centralizado de organizaciones

**Archivo:** `app/modules/calendario/routes.py`

**Cambios:** Eliminar `_get_org_ids_for_user()` local. Importar de `app.utils.organizaciones`:
```python
from app.utils.organizaciones import get_org_ids_for_user
```

Y reemplazar todas las llamadas:
```python
# ANTES
org_ids = _get_org_ids_for_user()

# DESPUÉS
org_ids = get_org_ids_for_user()
```

### CA9.2 — Eliminar helper local de permisos

**Archivo:** `app/modules/calendario/routes.py`

Eliminar `_get_nivel_permiso()`. Importar de `app.utils.permisos`:
```python
from app.utils.permisos import get_permiso_modulo
```

Y reemplazar:
```python
# ANTES
nivel_permiso = _get_nivel_permiso()

# DESPUÉS
nivel_permiso = get_permiso_modulo('Calendario')
```

---

## MÓDULO: BIBLIOTECA (MEDIO — Prioridad 3)

### B10.1 — Agregar validación de URL en links de descarga

**Archivo:** `app/templates/biblioteca/catalogo.html`

**Cambios:** Validar que `libro.FileUrl` sea URL válida antes de renderizar:
```html
{# ANTES #}
<a href="{{ libro.FileUrl }}">Descargar</a>

{# DESPUÉS #}
{% if libro.FileUrl and libro.FileUrl.startswith(('http://', 'https://')) %}
<a href="{{ libro.FileUrl }}" target="_blank" rel="noopener noreferrer">Descargar</a>
{% endif %}
```

### B10.2 — Agregar límite a renovaciones

**Archivo:** `app/modules/biblioteca/routes.py`

**Cambios en `renovar_prestamo`:**
```python
# Después de obtener el préstamo
MAX_RENOVACIONES = 3

# Contar renovaciones previas (necesita campo en modelo o lógica alternativa)
# Opción simple: verificar que la fecha de vencimiento no supere un máximo
from datetime import timedelta
MAX_DIAS_PRESTAMO = 60  # 2 meses máximo

if prestamo.LoanDate + timedelta(days=MAX_DIAS_PRESTAMO) < prestamo.DueDate + timedelta(days=dias_extra):
    flash(f'No se puede renovar. El préstamo no puede exceder {MAX_DIAS_PRESTAMO} días desde el inicio.', 'warning')
    return redirect(...)
```

---

## MÓDULO: AUTH (MEDIO — Prioridad 2)

### AU11.1 — Implementar validación de URL next

**Archivo:** `app/modules/auth/routes.py`

**Cambios:**
```python
from urllib.parse import urlparse

def is_safe_url(target):
    """Verifica que la URL sea interna (mismo dominio)."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    return (test_url.scheme in ('http', 'https') and
            ref_url.netloc == test_url.netloc)

# En la función login, antes del redirect:
next_page = request.args.get('next')
if next_page and not is_safe_url(next_page):
    next_page = None  # Ignorar URL externa
```

### AU11.2 — Agregar checkbox "Recordarme"

**Archivo:** `app/modules/auth/routes.py`

**Cambios:**
```python
# ANTES
login_user(usuario, remember=True)

# DESPUÉS
remember = request.form.get('remember') == 'on'
login_user(usuario, remember=remember)
```

**Archivo:** `app/templates/auth/login.html`

**Cambios:** Agregar checkbox antes del botón de login:
```html
<div class="flex items-center justify-between mt-4">
    <label class="flex items-center gap-2 text-sm text-white/70">
        <input type="checkbox" name="remember" class="rounded">
        Recordarme
    </label>
</div>
```

---

## MÓDULO: PORTADA (BAJO — Prioridad 4)

### P12.1 — Filtrar relaciones de apoderado por tipo

**Archivo:** `app/modules/portada/routes.py`

**Cambios:**
```python
# ANTES
relaciones = PersonRelationship.query.filter_by(
    RelatedPersonId=current_user.PersonId
).all()

# DESPUÉS
relaciones = PersonRelationship.query.filter_by(
    RelatedPersonId=current_user.PersonId,
    RefPersonRelationshipId=31  # Relación estudiante-apoderado
).all()
```

---

# PARTE III — VERIFICACIÓN POST-IMPLEMENTACIÓN

## Checklist de verificación

Después de implementar todos los cambios, verificar:

### Funcionalidad

- [ ] Login/logout funciona correctamente
- [ ] Todos los módulos accesibles según permisos
- [ ] Forms POST funcionan con CSRF (no errores 400)
- [ ] AJAX funciona con CSRF token en headers
- [ ] Reset de contraseña solo funciona via POST
- [ ] Chat no ejecuta JavaScript inyectado (XSS corregido)
- [ ] PDFs y CSVs no accesibles sin login
- [ ] Admin no accesible sin autenticación
- [ ] RUT con dígito inválido rechazado en matrícula

### Seguridad

- [ ] `curl -X GET /reportes/curso/1` retorna 302 redirect a login
- [ ] `curl -X GET /admin/` retorna 302 redirect a login
- [ ] `curl -X POST /admin/toggle-module/1` retorna 302 redirect a login
- [ ] `curl -X GET /reportes/curso/1/informe_notas/1` retorna 302 redirect a login
- [ ] `curl -X POST /gestion-usuarios/1/resetear-password` sin CSRF retorna 400
- [ ] Forms POST sin `csrf_token` retornan 400
- [ ] Login sin `remember` no persiste sesión al cerrar navegador

### Rendimiento (opcional)

- [ ] N+1 queries mitigados con `joinedload` en módulos principales
- [ ] Paginación implementada en listados grandes

---

# PARTE IV — DEPENDENCIAS A INSTALAR

```txt
# requirements.txt — Agregar si no existen
flask-wtf>=1.2.0
```

**No se requieren otras dependencias nuevas.** Los módulos `imghdr` y `secrets` son parte de la stdlib de Python.

---

# PARTE V — ORDEN DE IMPLEMENTACIÓN RECOMENDADO

| Fase | Prioridad | Cambios | Tiempo estimado |
|------|-----------|---------|-----------------|
| **0** | CRÍTICO | G1 (CSRF), R2.1 (reportes @login_required), G3 (admin protegido), G4 (credenciales) | 1-2 días |
| **1** | ALTO | C3.1 (XSS chat), U7.1 (reset POST), M4.1 (AJAX permisos), C3.2 (chat acceso), E5.1 (eval permisos), L6.1 (libro permisos) | 3-5 días |
| **2** | MEDIO | G5 (utils permisos), G6 (utils orgs), CA9/CA9.2 (calendario imports), AU11 (auth next/remember), E5.3 (upload MIME), M4.2 (RUT validación) | 1 semana |
| **3** | BAJO | P12.1 (portada filtro), B10.1 (URL validación), R8 (validaciones roles), L6.3 (permisos cruzados), limpieza código duplicado | 1 semana |

**Total estimado: 2-3 semanas de desarrollo.**

---

# NOTAS PARA EL LLM QUE IMPLEMENTE ESTOS CAMBIOS

1. **Leer antes de modificar:** Siempre lee el archivo completo antes de hacer cambios. No asumas la estructura.

2. **Preservar lógica existente:** Los cambios de seguridad no deben alterar la lógica de negocio. Solo agregar capas de protección.

3. **Testing manual después de cada cambio:** Después de modificar cada módulo, verificar que las rutas existentes sigan funcionando.

4. **CSRF y AJAX:** El cambio más delicado es G1 (CSRF global). Flask-WTF bloqueará TODOS los POST sin token. Verificar que:
   - Todos los forms tengan `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
   - Todas las llamadas fetch POST tengan header `X-CSRFToken`.
   - El meta tag `csrf-token` exista en `base.html`.

5. **Importar antes de decorar:** Al agregar `@permiso_requerido`, asegúrate de importar desde `app.modules.auth.routes`.

6. **No romper imports circulares:** Si al importar `permiso_requerido` desde `auth/routes.py` causas un import circular, mover el decorador a `app/utils/auth.py` y actualizar todos los imports.

7. **El decorador `@permiso_requerido` ya incluye `@login_required`:** No es necesario poner ambos. Solo `@permiso_requerido('Módulo', nivel=1)` es suficiente.

8. **Verificar nombres de módulos en EdugestModule:** Los nombres deben coincidir exactamente con los usados en `@permiso_requerido`. Los nombres conocidos son: 'Libro Digital', 'Evaluaciones', 'Comunicaciones', 'Biblioteca', 'Matrícula', 'Calendario', 'Reportes'. Verificar contra la base de datos.

9. **Mantener compatibilidad con templates:** Los templates usan `user_permisos` (dict de niveles por módulo) inyectado por context processor. NO eliminar este context processor. Los cambios de permisos son solo en el backend.

10. **Encoding UTF-8:** Al guardar archivos, usar UTF-8 sin BOM para evitar caracteres corruptos.
```

---
