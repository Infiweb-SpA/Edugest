## Analisis del Archivo 9 (biblioteca): `recursos.html`



### Proposito
Template Jinja2 que extiende `biblioteca/base.html`. Pagina estatica de enlaces a bibliotecas digitales open source.

### Recursos listados

| Recurso | URL | Descripcion |
|---------|-----|-------------|
| Project Gutenberg | gutenberg.org | 70,000+ libros electronicos gratuitos, clasicos de dominio publico |
| Internet Archive | archive.org/details/books | Millones de libros, textos academicos, audios y videos |
| Open Library | openlibrary.org | Catalogo editable, prestamos digitales controlados |
| Wikisource | es.wikisource.org | Textos originales de dominio publico (Wikimedia) |
| DOAJ | doaj.org | Directorio de revistas cientificas de acceso abierto |
| UNESCO Digital Library | unesdoc.unesco.org | Documentos y recursos educativos UNESCO |

### Observaciones para la auditoria

1. **Pagina completamente estatica**: Sin datos del backend, sin forms, sin logica de negocio.

2. **Enlaces externos con `target="_blank"`**: Todos los links abren en nueva pestana. Sin `rel="noopener noreferrer"` (aunque los navegadores modernos lo agregan por defecto).

3. **Tip informativo al final**: Sugiere registrar URLs de libros descargados como libros digitales en el catalogo de Edugest.

4. **Ningun riesgo de seguridad**: No hay forms, no hay datos sensibles, no hay interaccion con el backend.

---

### Modulo biblioteca: Resumen

| # | Archivo | Hallazgos clave |
|---|---------|-----------------|
| 1 | `routes.py` | 11 rutas, CRUD completo con control de stock, prestamos/devoluciones/renovaciones, auto-deteccion de atrasados, paginacion en catalogo e historial, sin CSRF, roleId 21 inusual |
| 2 | `__init__.py` | Define Blueprint (patron diferente a otros modulos) |
| 3 | `base.html` | Layout intermedio con navegacion por pestanas |
| 4 | `index.html` | Dashboard con KPIs, prestamos recientes, lazy loading |
| 5 | `catalogo.html` | Grid con paginacion, busqueda, CRUD con permisos, sin CSRF en eliminar |
| 6 | `nuevo_libro.html` | Formulario dual crear/editar, toggle virtual, sin CSRF |
| 7 | `prestamos.html` | Filtros por estado, devolver/renovar, sin CSRF, renovar hardcoded 7 dias |
| 8 | `nuevo_prestamo.html` | Select de libros y personas, sin CSRF, sin filtro por establecimiento |
| 9 | `historial.html` | **VACIO** |
| 10 | `recursos.html` | Pagina estatica con enlaces a bibliotecas open source |

---

Aqui va el `.md`:

```markdown
# Auditoría del Módulo: Biblioteca CRA

## 1. Resumen General

El módulo Biblioteca CRA (Centro de Recursos de Aprendizaje) gestiona el catálogo bibliográfico, sistema de préstamos/devoluciones con control de stock, historial de movimientos, y enlaces a recursos digitales open source. Es uno de los módulos mejor estructurados del sistema, con paginación, búsqueda, y protección de permisos consistente en todas las rutas.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/biblioteca/__init__.py` | Python | Define `biblioteca_bp` Blueprint |
| `app/modules/biblioteca/routes.py` | Python | Backend: 11 rutas, CRUD libros, préstamos, historial |
| `app/templates/biblioteca/base.html` | Jinja2/HTML | Layout intermedio con navegación por pestañas |
| `app/templates/biblioteca/index.html` | Jinja2/HTML | Dashboard con KPIs y préstamos recientes |
| `app/templates/biblioteca/catalogo.html` | Jinja2/HTML | Catálogo con búsqueda, paginación y CRUD |
| `app/templates/biblioteca/nuevo_libro.html` | Jinja2/HTML | Formulario crear/editar libro |
| `app/templates/biblioteca/prestamos.html` | Jinja2/HTML | Gestión de préstamos con filtros |
| `app/templates/biblioteca/nuevo_prestamo.html` | Jinja2/HTML | Formulario registrar préstamo |
| `app/templates/biblioteca/historial.html` | Jinja2/HTML | **Archivo vacío** |
| `app/templates/biblioteca/recursos.html` | Jinja2/HTML | Página de enlaces a bibliotecas open source |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2.

**Prefijo de rutas:** `/biblioteca`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `EdugestBook` | Edugest | Libros del catálogo (Title, Author, Isbn, TotalStock, AvailableStock, IsVirtual, FileUrl) |
| `EdugestBookLoan` | Edugest | Préstamos (BookId, OrganizationPersonRoleId, LoanDate, DueDate, ReturnDate, Status) |
| `OrganizationPersonRole` | Mineduc | Vinculación persona-sistema |
| `Person` | Mineduc | Datos personales |

### 2.2 Estados de préstamo

