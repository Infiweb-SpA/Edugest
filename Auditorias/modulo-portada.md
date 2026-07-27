## Analisis del Archivo 4 (portada): `reglamento.html`



### Proposito
Template Jinja2 que extiende `base.html`. Pagina estatica del reglamento interno del establecimiento con 10 capítulos, indice navegable, y pie de documento.

### Datos del backend

Ninguno. Pagina completamente estatica.

### Estructura

1. **Cabecera**: Gradiente slate oscuro, icono documento, titulo, año academico 2026.

2. **Indice**: Grid 2 columnas con links ancla a cada capitulo (`#cap1` a `#cap10`).

3. **10 capitulos** (sections con `scroll-mt-24` para compensar header fijo):
   - 1. Disposiciones Generales (Art. 1-4)
   - 2. Derechos y Deberes (Art. 5-7)
   - 3. Normas de Convivencia Escolar (Art. 8-12)
   - 4. Asistencia y Puntualidad (Art. 13-17)
   - 5. Evaluaciones y Calificaciones (Art. 18-22)
   - 6. Uniforme y Presentacion Personal (Art. 23-26.4)
   - 7. Uso de Tecnologias (Art. 27-30)
   - 8. Medidas Disciplinarias (Art. 31-34)
   - 9. Protocolo de Emergencias (Art. 35-38)
   - 10. Disposiciones Finales (Art. 39-42)

4. **Pie**: Aprobado por Consejo Escolar, ultima actualizacion Marzo 2026.

### Referencias legales citadas

| Referencia | Contexto |
|-----------|----------|
| Ley N° 20.845 | Inclusion Escolar |
| Ley N° 20.370 | Ley General de Educacion |
| DFL N° 2 | Ministerio de Educacion |
| Decreto N° 67 | Normativa de Admision / Estatuto Docente |
| Decreto N° 1.055 | Condiciones minimas de funcionamiento |

### Observaciones para la auditoria

1. **Pagina completamente estatica**: Sin riesgo de seguridad. Sin forms, sin datos sensibles, sin interaccion con backend.

2. **Referencia a "Libro Digital"**: Art. 32.2 menciona "Anotacion negativa: Registro en el Libro Digital". El reglamento esta alineado con la funcionalidad del sistema.

3. **Referencia a "plataforma digital"**: Art. 22 menciona consulta de calificaciones via plataforma digital. Art. 37 menciona actualizacion de informacion medica via plataforma.

4. **Ano academico hardcoded**: "2026" en la cabecera. Deberia actualizarse cada ano.

5. **Scroll anchos con `scroll-mt-24`**: Compensa el header fijo de `base.html`. Patron correcto para navegacion interna.

6. **Presentacion personal (Art. 26.1-26.4)**: Seccion destacada con border-l indigo. Incluye articulos sobre cabello que promueven la inclusion y no discriminacion.

---

### Modulo portada: Resumen

