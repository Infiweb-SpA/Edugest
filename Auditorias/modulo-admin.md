```markdown
# Auditoría del Módulo: Admin (Administración)

## 1. Resumen General

El módulo Admin proporciona el panel de administración central del sistema Edugest. Incluye la gestión de módulos (habilitar/deshabilitar), la matriz de permisos RBAC, y la gestión CRUD de roles y usuarios. Opera en paralelo con el sistema de autenticación de `auth` y el sistema de permisos granular definido en `permissions.py`.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/admin/permissions.py` | Python | Sistema RBAC completo: catálogo de features, verificación de permisos, inicialización |
| `app/modules/admin/routes.py` | Python | Backend: dashboard y toggle de módulos (2 rutas) |
| `app/templates/admin/dashboard.html` | Jinja2/HTML | Panel de administración con matriz de módulos |
| `app/templates/admin/login.html` | Jinja2/HTML | Login alternativo (light theme) |
| `app/templates/admin/permisos.html` | Jinja2/HTML | Matriz de permisos granular por rol y feature |
| `app/templates/admin/roles.html` | Jinja2/HTML | CRUD de roles del sistema |
| `app/templates/admin/rol_form.html` | Jinja2/HTML | Formulario crear/editar rol |
| `app/templates/admin/usuarios.html` | Jinja2/HTML | CRUD de usuarios del sistema |
| `app/templates/admin/usuario_form.html` | Jinja2/HTML | Formulario crear/editar usuario |

**Tecnologías:** Flask, SQLAlchemy ORM, Jinja2.

**Prefijo de rutas:** `/admin`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Uso |
|--------|-----|
| `EdugestModule` | Módulos habilitados/deshabilitados del sistema |
| `EdugestSystemRole` | Roles del sistema (Administrador, Soporte, UTP, Profesor, Apoderado, Estudiante) |
| `EdugestSystemUser` | Usuarios del sistema (diferente de `EdugestUser` usado en `auth`) |
| `EdugestFeaturePermission` | Permisos granulares por rol y feature (CanView, CanEdit, CanDelete) |
| `Person` | Persona vinculada al usuario |

### 2.2 Catálogo de Features (47 funcionalidades)

| Módulo | Cantidad | Códigos |
|--------|----------|---------|
| Admin | 5 | `admin_dashboard`, `admin_roles_crud`, `admin_users_crud`, `admin_modules_toggle`, `admin_permissions_matrix` |
| Gestion Usuarios | 1 | `gest_usuarios_profesor_jefe` |
| Libro Digital | 11 | `libro_grados_list`, `libro_grados_estado_column`, `libro_asignaturas_list`, `libro_asignatura_agregar_manual`, `libro_planificar`, `libro_abrir_libro`, `libro_unidades_ver`, `libro_nueva_evaluacion`, `libro_registrar_clase`, `libro_subir_material`, `libro_preguntas_resultados` |
| Evaluaciones | 9 | `eval_grados_ver`, `eval_asignaturas_ver`, `eval_unidades_ver`, `eval_nueva_evaluacion`, `eval_nueva_pregunta`, `eval_simulacion_rapida`, `eval_nota_manual`, `eval_guardar_notas_manuales`, `eval_publicar` |
| Comunicaciones | 4 | `com_anuncios_ver`, `com_publicar_anuncio`, `com_contactos_ver`, `com_comunicacion_apoderados` |
| Biblioteca CRA | 7 | `bib_dashboard`, `bib_nuevo_prestamo`, `bib_agregar_libro`, `bib_catalogo_editar`, `bib_catalogo_eliminar`, `bib_prestamos_ver`, `bib_tip_block` |
| Matrícula | 4 | `mat_listar_estudiantes`, `mat_nuevo_estudiante`, `mat_columna_acciones`, `mat_ver_detalle` |
| Reportes | 5 | `rep_index`, `rep_todo_el_grado`, `rep_asignaturas_calificaciones`, `rep_configurar_sumativas`, `rep_checkbox_sumativas` |

