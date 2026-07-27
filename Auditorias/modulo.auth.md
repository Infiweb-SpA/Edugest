Tienes toda la razon, se me paso. Aqui va el documento de auditoria del modulo auth:

```markdown
# Auditoría del Módulo: Auth (Autenticación)

## 1. Resumen General

El módulo Auth es el sistema de autenticación y control de acceso base de Edugest. Proporciona login/logout, gestión de sesiones mediante Flask-Login, un decorador de permisos por módulo, y una vista de administración de usuarios (solo lectura).

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/auth/__init__.py` | Python | Importa `auth_bp` desde routes |
| `app/modules/auth/routes.py` | Python | Backend: autenticación, permisos, gestión de usuarios |
| `app/templates/auth/login.html` | HTML standalone | Página de inicio de sesión |
| `app/templates/auth/unauthorized.html` | Jinja2/HTML | Página de error 403 (Acceso Denegado) |
| `app/templates/auth/usuarios.html` | Jinja2/HTML | Listado de usuarios (solo admin) |

**Tecnologías:** Flask, Flask-Login, Werkzeug (password hashing), Jinja2.

**Prefijo de rutas:** `/auth`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Uso |
|--------|-----|
| `EdugestUser` | Usuarios del sistema (Username, PasswordHash, RoleId, IsActive, PersonId) |
| `EdugestModule` | Módulos habilitados/deshabilitados del sistema |
| `EdugestRolePermission` | Permisos por rol y módulo (PermissionLevel: 0/1/2) |
| `Person` | Persona vinculada al usuario (nombre, apellido) |

### 2.2 Constantes de Roles

| RoleId | Rol inferido | Redirect post-login |
|--------|-------------|---------------------|
| 1 | Administrador | `admin.dashboard` |
| 3 | Profesor | `libro_digital.listar_grados` |
| 6 | Apoderado/Estudiante | `portada.bienvenida` |
| Otros | Sin rol específico | `portada.bienvenida` |

### 2.3 Niveles de permiso