| # | Archivo | Hallazgos clave |
|---|---------|-----------------|
| 1 | `__init__.py` | Importa Blueprint desde routes.py |
| 2 | `routes.py` | 2 rutas, bienvenida personalizada por rol, logica de visibilidad de eventos duplicada, sin permisos adicionales |
| 3 | `bienvenida.html` | Perfil con gradiente, acceso rapido, hijos/asignaturas, eventos, links vacios (#) |
| 4 | `reglamento.html` | Pagina estatica, 10 capitulos, ano hardcoded 2026 |

---

Aqui va el `.md`:

```markdown
# Auditoría del Módulo: Portada

## 1. Resumen General

El módulo Portada es la página de inicio personalizada del sistema Edugest. Proporciona una bienvenida adaptada al rol del usuario (estudiante, apoderado, profesor, administrador) con acceso rápido a módulos, información de cursos/hijos, próximos eventos del calendario, y una página estática del reglamento interno.

**Archivos del módulo:**

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `app/modules/portada/__init__.py` | Python | Importa `portada_bp` desde routes.py |
| `app/modules/portada/routes.py` | Python | Backend: 2 rutas, bienvenida personalizada |
| `app/templates/portada/bienvenida.html` | Jinja2/HTML | Página principal personalizada |
| `app/templates/portada/reglamento.html` | Jinja2/HTML | Reglamento interno (estático) |

**Tecnologías:** Flask, Flask-Login, SQLAlchemy ORM, Jinja2.

**Prefijo de rutas:** `/portada`

---

## 2. Modelo de Datos

### 2.1 Tablas utilizadas

| Modelo | Sistema | Uso |
|--------|---------|-----|
| `Person` | Mineduc | Datos personales |
| `PersonIdentifier` | Mineduc | RUT (Id=51) |
| `PersonRelationship` | Mineduc | Relación apoderado-hijo |
| `Organization` | Mineduc | Cursos (21), grados (46), asignaturas (22) |
| `OrganizationRelationship` | Mineduc | Jerarquía organizacional |
| `OrganizationPersonRole` | Mineduc | Matrícula |
| `EdugestRole` | Edugest | Nombre del rol |
| `EdugestCalendarEvent` | Edugest | Próximos eventos |

---

## 3. Mapa de Rutas

| Ruta | Método | Función | Protección | Descripción |
|------|--------|---------|------------|-------------|
| `/portada/bienvenida` | GET | `bienvenida` | `@login_required` | Página principal personalizada |
| `/portada/reglamento` | GET | `reglamento` | `@login_required` | Reglamento interno |

---

## 4. Funcionalidades de Negocio

### 4.1 Bienvenida
- Datos comunes: persona, RUT, nombre del rol.
- **Estudiante (RoleId=6)**: Curso actual, grado, asignaturas del grado. Grid de asignaturas con links a calificaciones y libro digital.
- **Apoderado (RoleId=5)**: Lista de hijos con RUT, curso, grado, asignaturas. Botón "Reporte" por hijo.
- **Admin (RoleId=1)**: 5 próximos eventos sin restricción.
- **Otros**: 5 próximos eventos filtrados por organizaciones visibles.

### 4.2 Reglamento
- Página estática con 10 capítulos y 42 artículos.
- Índice navegable con links ancla.
- Referencias a Ley 20.845 (Inclusión), Ley 20.370 (LGE), DFL N°2.

---

## 5. Hallazgos de Auditoría

### 5.1 Seguridad — NINGUNO

El módulo solo tiene GET con `@login_required`. No hay forms POST, no hay datos sensibles en riesgo adicional.

### 5.2 Arquitectura

#### [A1] Lógica de visibilidad de eventos duplicada
La función de calcular `org_ids` visibles está duplicada con `calendario/routes.py` (`_get_org_ids_for_user`). Tercer lugar donde se replica esta lógica (calendario, portada, y la versión de calendario).
- **Riesgo:** MEDIO (mantenibilidad)

#### [A2] Links vacíos en acceso rápido
"Libro Digital" y "Administrar" apuntan a `href="#"`. Links placeholder sin funcionalidad.
- **Riesgo:** BAJO (UX)

#### [A3] Rol nombre usado para condicionales en template
`rol_nombre in ['Estudiante', 'Profesor']` depende de que `EdugestRole.RoleName` sea exactamente estos strings. Si cambian, la UI falla silenciosamente.
- **Riesgo:** BAJO

#### [A4] Año académico hardcoded en reglamento
"2026" en la cabecera del reglamento.
- **Riesgo:** BAJO

#### [A5] Apoderado busca relaciones sin filtro de tipo
`PersonRelationship.query.filter_by(RelatedPersonId=current_user.PersonId)` no filtra por `RefPersonRelationshipId=31`. Podría incluir relaciones que no son padre-hijo.
- **Riesgo:** BAJO

---

## 6. Resumen de Hallazgos por Severidad

### Crítico (0)
Ninguno.

### Alto (0)
Ninguno.

### Medio (1)
- [A1] Lógica de visibilidad duplicada con calendario

### Bajo (4)
- [A2] Links vacíos en acceso rápido
- [A3] Rol nombre para condicionales
- [A4] Año hardcoded en reglamento
- [A5] Sin filtro de tipo en relaciones de apoderado

---

## 7. Endpoint Map Visual

```
GET /portada/bienvenida  → bienvenida()  (@login_required)
GET /portada/reglamento  → reglamento()  (@login_required)
```

---

## 8. Integración Cross-Módulo

| Módulo | Integración |
|--------|-------------|
| `reportes` | Link a `reporte_curso` e `reporte_notas_sumativas` |
| `libro_digital` | Link a `ver_unidades` |
| `calendario` | Muestra próximos eventos, link a `calendario.index` |

---

*Auditoría generada a partir del análisis de los 4 archivos del módulo portada.*
```

---
