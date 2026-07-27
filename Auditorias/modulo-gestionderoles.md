```markdown
# Auditoría del Módulo: Gestión de Roles

## 1. Resumen General

El módulo Gestión de Roles proporciona CRUD de roles y gestión de permisos por módulo utilizando el sistema antiguo de niveles (0/1/2). Opera como complemento al módulo Admin, cubriendo las funcionalidades de roles y permisos que no están en `admin/routes.py`.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/gestion_roles/__init__.py` | Python | Importa `gestion_roles_bp` |
| `app/modules/gestion_roles/routes.py` | Python | Backend: CRUD de roles y gestión de permisos |
| `app/templates/gestion_roles/listar.html` | Jinja2/HTML | Listado de roles en formato cards |
| `app/templates/gestion_roles/nuevo_rol.html` | Jinja2/HTML | Formulario crear rol |
| `app/templates/gestion_roles/editar_permisos.html` | Jinja2/HTML | Formulario editar permisos por módulo |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2.

**Prefijo de rutas:** `/gestion-roles`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Uso |
|--------|-----|
| `EdugestRole` | Catálogo de roles (RoleId, RoleName) |
| `EdugestRolePermission` | Permisos por rol y módulo (RoleId, ModuleId, PermissionLevel) |
| `EdugestModule` | Módulos del sistema |
| `EdugestUser` | Usuarios del sistema (para contar usuarios por rol) |

### 2.2 Niveles de permiso