| Nivel | Significado |
|-------|-------------|
| 0 | Sin acceso |
| 1 | Solo lectura |
| 2 | Lectura y escritura |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/auth/login` | GET, POST | `login` | Ninguna (público) | Página y lógica de login |
| `/auth/logout` | GET | `logout` | `@login_required` | Cerrar sesión |
| `/auth/usuarios` | GET | `listar_usuarios` | `@login_required` + verificación manual `RoleId==1` | Listar todos los usuarios |

---

## 4. Sistema de Permisos

### 4.1 Decorador `permiso_requerido(module_name, nivel=1)`

- Verifica autenticación del usuario.
- **RoleId=1 (Admin) tiene bypass total** sin consultar base de datos.
- Busca módulo por `ModuleName` en `EdugestModule`.
- Busca permiso por `RoleId` + `ModuleId` en `EdugestRolePermission`.
- Si no existe permiso o `PermissionLevel < nivel`, retorna 403 con template `unauthorized.html`.

### 4.2 Helper `verificar_escritura(module_name)`

- Función para uso dentro de rutas mixtas GET/POST cuando solo POST requiere nivel 2.
- Admin (RoleId=1) tiene bypass.
- Lanza `abort(403)` si no tiene permiso.

### 4.3 Configuración de Flask-Login

- `login_view`: `auth.login`
- `login_message`: "Debes iniciar sesión para acceder."
- `login_message_category`: `warning`
- `remember=True` hardcodeado en `login_user()`.

---

## 5. Análisis por Archivo

### 5.1 `__init__.py`

Una sola línea: `from app.modules.auth.routes import auth_bp`. Solo importa el blueprint.

### 5.2 `routes.py` — Backend

#### Funcionalidades principales

- **Login**: Autenticación por Username (RUT) + password con `check_password_hash`. Respeta parámetro `next` para redirección. Redirige según rol.
- **Logout**: `logout_user()` y redirect a login.
- **Listar usuarios**: Solo admin. Carga todos los `EdugestUser` con su `Person` asociada (N+1 queries).
- **User loader**: Carga usuario por `EdugestUser.query.get(int(user_id))`.

#### Helpers

| Función | Descripción |
|---------|-------------|
| `init_login_manager(app)` | Inicializa Flask-Login en la aplicación |
| `load_user(user_id)` | User loader para Flask-Login |
| `permiso_requerido(module_name, nivel)` | Decorador de protección por módulo |
| `verificar_escritura(module_name)` | Helper para verificar permiso nivel 2 |

### 5.3 `login.html` — Página de Login

- **Standalone**: No hereda de `base.html`.
- **CDN externo**: Tailwind CSS (`cdn.tailwindcss.com`), Google Fonts (`DM Sans`).
- **Diseño**: Dark theme con glassmorphism, gradientes indigo/violeta.
- **Campos**: `username` (RUT) + `password` con toggle de visibilidad (JS).
- **Flash messages**: Categorías `error` (rojo), `warning` (ámbar), otro (verde).
- **Footer**: "Edugest SpA © 2026 · Región de La Araucanía".
- **Animaciones**: `fadeUp` con 3 niveles de delay.

### 5.4 `unauthorized.html` — Página 403

- Hereda de `base.html`.
- Icono de candado rojo, título "Acceso No Autorizado".
- Mensaje dinámico via `{{ mensaje }}` con fallback estático.
- Botón "Volver al Panel" → `admin.dashboard`.

### 5.5 `usuarios.html` — Listado de Usuarios

- Hereda de `base.html`.
- Tabla con columnas: RUT (Username), Nombre (FirstName + LastName), Rol (badge por RoleId), Estado (Activo/Inactivo).
- Mapeo de roles: 1=Administrador (púrpura), 3=Profesor (azul), 6=Apoderado (verde), otro=grís.
- Solo lectura, sin CRUD.

---

## 6. Hallazgos de Auditoría

### 6.1 Seguridad — CRÍTICO

#### [S1] Sin protección CSRF
El formulario de login POST no incluye token CSRF. Tampoco se evidencia configuración global de CSRF en el módulo.
- **Archivo:** `routes.py` + `login.html`
- **Riesgo:** Alto
- **Recomendación:** Implementar `Flask-WTF` o middleware CSRF.

#### [S2] `remember=True` hardcodeado
`login_user(usuario, remember=True)` siempre recuerda la sesión. En entornos compartidos o públicos, la sesión persiste indefinidamente.
- **Archivo:** `routes.py`, función `login`
- **Riesgo:** Medio
- **Recomendación:** Agregar checkbox "Recordarme" y usar `remember=False` por defecto.

#### [S3] Open Redirect via parámetro `next`
La redirección post-login usa `request.args.get('next')` sin validar que sea una URL interna. Un atacante podría redirigir a sitio externo tras login.
- **Archivo:** `routes.py`, función `login`
- **Riesgo:** Medio
- **Recomendación:** Validar que `next` sea URL relativa o del mismo dominio.

#### [S4] Sin rate limiting en login
No hay limitación de intentos. Permite fuerza bruta contra `/auth/login`.
- **Archivo:** `routes.py`
- **Riesgo:** Medio
- **Recomendación:** Implementar `Flask-Limiter` o bloqueo temporal tras N intentos fallidos.

### 6.2 Seguridad — MEDIO

#### [S5] Admin bypass total de permisos
`RoleId=1` salta toda verificación en `permiso_requerido()` y `verificar_escritura()`. Si la cuenta admin es comprometida, el atacante tiene acceso total sin restricciones.
- **Archivo:** `routes.py`
- **Riesgo:** Bajo (diseño intencional)

#### [S6] Sin gestión de contraseñas
No hay rutas para cambio de contraseña, recuperación, reseteo, ni expiración.
- **Archivo:** `routes.py`
- **Riesgo:** Medio
- **Recomendación:** Implementar cambio de contraseña y recuperación por email.

### 6.3 Rendimiento

#### [P1] N+1 queries en listar_usuarios
`EdugestUser.query.all()` seguido de un query individual por cada usuario para obtener `Person`.
- **Archivo:** `routes.py`, función `listar_usuarios`
- **Riesgo:** Bajo-Medio
- **Recomendación:** Usar `joinedload` o `subqueryload` de SQLAlchemy.

#### [P2] Imports locales repetidos
Los imports de `EdugestUser`, `EdugestModule`, `EdugestRolePermission` se hacen dentro de múltiples funciones para evitar imports circulares.
- **Archivo:** `routes.py`
- **Riesgo:** Bajo (rendimiento)
- **Recomendación:** Reestructurar para permitir imports a nivel de módulo.

### 6.4 Arquitectura y Mantenibilidad

#### [A1] Verificación de admin inconsistente
`listar_usuarios` verifica `current_user.RoleId != 1` directamente en lugar de usar el decorador `permiso_requerido`.
- **Archivo:** `routes.py`
- **Riesgo:** Bajo
- **Recomendación:** Usar `@permiso_requerido('Admin', nivel=2)` o decorador de admin dedicado.

#### [A2] Categorías flash inconsistentes
Login usa `'error'`, logout usa `'success'`. Otros módulos usan `'danger'`, `'warning'`, `'info'`.
- **Archivo:** `routes.py` + `login.html`
- **Riesgo:** Bajo (UX)
- **Recomendación:** Estandarizar categorías flash en todo el proyecto.

#### [A3] Sin CRUD de usuarios
La vista `usuarios.html` solo muestra listado. No hay botones para crear, editar, activar/desactivar ni eliminar usuarios desde esta vista.
- **Archivo:** `usuarios.html`
- **Riesgo:** Bajo (funcionalidad posiblemente en módulo `gestion_usuarios`)

#### [A4] Inconsistencia en semántica de RoleId=6
En `routes.py` el redirect post-login para RoleId=6 va a `portada.bienvenida` (tratado como apoderado/estudiante). En `usuarios.html` se muestra como "Apoderado". En el módulo matrícula, RoleId=6 se usa como rol de estudiante en `OrganizationPersonRole`.
- **Archivo:** `routes.py`, `usuarios.html`
- **Riesgo:** Medio (confusión de negocio)
- **Recomendación:** Clarificar la semántica de RoleId=6 y documentarla.

### 6.5 Frontend

#### [F1] Tailwind via CDN en login.html
Usa `cdn.tailwindcss.com` que es la versión de desarrollo. En producción debería usar build compilada.
- **Archivo:** `login.html`
- **Riesgo:** Bajo (rendimiento en producción)

#### [F2] Sin maxlength ni validación de formato de RUT en frontend
El campo username no tiene `maxlength` ni validación JavaScript de formato antes del envío.
- **Archivo:** `login.html`
- **Riesgo:** Bajo

#### [F3] Encoding corrupto
Caracteres corruptos (`贸`, `铆`, `帽`, `帗`) confirman problema sistémico de encoding UTF-8.
- **Archivos:** `routes.py`, `login.html`
- **Riesgo:** Bajo (no afecta funcionalidad)
- **Recomendación:** Re-guardar todos los archivos como UTF-8 sin BOM.

#### [F4] Botón "Volver al Panel" siempre va a admin.dashboard
En `unauthorized.html`, el botón redirige a `admin.dashboard` sin considerar el rol del usuario. Un usuario no-admin recibiría otro 403.
- **Archivo:** `unauthorized.html`
- **Riesgo:** Bajo (UX)
- **Recomendación:** Redirigir según rol o a `portada.bienvenida`.

---

## 7. Resumen de Hallazgos por Severidad

### Alto (2)
- [S1] Sin protección CSRF
- [S2] `remember=True` hardcodeado

### Medio (4)
- [S3] Open Redirect via parámetro `next`
- [S4] Sin rate limiting en login
- [S6] Sin gestión de contraseñas
- [A4] Inconsistencia en semántica de RoleId=6

### Bajo (8)
- [S5] Admin bypass total (diseño intencional)
- [P1] N+1 queries en listar_usuarios
- [P2] Imports locales repetidos
- [A1] Verificación de admin inconsistente
- [A2] Categorías flash inconsistentes
- [A3] Sin CRUD de usuarios
- [F1] Tailwind CDN en producción
- [F4] Botón unauthorized siempre a admin.dashboard

---

## 8. Endpoint Map Visual

```
GET  /auth/login      → login()              (público)
POST /auth/login      → login()              (público)
GET  /auth/logout     → logout()             (@login_required)
GET  /auth/usuarios   → listar_usuarios()    (@login_required + RoleId==1)
```

---

*Auditoría generada a partir del análisis de los 5 archivos del módulo auth.*
```

---