### 2.3 Roles definidos (6)

| Rol | Descripción | Acceso |
|-----|-------------|--------|
| Administrador | Control total | Todos los features (view+edit+delete) |
| Soporte | Soporte técnico | Todo excepto funciones pedagógicas puras |
| UTP | Unidad Técnico Pedagógica | Todo lo pedagógico, nada de admin |
| Profesor | Docente | Lo pedagógico de sus cursos, lectura en reportes |
| Apoderado | Padre/madre/tutor | Solo lectura: anuncios, contactos, biblioteca, detalle matrícula, reportes |
| Estudiante | Alumno | Solo lectura: evaluaciones, anuncios, biblioteca, reportes |

### 2.4 Tipos de permiso por feature

Cada feature tiene 3 permisos booleanos: `CanView`, `CanEdit`, `CanDelete`.

---

## 3. Mapa de Rutas (definidas en routes.py)

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/admin/` | GET | `dashboard` | **NINGUNA** | Panel de administración |
| `/admin/toggle-module/<module_id>` | POST | `toggle_module` | **NINGUNA** | Habilitar/deshabilitar módulo |

### Rutas referenciadas en templates (no definidas en routes.py analizado)

| Endpoint | Usado en | Estado |
|----------|----------|--------|
| `admin.login` | `admin/login.html` | No existe en routes.py |
| `admin.init_rbac` | `permisos.html` | No existe en routes.py |
| `admin.guardar_permisos` | `permisos.html` | No existe en routes.py |
| `admin.nuevo_rol` | `roles.html` | No existe en routes.py |
| `admin.editar_rol(role_id)` | `roles.html` | No existe en routes.py |
| `admin.eliminar_rol(role_id)` | `roles.html` | No existe en routes.py |
| `admin.listar_roles` | `rol_form.html` | No existe en routes.py |
| `admin.nuevo_usuario` | `usuarios.html` | No existe en routes.py |
| `admin.editar_usuario(user_id)` | `usuarios.html` | No existe en routes.py |
| `admin.toggle_usuario(user_id)` | `usuarios.html` | No existe en routes.py |
| `admin.eliminar_usuario(user_id)` | `usuarios.html` | No existe en routes.py |
| `admin.listar_usuarios` | `usuario_form.html` | No existe en routes.py |

**Nota:** Estas rutas probablemente están definidas en los módulos `gestion_roles/routes.py` y `gestion_usuarios/routes.py` de la estructura de carpetas, y se registran bajo el mismo blueprint `admin_bp`.

---

## 4. Sistema RBAC (permissions.py)

### 4.1 Helpers

| Función | Descripción |
|---------|-------------|
| `get_current_user()` | Obtiene usuario desde `session['user_id']` |
| `get_current_user_role()` | Obtiene el rol del usuario actual |
| `get_current_role_id()` | Obtiene el RoleId del usuario actual |
| `check_permission(feature_code, permission_type)` | Verifica permiso, retorna bool. Admin (RoleId=1) tiene bypass total |
| `@require_permission(feature_code, permission_type, redirect_url)` | Decorador que protege rutas |
| `@require_module_enabled(module_name)` | Decorador que verifica si módulo está habilitado |
| `init_rbac_system()` | Inicializa roles, permisos y usuario admin por defecto |

### 4.2 Context Processor

La función `can(feature, permission_type)` está disponible en templates Jinja2 para verificar permisos granulares. Se usa en `roles.html`, `usuarios.html` y `permisos.html`.

### 4.3 Inicialización por defecto

- `init_default_roles()`: Crea 6 roles si no existen.
- `init_default_permissions()`: Inicializa matriz completa de 47 features × 6 roles. Solo inserta, nunca actualiza existentes.
- `init_default_admin_user()`: Crea usuario `admin` / `admin123` si no hay usuarios.

---

## 5. Análisis por Archivo

### 5.1 `permissions.py`

Sistema RBAC completo con catálogo de 47 features, matriz de permisos para 6 roles, y funciones de inicialización. Opera con `session['user_id']` y `EdugestSystemUser` (sistema paralelo a Flask-Login).

### 5.2 `routes.py`

Solo 2 rutas (dashboard y toggle de módulos), ambas completamente sin protección de acceso.

### 5.3 `dashboard.html`

Panel de módulos con botones de toggle (activar/desactivar). Forms POST sin CSRF, sin confirmación.

### 5.4 `login.html`

Login alternativo que hereda de `base_public.html`. Expone credenciales por defecto (`admin`/`admin123`) en el template. Referencia endpoint `admin.login` que no existe en routes.py.

### 5.5 `permisos.html`

Matriz de permisos interactiva agrupada por módulo. Checkboxes para view/edit/delete. Usada con `can()`. Endpoints `init_rbac` y `guardar_permisos` no existen en routes.py.

### 5.6 `roles.html`

Listado de roles con CRUD parcial. Usa `can()` para proteger acciones. Roles protegidos contra eliminación (Administrador, Soporte, Profesor, Apoderado, Estudiante).

### 5.7 `rol_form.html`

Formulario crear/editar rol. Nombre readonly solo para "Administrador". Sin CSRF, sin protección de acceso.

### 5.8 `usuarios.html`

CRUD completo de usuarios con permisos granulares via `can()`. Muestra último acceso. Toggle sin verificación de permisos.

### 5.9 `usuario_form.html`

Formulario crear/editar usuario. Confirmación de contraseña solo en creación. Sin validación de fortaleza de contraseña. Sin vinculación a Person.

---

## 6. Hallazgos de Auditoría

### 6.1 Seguridad — CRÍTICO

#### [S1] Rutas sin ninguna protección de acceso
Las rutas de `admin/routes.py` (`dashboard` y `toggle_module`) son completamente públicas. No usan `@login_required`, `@permiso_requerido`, `@require_permission`, ni verificación manual. Cualquier usuario no autenticado puede ver el panel de administración y habilitar/deshabilitar módulos.
- **Archivo:** `routes.py`
- **Riesgo:** CRITICO
- **Recomendación:** Agregar `@login_required` + verificación de rol admin.

#### [S2] Credenciales admin por defecto expuestas en template
`admin/login.html` muestra "Usuario por defecto: admin / admin123" directamente en la página. Combinado con rutas sin protección, cualquier persona puede acceder al panel de administración.
- **Archivo:** `admin/login.html`
- **Riesgo:** CRITICO
- **Recomendación:** Eliminar texto del template. Forzar cambio de contraseña en primer login.

#### [S3] Credenciales hardcodeadas en inicialización
`init_default_admin_user()` crea usuario con Username=`admin` y Password=`admin123`. Credenciales predecibles que se ejecutan automáticamente.
- **Archivo:** `permissions.py`
- **Riesgo:** ALTO
- **Recomendación:** Generar contraseña aleatoria o requerir configuración manual.

### 6.2 Seguridad — ALTO

#### [S4] Sistema de autenticación duplicado y conflictivo
`permissions.py` usa `session['user_id']` con `EdugestSystemUser`, mientras que `auth/routes.py` usa Flask-Login con `EdugestUser`. Dos sistemas paralelos que pueden causar:
- Autenticación válida en un sistema pero no en el otro.
- Permisos concedidos sin autenticación correcta.
- Dos tablas de usuarios distintas operando simultáneamente.
- **Archivos:** `permissions.py`, `auth/routes.py`
- **Riesgo:** ALTO
- **Recomendación:** Unificar en un solo sistema de autenticación.

#### [S5] Dos sistemas de permisos paralelos
- `auth/routes.py` usa `EdugestRolePermission` + `EdugestModule` (permisos por módulo con nivel 0/1/2).
- `permissions.py` usa `EdugestFeaturePermission` + `FEATURE_CATALOG` (permisos por feature con CanView/CanEdit/CanDelete).

Ambos sistemas operan simultáneamente con distintas tablas y modelos de permisos.
- **Riesgo:** ALTO
- **Recomendación:** Unificar en un solo sistema de permisos.

#### [S6] Múltiples endpoints no implementados
12 endpoints referenciados en templates no existen en `admin/routes.py`. Esto significa que la funcionalidad CRUD de roles, permisos y usuarios puede estar rota o parcialmente implementada en otro archivo.
- **Archivos:** Todos los templates de admin
- **Riesgo:** ALTO (funcionalidad rota)
- **Recomendación:** Verificar si existen en `gestion_roles/routes.py` y `gestion_usuarios/routes.py`, y registrarlos en el blueprint correcto.

### 6.3 Seguridad — MEDIO

#### [S7] Sin protección CSRF global
Ningún formulario POST del módulo incluye token CSRF. Esto afecta a: toggle de módulos, guardar permisos, crear/editar rol, crear/editar usuario, toggle usuario, eliminar usuario, restaurar defaults.
- **Archivos:** Todos los templates con forms POST
- **Riesgo:** MEDIO
- **Recomendación:** Implementar protección CSRF global con `Flask-WTF`.

#### [S8] Toggle de usuario sin verificación de permisos
En `admin/usuarios.html`, el botón "Desactivar/Activar" no tiene condición `{% if can(...) %}`, inconsistente con "Editar" y "Eliminar" que sí la tienen.
- **Archivo:** `admin/usuarios.html`
- **Riesgo:** MEDIO
- **Recomendación:** Agregar `{% if can('admin_users_crud', 'edit') %}` al botón toggle.

### 6.4 Rendimiento

#### [P1] `EdugestModule.query.all()` sin paginación
Dashboard carga todos los módulos de una sola vez.
- **Riesgo:** BAJO (pocos módulos esperados)

### 6.5 Arquitectura y Mantenibilidad

#### [A1] `init_default_permissions()` solo inserta, nunca actualiza
Si se modifica la matriz de permisos, los cambios no se aplican a permisos existentes.
- **Recomendación:** Agregar lógica de actualización o flag de `force_reset`.

#### [A2] Login duplicado
`admin/login.html` y `auth/login.html` son dos páginas de login distintas con diferentes diseños y bases template.
- **Recomendación:** Unificar en una sola página de login.

#### [A3] Inconsistencia en semántica de RoleId=6
- `auth/routes.py`: redirect a `portada.bienvenida` (tratado como apoderado/estudiante).
- `admin/usuarios.html` (auth): muestra como "Apoderado".
- Módulo matrícula: RoleId=6 es rol de estudiante en `OrganizationPersonRole`.
- `admin/usuarios.html` (admin): no muestra RoleId=6 directamente, usa `RoleName`.
- **Recomendación:** Documentar y unificar la semántica de roles.

#### [A4] Verificación de admin inconsistente
Algunas rutas usan `can()`, otras usan verificación manual `RoleId != 1`, otras no tienen verificación alguna.
- **Recomendación:** Estandarizar con decoradores de permisos.

#### [A5] Select de roles sin filtro de activos
`usuario_form.html` muestra todos los roles sin filtrar por `IsActive`.
- **Recomendación:** Filtrar roles activos en el backend.

#### [A6] Sin campo de Person en usuario_form
No hay forma de vincular una `Person` al usuario desde el formulario. El `PersonId` debe asignarse manualmente o por otro mecanismo no visible.

### 6.6 Frontend

#### [F1] Encoding corrupto
Caracteres corruptos (`贸`, `铆`, `煤`, `贸`, `谩`) confirman problema sistémico de encoding UTF-8.

#### [F2] Sin validación de fortaleza de contraseña
`usuario_form.html` no tiene `minlength`, patrón, ni indicación de requisitos para la contraseña.

#### [F3] Confirmar contraseña sin validación JS
El campo `confirm_password` en creación de usuario no tiene validación JavaScript de coincidencia antes del envío.

#### [F4] Sin toggle de visibilidad de contraseña
`admin/login.html` y `usuario_form.html` no tienen botón para mostrar/ocultar contraseña (a diferencia de `auth/login.html`).

#### [F5] Roles protegidos contra eliminación solo en template
La protección contra eliminación de roles fundamentales (Administrador, Soporte, Profesor, Apoderado, Estudiante) se hace con `{% if %}` en el template. Si el backend no valida esto también, un request directo podría eliminarlos.

---

## 7. Resumen de Hallazgos por Severidad

### Crítico (2)
- [S1] Rutas sin ninguna protección de acceso
- [S2] Credenciales admin por defecto expuestas en template

### Alto (4)
- [S3] Credenciales hardcodeadas en inicialización
- [S4] Sistema de autenticación duplicado y conflictivo
- [S5] Dos sistemas de permisos paralelos
- [S6] Múltiples endpoints no implementados (12 endpoints)

### Medio (2)
- [S7] Sin protección CSRF global
- [S8] Toggle de usuario sin verificación de permisos

### Bajo (10)
- [P1] Sin paginación en módulos
- [A1] Permisos por defecto solo insertan, no actualizan
- [A2] Login duplicado
- [A3] Inconsistencia en semántica de RoleId=6
- [A4] Verificación de admin inconsistente
- [A5] Select de roles sin filtro de activos
- [A6] Sin campo de Person en formulario de usuario
- [F2] Sin validación de fortaleza de contraseña
- [F4] Sin toggle de visibilidad de contraseña
- [F5] Protección de eliminación de roles solo en template

---

## 8. Endpoint Map Visual

### Definidos en routes.py
```
GET  /admin/                           → dashboard()         (SIN PROTECCIÓN)
POST /admin/toggle-module/<module_id>  → toggle_module()      (SIN PROTECCIÓN)
```

### Referenciados en templates (no en routes.py)
```
POST /admin/login                      → admin.login          (NO EXISTE)
POST /admin/init-rbac                  → admin.init_rbac      (NO EXISTE)
POST /admin/guardar-permisos           → admin.guardar_permisos (NO EXISTE)
GET  /admin/nuevo-rol                  → admin.nuevo_rol      (NO EXISTE)
GET  /admin/editar-rol/<role_id>       → admin.editar_rol     (NO EXISTE)
POST /admin/eliminar-rol/<role_id>     → admin.eliminar_rol   (NO EXISTE)
GET  /admin/listar-roles               → admin.listar_roles   (NO EXISTE)
GET  /admin/nuevo-usuario              → admin.nuevo_usuario  (NO EXISTE)
GET  /admin/editar-usuario/<user_id>   → admin.editar_usuario (NO EXISTE)
POST /admin/toggle-usuario/<user_id>   → admin.toggle_usuario (NO EXISTE)
POST /admin/eliminar-usuario/<user_id> → admin.eliminar_usuario (NO EXISTE)
GET  /admin/listar-usuarios            → admin.listar_usuarios (NO EXISTE)
```

---

## 9. Diagrama de Relación entre Sistemas

```
┌─────────────────────────────────────────────────────┐
│                    FLASK APP                         │
├──────────────────┬──────────────────────────────────┤
│  auth/routes.py  │  admin/permissions.py            │
│                  │                                  │
│  Flask-Login     │  session['user_id']              │
│  EdugestUser     │  EdugestSystemUser               │
│  EdugestRolePerm │  EdugestFeaturePermission        │
│  EdugestModule   │  FEATURE_CATALOG                 │
│                  │                                  │
│  permiso_requerido│  @require_permission            │
│  verificar_escrit│  check_permission                │
│  (nivel 0/1/2)   │  (CanView/Edit/Delete)           │
├──────────────────┴──────────────────────────────────┤
│              admin/routes.py                         │
│  (Solo dashboard + toggle, SIN protección)           │
└─────────────────────────────────────────────────────┘
```

---

*Auditoría generada a partir del análisis de los 9 archivos del módulo admin.*
```

---