| Nivel | Significado | Color |
|-------|-------------|-------|
| 0 | Sin acceso | Rojo |
| 1 | Solo lectura | Ámbar |
| 2 | Lectura y escritura | Verde |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/gestion-roles/` | GET | `listar` | `@login_required` + admin check | Listar roles con estadísticas |
| `/gestion-roles/<role_id>/permisos` | GET, POST | `editar_permisos` | `@login_required` + admin check | Ver/editar permisos de un rol |
| `/gestion-roles/nuevo` | GET, POST | `crear_rol` | `@login_required` + admin check | Crear nuevo rol |

---

## 4. Análisis por Archivo

### 4.1 `__init__.py`

Una sola línea: import del blueprint. Patrón estándar.

### 4.2 `routes.py` — Backend

#### Funcionalidades principales

- **Listar roles**: Consulta todos los `EdugestRole` y calcula estadísticas (total usuarios, permisos activos, total módulos). Detecta roles huérfanos (existentes en `EdugestUser.RoleId` pero no en `EdugestRole`).
- **Editar permisos (GET)**: Muestra todos los módulos con su nivel de permiso actual (0/1/2).
- **Editar permisos (POST)**: Elimina TODOS los permisos existentes del rol y los recrea desde cero (delete-all + re-insert).
- **Crear rol**: Requiere ID numérico manual + nombre. Verifica que el ID no exista. Crea permisos vacíos (nivel 0) para todos los módulos. Redirige a editar permisos.

#### Helpers

| Función | Descripción |
|---------|-------------|
| `_admin_required()` | Verifica `current_user.is_authenticated and current_user.RoleId == 1` |
| `_obtener_nombre_rol(role_id)` | Obtiene nombre del rol, fallback a "Rol {id}" |

### 4.3 `listar.html` — Listado de Roles

- Grid de cards (1-2-3 columnas responsivas).
- Cada card: nombre, ID, badge de tipo, estadísticas (usuarios, módulos con acceso), barra de progreso, botón "Configurar Permisos".
- Leyenda de niveles (0=rojo, 1=ámbar, 2=verde).
- Badges hardcodeados por RoleId: 1=Admin, 3=Profesor, 6=Apoderado, otro=Personalizado.
- Botón "+ Nuevo Rol".

### 4.4 `nuevo_rol.html` — Formulario Crear Rol

- Campos: ID numérico (`role_id`, type number, min=1) + nombre (`nombre`, type text).
- Texto informativo sobre IDs ya en uso (1, 3, 6).
- Sin validación de rango máximo para ID.

### 4.5 `editar_permisos.html` — Formulario Permisos

- Lista de módulos con select (0/1/2) por cada uno.
- Iconos emoji por tipo de módulo.
- Cambio dinámico de color del select via JavaScript (`actualizarColor()`).
- Muestra si el módulo está activo o deshabilitado.
- Campos nombrados como `permiso_{ModuleId}`.

---

## 5. Hallazgos de Auditoría

### 5.1 Seguridad — ALTO

#### [S1] Sistema de permisos paralelo
Este módulo gestiona `EdugestRolePermission` (niveles 0/1/2 por módulo), mientras que `admin/permisos.html` gestiona `EdugestFeaturePermission` (CanView/CanEdit/CanDelete por feature). Dos sistemas operando simultáneamente con distintas tablas.
- **Riesgo:** ALTO
- **Recomendación:** Unificar en un solo sistema de permisos.

#### [S2] Delete-all + re-insert en permisos
`editar_permisos` elimina TODOS los permisos del rol y los recrea. Si el proceso falla a mitad de camino, el rol queda sin permisos.
- **Riesgo:** MEDIO
- **Recomendación:** Usar transacción explícita o UPSERT.

### 5.2 Seguridad — MEDIO

#### [S3] Sin protección CSRF
Ningún formulario POST incluye token CSRF.
- **Riesgo:** MEDIO

#### [S4] RoleId proporcionado por el usuario
En `crear_rol`, el `role_id` viene del formulario. No hay validación de rango máximo.
- **Riesgo:** MEDIO

### 5.3 Rendimiento

#### [P1] `total_modulos` consultado por cada rol en el loop
`EdugestModule.query.count()` se ejecuta una vez por rol en el loop de listado.
- **Riesgo:** BAJO
- **Recomendación:** Calcular una sola vez antes del loop.

### 5.4 Arquitectura

#### [A1] Sin eliminación de roles
No hay ruta para eliminar roles desde este módulo.

#### [A2] Roles huérfanos sin acción correctiva
Se detectan roles huérfanos pero no se ofrece forma de resolverlos.

#### [A3] Sin validación backend de nivel de permiso
No se verifica que el nivel enviado sea 0, 1 o 2. Un valor fuera de rango se guardaría igual.

#### [A4] Badges hardcodeados por RoleId en template
Mismo patrón inconsistente observado en otros módulos. RoleId=6 mostrado como "Apoderado".

### 5.5 Frontend

#### [F1] Sin protección de permisos en templates
Ningún template usa `can()` u otra verificación. La protección depende exclusivamente del backend.

#### [F2] Sin paginación
Todos los roles se muestran sin paginación.

---

## 6. Resumen de Hallazgos por Severidad

### Alto (1)
- [S1] Sistema de permisos paralelo (conflicto con admin/permissions.py)

### Medio (3)
- [S2] Delete-all + re-insert en permisos
- [S3] Sin protección CSRF
- [S4] RoleId sin validación de rango máximo

### Bajo (5)
- [P1] `total_modulos` consultado en cada iteración
- [A1] Sin eliminación de roles
- [A2] Roles huérfanos sin acción correctiva
- [A3] Sin validación backend de nivel de permiso
- [F1] Sin protección de permisos en templates

---

## 7. Endpoint Map Visual

```
GET  /gestion-roles/                    → listar()            (@login_required + admin)
GET  /gestion-roles/<role_id>/permisos  → editar_permisos()   (@login_required + admin)
POST /gestion-roles/<role_id>/permisos  → editar_permisos()   (@login_required + admin)
GET  /gestion-roles/nuevo               → crear_rol()         (@login_required + admin)
POST /gestion-roles/nuevo               → crear_rol()         (@login_required + admin)
```

---

*Auditoría generada a partir del análisis de los 5 archivos del módulo gestión_roles.*
```

---
