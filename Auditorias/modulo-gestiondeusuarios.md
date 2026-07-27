```markdown
# Auditoría del Módulo: Gestión de Usuarios

## 1. Resumen General

El módulo Gestión de Usuarios proporciona CRUD completo de usuarios del sistema con integración al modelo Mineduc (Person, PersonIdentifier, Organization). Incluye funcionalidad avanzada de asignación de profesor jefe a cursos y reseteo de contraseñas.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/gestion_usuarios/__init__.py` | Python | Importa `gestion_usuarios_bp` |
| `app/modules/gestion_usuarios/routes.py` | Python | Backend: CRUD de usuarios, API de cursos, gestión de profesor jefe |
| `app/templates/gestion_usuarios/listar.html` | Jinja2/HTML | Listado de usuarios en tabla |
| `app/templates/gestion_usuarios/formulario.html` | Jinja2/HTML | Formulario crear/editar usuario con Alpine.js |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Werkzeug (password hashing), Alpine.js, Jinja2.

**Prefijo de rutas:** `/gestion-usuarios`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `EdugestUser` | Auth | Usuarios del sistema |
| `EdugestRole` | Auth | Roles disponibles |
| `EdugestRolePermission` | Auth | Permisos (para contar módulos accesibles) |
| `Person` | Mineduc | Persona vinculada al usuario |
| `PersonIdentifier` | Mineduc | RUT de la persona (RefPersonIdentificationSystemId=51) |
| `PersonTelephone` | Mineduc | Teléfono de contacto |
| `PersonEmailAddress` | Mineduc | Email de contacto |
| `Organization` | Mineduc | Grados (TypeId=46) y cursos (TypeId=21) |
| `OrganizationRelationship` | Mineduc | Relación grado padre → curso hijo |
| `OrganizationPersonRole` | Mineduc | Asignación de profesor jefe (`EsProfesorJefe=True`) |

### 2.2 Relaciones clave