| Status | Descripción |
|--------|-------------|
| `Prestado` | Préstamo activo, dentro del plazo |
| `Atrasado` | Préstamo activo, fuera del plazo (auto-detectado) |
| `Devuelto` | Libro devuelto |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/biblioteca/` | GET | `index` | `@login_required` + permiso Bib 1 | Dashboard con estadísticas |
| `/biblioteca/catalogo` | GET | `catalogo` | `@login_required` + permiso Bib 1 | Catálogo paginado con búsqueda |
| `/biblioteca/libro/nuevo` | GET, POST | `nuevo_libro` | `@login_required` + permiso Bib 2 | Agregar libro |
| `/biblioteca/libro/<book_id>/editar` | GET, POST | `editar_libro` | `@login_required` + permiso Bib 2 | Editar libro |
| `/biblioteca/libro/<book_id>/eliminar` | POST | `eliminar_libro` | `@login_required` + permiso Bib 2 | Eliminar libro (si sin préstamos activos) |
| `/biblioteca/prestamos` | GET | `prestamos` | `@login_required` + permiso Bib 1 | Gestión de préstamos con filtros |
| `/biblioteca/prestamo/nuevo` | GET, POST | `nuevo_prestamo` | `@login_required` + permiso Bib 2 | Registrar préstamo |
| `/biblioteca/prestamo/<loan_id>/devolver` | POST | `devolver_prestamo` | `@login_required` + permiso Bib 2 | Registrar devolución |
| `/biblioteca/prestamo/<loan_id>/renovar` | POST | `renovar_prestamo` | `@login_required` + permiso Bib 2 | Extender fecha de devolución |
| `/biblioteca/historial` | GET | `historial` | `@login_required` + permiso Bib 1 | Historial paginado |
| `/biblioteca/recursos-digitales` | GET | `recursos_digitales` | `@login_required` + permiso Bib 1 | Recursos open source |

---

## 4. Funcionalidades de Negocio

### 4.1 Dashboard
- Cuenta total libros, préstamos activos, atrasados.
- Muestra 5 préstamos más recientes.

### 4.2 Catálogo
- Paginación (`per_page=12`).
- Búsqueda por título, autor o ISBN (ILIKE).
- CRUD completo: crear, editar, eliminar libros.
- Soporte para libros virtuales (e-books con URL de descarga).
- ISBN auto-generado si no se proporciona (`EDU-{timestamp}`).

### 4.3 Préstamos
- **Auto-detección de atrasados**: Al visitar `/prestamos`, marca como "Atrasado" todos los préstamos vencidos.
- Filtros por estado (Todos/Prestados/Atrasados/Devueltos).
- Control de stock: descuenta al prestar, recupera al devolver.
- Validaciones: stock disponible, sin préstamo duplicado del mismo libro.
- Renovación con extensión configurable (hardcoded 7 días en template).

### 4.4 Historial
- Paginación (`per_page=20`).
- Filtros por libro y persona.
- **Template vacío**: `historial.html` no tiene contenido.

### 4.5 Recursos Digitales
- Página estática con 6 enlaces a bibliotecas open source.

---

## 5. Análisis por Archivo

### 5.1 `__init__.py`
Define el Blueprint (patrón diferente a otros módulos que lo definen en `routes.py`).

### 5.2 `routes.py`
Backend completo con 11 rutas. Todas protegidas con `@login_required` + `@permiso_requerido`. Implementa paginación, búsqueda, control de stock, y auto-detección de atrasados.

### 5.3 `base.html`
Layout intermedio con navegación por pestañas (Dashboard, Catálogo, Préstamos, Recursos Digitales). Detección de pestaña activa via `request.endpoint`.

### 5.4 `index.html`
Dashboard con 3 KPIs, acciones rápidas (solo nivel 2), y lista de 5 préstamos recientes con badges de estado.

### 5.5 `catalogo.html`
Grid de tarjetas con búsqueda, paginación, y acciones CRUD con protección de permisos.

### 5.6 `nuevo_libro.html`
Formulario dual crear/editar con toggle para libro virtual (muestra/oculta campo URL).

### 5.7 `prestamos.html`
Tabla con filtros por estado (pill buttons), acciones devolver/renovar para nivel 2.

### 5.8 `nuevo_prestamo.html`
Select de libros disponibles y personas, duración configurable (7/14/30 días).

### 5.9 `historial.html`
**Archivo vacío**. La ruta existe en el backend pero el template no tiene contenido.

### 5.10 `recursos.html`
Página estática con 6 enlaces a bibliotecas open source (Gutenberg, Internet Archive, Open Library, Wikisource, DOAJ, UNESCO).

---

## 6. Hallazgos de Auditoría

### 6.1 Seguridad — ALTO

#### [S1] Sin protección CSRF
Ningún formulario POST incluye token CSRF. Afecta a: nuevo libro, editar libro, eliminar libro, nuevo préstamo, devolver, renovar.
- **Archivos:** Todos los templates con forms POST
- **Riesgo:** ALTO

### 6.2 Seguridad — MEDIO

#### [S2] Búsqueda de persona para préstamo usa `.first()`
`OrganizationPersonRole.query.filter_by(PersonId=persona_id).first()` toma el primer rol de la persona sin importar cuál. Si tiene múltiples roles, podría tomar el incorrecto.
- **Riesgo:** MEDIO

#### [S3] RoleId 21 en filtro de personas
El filtro `RoleId.in_([6, 21])` usa RoleId=21 para profesores, pero este ID no está documentado en el sistema de roles estándar (que usa RoleId=3 para Profesor).
- **Riesgo:** MEDIO

#### [S4] Renovación sin límite
No hay límite en la cantidad de renovaciones ni en los días extra. Un préstamo podría renovarse indefinidamente.
- **Riesgo:** MEDIO

#### [S5] Eliminación de libro con historial
`eliminar_libro` solo verifica préstamos activos. Un libro con historial de préstamos devueltos puede eliminarse, potencialmente perdiendo el historial (dependiendo de la configuración de cascade en SQLAlchemy).
- **Riesgo:** MEDIO

### 6.3 Rendimiento

#### [P1] Auto-actualización de atrasados al cargar préstamos
Cada visita a `/prestamos` ejecuta UPDATE masivo de todos los préstamos vencidos.
- **Riesgo:** BAJO-MEDIO

#### [P2] N+1 queries en templates
Acceso a relaciones lazy (`p.book`, `p.person_role.person`) en listas.
- **Riesgo:** MEDIO

### 6.4 Arquitectura

#### [A1] Template `historial.html` vacío
La ruta `/biblioteca/historial` existe en el backend pero el template no tiene contenido.
- **Riesgo:** BAJO (funcionalidad incompleta)

#### [A2] ISBN no editable en modo edición
El campo ISBN se muestra pero el backend de `editar_libro` no lo actualiza.

#### [A3] Sin búsqueda por persona/titulo en préstamos
El backend acepta parámetro `search` pero el template no tiene input de búsqueda.

#### [A4] Link de descarga sin validación de URL
`<a href="{{ libro.FileUrl }}">` sin validación de dominio o protocolo.

### 6.5 Frontend

#### [F1] Renovar con días hardcoded en template
`<input type="hidden" name="dias_extra" value="7">`. Siempre renueva 7 días.

#### [F2] Sin protección CSRF en formularios de eliminar y acciones
Forms POST de eliminar libro, devolver y renovar sin token CSRF.

---

## 7. Resumen de Hallazgos por Severidad

### Crítico (0)
Ninguno.

### Alto (1)
- [S1] Sin protección CSRF

### Medio (5)
- [S2] Búsqueda de persona usa `.first()` (rol arbitrario)
- [S3] RoleId 21 inusual para profesores
- [S4] Renovación sin límite
- [S5] Eliminación de libro puede perder historial
- [P2] N+1 queries en templates

### Bajo (4)
- [P1] Auto-actualización de atrasados en cada visita
- [A1] Template `historial.html` vacío
- [A2] ISBN no editable en modo edición
- [A4] Link de descarga sin validación de URL

---

## 8. Endpoint Map Visual

```
GET  /biblioteca/                           → index()               (permiso Bib 1)
GET  /biblioteca/catalogo                   → catalogo()            (permiso Bib 1)
GET  /biblioteca/libro/nuevo                → nuevo_libro()         (permiso Bib 2)
POST /biblioteca/libro/nuevo                → nuevo_libro()         (permiso Bib 2)
GET  /biblioteca/libro/<id>/editar          → editar_libro()        (permiso Bib 2)
POST /biblioteca/libro/<id>/editar          → editar_libro()        (permiso Bib 2)
POST /biblioteca/libro/<id>/eliminar        → eliminar_libro()      (permiso Bib 2)
GET  /biblioteca/prestamos                  → prestamos()           (permiso Bib 1)
GET  /biblioteca/prestamo/nuevo             → nuevo_prestamo()      (permiso Bib 2)
POST /biblioteca/prestamo/nuevo             → nuevo_prestamo()      (permiso Bib 2)
POST /biblioteca/prestamo/<id>/devolver     → devolver_prestamo()   (permiso Bib 2)
POST /biblioteca/prestamo/<id>/renovar      → renovar_prestamo()    (permiso Bib 2)
GET  /biblioteca/historial                  → historial()           (permiso Bib 1)
GET  /biblioteca/recursos-digitales         → recursos_digitales()  (permiso Bib 1)
```

---

## 9. Diagrama de Flujo de Préstamos

```
Nuevo Préstamo (nuevo_prestamo)
  ├── Verifica stock disponible
  ├── Verifica sin préstamo duplicado
  ├── Descuenta AvailableStock
  └── Crea EdugestBookLoan (Status='Prestado')
      │
      ├── [Fecha vencimiento pasada]
      │   └── Auto-detectado como 'Atrasado' al visitar /prestamos
      │
      ├── Devolver (devolver_prestamo)
      │   ├── Status → 'Devuelto'
      │   ├── ReturnDate → hoy
      │   └── Recupera AvailableStock
      │
      └── Renovar (renovar_prestamo)
          ├── DueDate += dias_extra
          └── Status → 'Prestado' (si estaba Atrasado)
```

---

*Auditoría generada a partir del análisis de los 10 archivos del módulo biblioteca (1 __init__.py + 1 routes.py + 8 templates, 1 vacío).*
```

---