- Un `EdugestUser` se vincula a una `Person` via `PersonId`.
- El RUT se obtiene de `PersonIdentifier` con `RefPersonIdentificationSystemId=51`.
- Un profesor puede ser asignado como "Profesor Jefe" de un curso via `OrganizationPersonRole` con `EsProfesorJefe=True`.
- Los grados son `Organization` con `RefOrganizationTypeId=46`, los cursos con `RefOrganizationTypeId=21`.
- La relación grado→curso se modela via `OrganizationRelationship` (`ParentOrganizationId` → `OrganizationId`).

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/gestion-usuarios/` | GET | `listar` | `@login_required` + admin | Listar todos los usuarios |
| `/gestion-usuarios/nuevo` | GET, POST | `crear` | `@login_required` + admin | Crear usuario (2 modos) |
| `/gestion-usuarios/<user_id>/editar` | GET, POST | `editar` | `@login_required` + admin | Editar usuario |
| `/gestion-usuarios/<user_id>/resetear-password` | GET, POST | `resetear_password` | `@login_required` + admin | Resetear contraseña |
| `/gestion-usuarios/<user_id>/toggle-activo` | POST | `toggle_activo` | `@login_required` + admin | Activar/desactivar usuario |
| `/gestion-usuarios/api/cursos/<grado_id>` | GET | `api_cursos_por_grado` | `@login_required` + admin | API JSON para dropdown AJAX |

---

## 4. Funcionalidades de Negocio

### 4.1 Listar usuarios
- Consulta todos los `EdugestUser` ordenados por `CreatedAt` descendente.
- Para cada usuario obtiene: `Person`, `PersonIdentifier` (RUT), cantidad de permisos activos.
- Si el usuario tiene rol de profesor, busca asignación de profesor jefe activa.
- Muestra badge de profesor jefe con nombre del curso y grado.

### 4.2 Crear usuario (2 modos)

**Modo "existente"**: Seleccionar una `Person` existente que no tenga usuario. El username se asigna automáticamente como el RUT de la persona.

**Modo "nueva persona"**: Crear `Person` + `PersonIdentifier` (RUT) + `PersonEmailAddress` + `PersonTelephone` + `EdugestUser`. Username = RUT. Si el RUT ya existe como identificador pero la persona no tiene usuario, reutiliza la persona existente.

Ambos modos:
- Validan contraseña mínima de 4 caracteres.
- Permiten asignar rol.
- Si el rol es "Profesor", permite designar como profesor jefe de un curso específico.
- Usan `db.session.flush()` para obtener IDs antes de crear relaciones.

### 4.3 Editar usuario
- Modifica rol, estado activo y contraseña opcional.
- Gestión de profesor jefe: asigna o quita según checkbox.
- Al asignar nuevo curso como jefe, cierra la asignación anterior (marca `ExitDate`).

### 4.4 Resetear contraseña
- Genera contraseña aleatoria con `secrets.token_hex(4)` (8 caracteres hexadecimales).
- Acepta GET y POST.
- Muestra la contraseña temporal en un flash message.

### 4.5 Toggle activo/inactivo
- Invierte `IsActive` del usuario.

### 4.6 API cursos por grado
- Retorna JSON con los cursos de un grado seleccionado.
- Usado para dropdown dependiente via AJAX en el formulario.

---

## 5. Helpers

| Función | Descripción |
|---------|-------------|
| `_admin_required()` | Verifica `current_user.is_authenticated and current_user.RoleId == 1` |
| `_normalizar_rut(rut)` | Elimina puntos, espacios, convierte a mayúsculas |
| `_persona_ya_tiene_usuario(person_id)` | Verifica si `Person` ya tiene `EdugestUser` |
| `_obtener_roles_disponibles()` | Retorna todos los `EdugestRole` |
| `_es_profesor_rol(role_id)` | Verifica si `RoleName.lower() == 'profesor'` (definida 2 veces) |
| `_obtener_grados_con_cursos()` | Retorna grados con sus cursos hijos (definida 2 veces) |
| `_obtener_profesor_jefe(person_id)` | Retorna asignación activa de profesor jefe (definida 2 veces) |
| `_obtener_info_jefe(person_id)` | Retorna dict con curso, grado, IDs y asignación |
| `_crear_asignacion_profesor_jefe(person_id, curso_id, role_id)` | Cierra asignación anterior y crea nueva |
| `_quitar_asignacion_profesor_jefe(person_id)` | Cierra asignación activa (marca `ExitDate`) |

---

## 6. Análisis por Archivo

### 6.1 `__init__.py`

Una sola línea: import del blueprint. Patrón estándar.

### 6.2 `routes.py` — Backend

Archivo extenso (~280 líneas) con 6 rutas y 10 helpers. Incluye funciones duplicadas (`_es_profesor_rol`, `_obtener_grados_con_cursos`, `_obtener_profesor_jefe`) definidas al inicio y al final del archivo.

### 6.3 `listar.html` — Listado de Usuarios

Tabla con columnas: RUT (monospace), Nombre, Rol (badge gris), Profesor Jefe (badge amber con curso/grado), Permisos (count), Estado (badge verde/rojo), Acciones (editar + toggle).

### 6.4 `formulario.html` — Formulario Crear/Editar

Template complejo con Alpine.js para:
- Pestañas (Persona Existente / Registrar Funcionario Nuevo) en modo crear.
- Dropdown dependiente grado→curso via AJAX.
- Mostrar/ocultar sección de profesor jefe según el rol seleccionado.
- Pre-carga de datos en modo edición.

Campos en modo crear: persona (existente o nueva con nombres, apellidos, RUT, email, teléfono), contraseña, rol, asignación de profesor jefe (opcional), activo.

Campos en modo editar: persona (solo lectura), nueva contraseña (opcional), rol, asignación de profesor jefe, activo, resetear contraseña.

---

## 7. Hallazgos de Auditoría

### 7.1 Seguridad — CRÍTICO

#### [S1] Resetear contraseña accesible via GET
`resetear_password` acepta GET (`methods=['GET', 'POST']`). El botón en `formulario.html` es un simple `<a href="...">`. Un atacante podría forzar el reseteo de cualquier contraseña enviando este link al admin.
- **Archivo:** `routes.py` línea `@gestion_usuarios_bp.route('/<int:user_id>/resetear-password', methods=['GET', 'POST'])`
- **Riesgo:** CRITICO
- **Recomendación:** Solo permitir POST con token CSRF.

#### [S2] Contraseña temporal visible en flash message
La nueva contraseña generada se muestra via `flash()`: `flash(f'Contraseña de {usuario.Username} reseteada. Nueva contraseña temporal: {nueva_pass}', 'success')`. Cualquier persona que vea la pantalla puede verla.
- **Archivo:** `routes.py`, función `resetear_password`
- **Riesgo:** ALTO
- **Recomendación:** Enviar por canal seguro o forzar cambio en primer login.

### 7.2 Seguridad — ALTO

#### [S3] Sin protección CSRF
Ningún formulario POST incluye token CSRF. Afecta a: crear usuario, editar usuario, toggle activo.
- **Archivos:** `routes.py`, `formulario.html`, `listar.html`
- **Riesgo:** ALTO

#### [S4] Política de contraseña débil
Contraseña mínima de 4 caracteres (`len(nueva_password) < 4`). La contraseña temporal usa `secrets.token_hex(4)` = 8 caracteres hexadecimales.
- **Archivos:** `routes.py`
- **Riesgo:** MEDIO
- **Recomendación:** Mínimo 8 caracteres, incluir mayúsculas, números y símbolos.

#### [S5] Sin validación backend de pertenencia de curso a grado
En la asignación de profesor jefe, `curso_id` y `grado_id` se envían independientemente. No se verifica en backend que el curso realmente pertenezca al grado seleccionado.
- **Archivo:** `routes.py`, funciones `crear` y `editar`
- **Riesgo:** MEDIO
- **Recomendación:** Validar `OrganizationRelationship(ParentOrganizationId=grado_id, OrganizationId=curso_id)`.

### 7.3 Seguridad — MEDIO

#### [S6] Sin campo de confirmar contraseña
A diferencia de `admin/usuario_form.html`, este formulario no tiene campo de confirmación de contraseña al crear usuario.
- **Archivo:** `formulario.html`
- **Riesgo:** BAJO (UX)

#### [S7] Verificación de rol profesor por nombre
`_es_profesor_rol()` compara `RoleName.lower() == 'profesor'`. Si el nombre cambia (ej: "Profesor(a)"), la verificación falla y la sección de profesor jefe no se muestra.
- **Archivos:** `routes.py`, `formulario.html` (Alpine.js)
- **Riesgo:** MEDIO

#### [S8] Resetear contraseña sin forzar cambio
La contraseña temporal funciona como contraseña permanente. No hay mecanismo para forzar cambio en el próximo login.
- **Riesgo:** MEDIO

### 7.4 Código

#### [C1] Funciones duplicadas
`_es_profesor_rol()`, `_obtener_grados_con_cursos()` y `_obtener_profesor_jefe()` están definidas DOS veces en `routes.py` (al inicio y al final del archivo). Indica merge de código mal resuelto.
- **Riesgo:** BAJO (mantenibilidad, posible confusión)

### 7.5 Rendimiento

#### [P1] N+1 queries en listar
Para cada usuario se ejecutan múltiples queries: `Person`, `PersonIdentifier`, `EdugestRolePermission` (count), y si es profesor: `OrganizationPersonRole` + `Organization` + `OrganizationRelationship` + `Organization`.
- **Riesgo:** MEDIO
- **Recomendación:** Usar `joinedload` o queries agregadas.

#### [P2] Sin paginación
Todos los usuarios se cargan de una sola vez.
- **Riesgo:** BAJO-MEDIO (crece con el tiempo)

### 7.6 Frontend

#### [F1] Sin protección de permisos en templates
Ningún template usa `can()`. La protección depende exclusivamente del backend.

#### [F2] API cursos sin protección granular
`api_cursos_por_grado` solo verifica admin, no usa permisos RBAC.

#### [F3] Alpine.js como dependencia
El formulario depende completamente de Alpine.js para su funcionalidad. Sin JS, las pestañas, el dropdown dependiente y la sección de profesor jefe no funcionan.

---

## 8. Resumen de Hallazgos por Severidad

### Crítico (1)
- [S1] Resetear contraseña accesible via GET (CSRF)

### Alto (3)
- [S2] Contraseña temporal visible en flash message
- [S3] Sin protección CSRF
- [S5] Sin validación backend de pertenencia curso→grado

### Medio (4)
- [S4] Política de contraseña débil (min 4 caracteres)
- [S7] Verificación de rol profesor por nombre (frágil)
- [S8] Resetear contraseña sin forzar cambio
- [P1] N+1 queries en listar

### Bajo (4)
- [S6] Sin campo de confirmar contraseña
- [C1] Funciones duplicadas en routes.py
- [P2] Sin paginación
- [F1] Sin protección de permisos en templates

---

## 9. Endpoint Map Visual

```
GET  /gestion-usuarios/                          → listar()                (@login_required + admin)
GET  /gestion-usuarios/nuevo                     → crear()                 (@login_required + admin)
POST /gestion-usuarios/nuevo                     → crear()                 (@login_required + admin)
GET  /gestion-usuarios/<user_id>/editar          → editar()                (@login_required + admin)
POST /gestion-usuarios/<user_id>/editar          → editar()                (@login_required + admin)
GET  /gestion-usuarios/<user_id>/resetear-password → resetear_password()   (@login_required + admin)
POST /gestion-usuarios/<user_id>/resetear-password → resetear_password()   (@login_required + admin)
POST /gestion-usuarios/<user_id>/toggle-activo   → toggle_activo()         (@login_required + admin)
GET  /gestion-usuarios/api/cursos/<grado_id>     → api_cursos_por_grado()  (@login_required + admin)
```

---

## 10. Diagrama de Integración con Módulo Mineduc

```
┌──────────────────────────────────┐
│       GESTIÓN DE USUARIOS        │
├──────────────────────────────────┤
│  EdugestUser ──→ Person          │
│  Username = PersonIdentifier.RUT │
│                                  │
│  Si rol = "Profesor":            │
│    → OrganizationPersonRole      │
│      (EsProfesorJefe=True)       │
│      → Organization (Curso)      │
│        → OrganizationRelation    │
│          → Organization (Grado)  │
└──────────────────────────────────┘
```

---

*Auditoría generada a partir del análisis de los 4 archivos del módulo gestión_usuarios.*
```

---
