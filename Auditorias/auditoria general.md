## Texto para el archivo de Auditoria General

```markdown
# AUDITORIA GENERAL - Sistema Edugest
## Fecha: Julio 2026
## Fase: Revision completa de arquitectura, modelos, permisos y flujo de datos

---

## 1. RESUMEN EJECUTIVO

El sistema Edugest es una plataforma de gestion educativa construida con Flask + SQLite
que implementa el estandar MINEDUC (EDE) con extensiones propias (Edugest). La arquitectura
de base de datos es solida y el flujo de matricula SI persiste correctamente en ambas capas
(MINEDUC y Edugest). Los problemas detectados son principalmente de **seguridad de rutas**,
**fragmentacion del sistema de permisos** y **consistencia de logica de negocio**.

---

## 2. TECNOLOGIAS

- Python / Flask
- SQLite
- Flask-Login (autenticacion)
- SQLAlchemy (ORM)
- Jinja2 (templates)
- Tailwind CSS
- JavaScript (frontend)
- ReportLab + Matplotlib (PDF/graficos)

---

## 3. ARQUITECTURA DE BASE DE DATOS

### 3.1 Capa MINEDUC (estandar EDE)
Tablas base oficiales que representan la estructura escolar chilena:

| Tabla | Proposito |
|---|---|
| `Person` | Identidad de personas (alumnos, profesores, apoderados) |
| `PersonIdentifier` | Documentos oficiales (RUT sys_id=51, IPE sys_id=52, etc.) |
| `Organization` | Estructura jerarquica (RBD, Modalidad, Jornada, Nivel, Grado, Curso, Asignatura) |
| `OrganizationRelationship` | Jerarquia padre-hijo entre organizaciones |
| `OrganizationPersonRole` | Vinculo persona-organizacion-rol |
| `OrganizationCalendarSession` | Leccionario oficial |
| `RoleAttendanceEvent` | Registro de asistencia oficial |
| `AssessmentResult` | Acta final de calificaciones |
| `Incident` / `IncidentPerson` | Incidentes y anotaciones |
| `K12StudentDiscipline` | Medidas disciplinarias |
| `PersonAddress`, `PersonTelephone`, `PersonEmailAddress` | Datos de contacto |
| `PersonRelationship` | Relaciones entre personas (padre, madre, apoderado) |
| `PersonHealth`, `PersonStatus`, `PersonDegreeOrCertificate` | Extensiones de persona |
| `PersonBirthplace`, `PersonAllergy` | Datos adicionales |

### 3.2 Capa Edugest (extensiones propias)

| Modulo | Tablas | Dependencia MINEDUC |
|---|---|---|
| A: Config y Permisos | `EdugestModule`, `EdugestRolePermission`, `EdugestOrganizationConfig` | `Organization.OrganizationId` |
| B: Planificacion y Asistencia | `EdugestCurriculumPlan`, `EdugestSessionAttendance`, `EdugestStudentObservation` | `Organization.OrganizationId`, `OrganizationCalendarSession`, `OrganizationPersonRole` |
| C: Evaluaciones Digitales | `EdugestAssessmentInstrument`, `EdugestAssessmentQuestion`, `EdugestQuestionOption`, `EdugestStudentResponse` | `Organization.OrganizationId`, `EdugestCurriculumPlan`, `OrganizationPersonRole` |
| D: Biblioteca CRA | `EdugestBook`, `EdugestBookLoan` | `OrganizationPersonRole` |
| E: Comunicaciones | `EdugestChatMessage`, `EdugestAnnouncement` | `Person.PersonId`, `Organization.OrganizationId` |
| F: Matricula Extendida | `EdugestStudentEnrollment`, `EdugestEmergencyContact`, `EdugestStudentHealth`, `EdugestStudentPIE`, `EdugestPersonRelationshipDetail` | `Person.PersonId`, `PersonRelationship.PersonRelationshipId` |
| G: Notas Manuales | `EdugestManualGrade` | `EdugestAssessmentInstrument`, `OrganizationPersonRole` |
| H: Usuarios y Auth | `EdugestUser`, `EdugestRole` | `Person.PersonId` |
| I: Calendario | `EdugestCalendarEvent` | `Organization.OrganizationId`, `EdugestAssessmentInstrument`, `Person.PersonId` |

### 3.3 Jerarquia MINEDUC (creada en seed.py)

```
RBD (Tipo 10)
  └── Modalidad (Tipo 38)
        └── Jornada (Tipo 39)
              └── Nivel (Tipo 40)
                    └── Rama (Tipo 41)
                          └── Sector (Tipo 42)
                                └── Especialidad (Tipo 43)
                                      └── TipoCurso (Tipo 44)
                                            └── CodigoEnsenanza (Tipo 45)
                                                  └── Grado (Tipo 46)
                                                        ├── Curso/Letra (Tipo 21)
                                                        └── Asignatura (Tipo 22)
```

---

## 4. SISTEMA DE PERMISOS

### 4.1 Sistema A (ACTIVO - el que funciona)

- **Tablas:** `EdugestModule` + `EdugestRolePermission` + `EdugestRole`
- **Niveles:** 0=Sin acceso, 1=Solo lectura, 2=Lectura y escritura
- **Autenticacion:** Flask-Login con `EdugestUser`
- **Context processor** en `__init__.py` inyecta `user_permisos` en Jinja2
- **Admin (RoleId=1):** Acceso nivel 2 automatico a todos los modulos

### 4.2 Sistema B (MUERTO - codigo sin uso)

- **Archivo:** `app/modules/admin/permissions.py`
- **Tablas que NO existen:** `EdugestSystemRole`, `Edug **Formato:** Booleanos CanView/CanEdit/CanDelete por feature code
- **Funciones:** `init_rbac_system()`, `check_permission()estSystemUser`, `EdugestFeaturePermission`
-`, `require_permission()`
- **Estado:** Nunca se importa ni ejecuta. Codigo muerto.

### 4.3 Implementaciones redundantes del chequeo de permisos

| # | Implementacion | Ubicacion | Usa |
|---|---|---|---|
| 1 | `get_permiso_modulo()` | `matricula/routes.py` | Helper local, consulta EdugestRolePermission |
| 2 | `get_permiso_modulo()` | `reportes/routes.py` | Helper local, copia exacta de #1 |
| 3 | `_get_nivel_permiso()` | `calendario/routes.py` | Helper local, misma logica |
| 4 | `_es_nivel_2_evaluaciones()` | `evaluaciones/routes.py` | Helper local, variante |
| 5 | `verificar_escritura()` | `auth/routes.py` | Funcion exportada, abort(403) |
| 6 | `permiso_requerido()` | `auth/routes.py` | Decorador principal |
| 7 | `if current_user.RoleId == 1` | Multiples archivos | Chequeo manual inline |

### 4.4 Mapa de uso de permisos por modulo

| Modulo | Decorador `@permiso_requerido` | Helper local | Manual `RoleId==1` | Sin proteccion |
|---|---|---|---|---|
| admin | NO | NO | NO | **TODAS (2)** |
| auth | NO | NO | SI | Login es publico |
| portada | NO | NO | NO | **TODAS (2)** |
| matricula | NO | SI (`get_permiso_modulo`) | NO | AJAX endpoints |
| **calendario** | **SI - TODAS** | Helper para nivel adicional | NO | Ninguna |
| **comunicacion** | **SI - TODAS** | Inline para chat | NO | Ninguna |
| evaluaciones | PARCIAL (6/10) | SI (`_es_nivel_2`) | NO | 4 rutas GET |
| **biblioteca** | **SI - TODAS** | NO | NO | Ninguna |
| libro_digital | PARCIAL (5/9) | Inline en `ver_unidades` | NO | 4 rutas GET |
| gestion_usuarios | NO | NO | SI | Todas (manual) |
| gestion_roles | NO | NO | SI | Todas (manual) |
| reportes | NO | SI (`get_permiso_modulo`) | NO | 6+ rutas |

---

## 5. PROBLEMAS DETECTADOS

### 5.1 CRITICOS (afectan funcionalidad o seguridad)

| ID | Problema | Archivo(s) | Descripcion |
|---|---|---|---|
| iniciar la app sin seed.py. El modulo de Matricula queda deshabilitado. |
| C2 | Sistema de permisos B (muerto) coexiste con Sistema A | `admin/permissions.py` | Importa modelos inexistentes (`EdugestSystemRole`, `EdugestSystemUser`, `EdugestFeaturePermission`). Si se importa, causa ImportError. |
| C3 | Admin sin `@login_required` | `admin/routes.py` | `/admin/` y `/admin/toggle-module` accesibles sin autenticacion. |
| C4 | Toggle de modulos sin verificacion de permisos | `admin/routes.py` | Cualquier usuario (o no autenticado) puede habilitar/deshabilitar modulos. |

### 5.2 ALTAS (afectan experiencia o logica de negocio)

| ID | Problema | Archivo(s) | Descripcion |
|---|---|---|---|
| A1 | RoleId de Apoderado inconsistente | `portada`, `reportes`, `comunicacion`, `auth`, `seed` | `portada` y `reportes` usan RoleId=5 para apoderados. `comunicacion` verifica RoleId=6. `auth` redirige RoleId=6 a portada. `seed.py` nunca crea usuario con RoleId=5. No hay garantia de consistencia. |
| A2 | Sender en anuncios no es usuario actual | `comunicacion/routes.py` | `nuevo_anuncio()` busca la primera persona con RoleId 1 o 2 en la BD, no usa `current_user.PersonId`. |
| A3 | 4 rutas de libro_digital sin decorador | `libro_digital/routes.py` | `listar_grados`, `asignaturas_por_grado`, `ver_unidades`, `registrar_clase_get` solo tienen `@login_required`. Cualquier usuario autenticado accede. Lineas en blanco entre decorador y def sugieren decorador removidoMatricula", "Reportes" y "Calend C1 | Modulos faltantes en semilla de `__init__.py` | `app/__init__.py` | "ario" no se crean al. |
| A4 | 4 rutas de evaluaciones sin decorador | `evaluaciones/routes.py` | `asignaturas_por_grado`, `unidades_asignatura`, `rendir`, `resultados` sin `@permiso_requerido`. |
| A5 | 6+ rutas de reportes sin proteccion | `reportes/routes.py` | `index`, `reporte_curso`, `reporte_grado`, `reporte_notas_sumativas`, graficos, export, PDF. Solo helper local inline para algunas. |
| A6 | `ver_unidades()` consulta permiso equivocado | `libro_digital/routes.py` | Consulta `ModuleName='Evaluaciones'` en vez de `'Libro Digital'` para filtrar visibilidad de evaluaciones. |

### 5.3 MEDIAS (deuda tecnica, mantenibilidad)

| ID | Problema | Archivo(s) | Descripcion |
|---|---|---|---|
| M1 | `_get_org_ids_for_user()` duplicada | `portada/routes.py`, `calendario/routes.py` | ~60 lineas de logica identica copiada en dos archivos. |
| M2 | `get_permiso_modulo()` duplicada | `matricula/routes.py`, `reportes/routes.py` | Mismo helper copiado en dos archivos. |
| M3 | Cada modulo redefine helper de permisos localmente | 5+ archivos | Al menos 5 implementaciones distintas del mismo chequeo. |
| M4 | Decorador `permiso_requerido()` subutilizado | `auth/routes.py` | Definido correctamente pero solo usado en calendario, comunicacion, parcialmente evaluaciones y biblioteca. |
| M5 | Verificacion redundante despues de decorador | `comunicacion/routes.py` | `nuevo_anuncio()` verifica `RoleId == 6` despues de `@permiso_requerido('Comunicaciones', nivel=2)`. |

### 5.4 BAJAS (cosmeticas, inconsistencias menores)

| ID | Problema | Archivo(s) | Descripcion |
|---|---|---|---|
| B1 | `pytz` vs `ZoneInfo` inconsistentes | `comunicacion` vs modelos | Dos mecanismos para zona horaria de Chile. |
| B2 | `EdugestChatMessage.SentAt` usa `datetime.utcnow` | `edugest.py` modelo | Guarda UTC en vez de hora Chile como el resto de las tablas. |
| B3 | `crear_instrumento()` redirige hardcodeado | `evaluaciones/routes.py` | Redirige siempre a grado_id=1 ignorando el org_id recibido. |
| B4 | Lineas en blanco entre decoradores y defs | `libro_digital/routes.py` | 4 funciones con linea en blanco entre `@login_required` y `def`, sugiere decorador eliminado. |
| B5 | Roles 2, 3, 4, 5 no se crean en `EdugestRole` en seed | `seed.py` | Solo se crean usuarios con RoleId, pero el catalogo `EdugestRole` queda sin entradas para Director, Profesor, Funcionario, Apoderado. |

---

## 6. FLUJO DE MATRICULA (verificacion)

### 6.1 El flujo SI guarda en tablas MINEDUC

| Operacion | Tabla MINEDUC | Verificado |
|---|---|---|
| Crear/actualizar estudiante | `Person` | SI |
| RUT, IPE, num_matricula, num_lista | `PersonIdentifier` (sys_id 51, 52, 55, 54) | SI |
| Asignar curso | `OrganizationPersonRole` (RoleId=6) | SI |
| Residencia | `PersonAddress` | SI |
| Relacion estudiante-apoderado | `PersonRelationship` (RefPersonRelationshipId=31) | SI |
| Datos de apoderados | `PersonTelephone`, `PersonEmailAddress`, `PersonDegreeOrCertificate` | SI |

### 6.2 El flujo SI guarda en tablas Edugest

| Operacion | Tabla Edugest | Verificado |
|---|---|---|
| Datos extendidos de matricula | `EdugestStudentEnrollment` | SI |
| Contactos de emergencia | `EdugestEmergencyContact` | SI |
| Informacion medica | `EdugestStudentHealth` | SI |
| PIE | `EdugestStudentPIE` | SI |
| Detalles de relacion apoderado | `EdugestPersonRelationshipDetail` | SI |

### 6.3 Posibles causas de "no se guardan datos"

1. El modulo "Matricula" no existe en `EdugestModule` (problema C1) → `verificar_modulo_habilitado()` bloquea el acceso.
2. Error en tiempo de ejecucion causa `db.session.rollback()` (el except en `nuevo_estudiante()` borra todo).
3. Confusion entre tablas: esperar datos en `AssessmentResult` (que no se llena desde matricula).

---

## 7. MAPEO DE ROLES

| RoleId | Rol | Creado en seed? | Referenciado en |
|---|---|---|---|
| 1 | Administrador | No (creado manual) | auth, admin, gestion_usuarios, gestion_roles, todos |
| 2 | Director | SI (crear_director_prueba) | comunicacion (rol_nombre_map) |
| 3 | Profesor | SI (crear_profesor_jefe_prueba) | auth (redirect), comunicacion, gestion_usuarios |
| 4 | Funcionario | NO | comunicacion (rol_nombre_map) |
| 5 | Apoderado | NO | portada (RoleId==5), reportes (RoleId==5) |
| 6 | Estudiante | SI (matricula automatica) | auth (redirect), portada, comunicacion, evaluaciones |

---

## 8. MODULOS Y ESTADO

| Modulo | Ruta URL | Blueprint | Archivo principal |
|---|---|---|---|
| Admin | `/admin/` | `admin_bp` | `admin/routes.py` |
| Auth | `/auth/` | `auth_bp` | `auth/routes.py` |
| Portada | `/portada/` | `portada_bp` | `portada/routes.py` |
| Matricula | `/matricula/` | `matricula_bp` | `matricula/routes.py` |
| Calendario | `/calendario/` | `calendario_bp` | `calendario/routes.py` |
| Comunicacion | `/comunicacion/` | `comunicacion_bp` | `comunicacion/routes.py` |
| Evaluaciones | `/evaluaciones/` | `evaluaciones_bp` | `evaluaciones/routes.py` |
| Biblioteca | `/biblioteca/` | `biblioteca_bp` | `biblioteca/routes.py` |
| Libro Digital | `/libro-digital/` | `libro_digital_bp` | `libro_digital/routes.py` |
| Gestion Usuarios | `/gestion-usuarios/` | `gestion_usuarios_bp` | `gestion_usuarios/routes.py` |
| Gestion Roles | `/gestion-roles/` | `gestion_roles_bp` | `gestion_roles/routes.py` |
| Reportes | `/reportes/` | `reportes_bp` | `reportes/routes.py` |

---

## 9. ARCHIVOS REVISADOS EN AUDITORIA GENERAL

| Archivo | Rol en auditoria |
|---|---|
| `app/models/edugest.py` | Modelos Edugest (todas las tablas extendidas) |
| `app/models/EdugestCalendar.py` | Modelo de calendario |
| `app/models/mineduc.py` | Modelos MINEDUC base |
| `app/models/__init__.py` | Imports de modelos |
| `app/__init__.py` | Factory, registro de blueprints, semilla de modulos |
| `app/config.py` | Configuracion de BD |
| `app/modules/admin/permissions.py` | Sistema B de permisos (muerto) |
| `app/modules/admin/routes.py` | Panel admin |
| `app/modules/auth/routes.py` | Autenticacion y decorador de permisos |
| `app/modules/portada/routes.py` | Pantalla de bienvenida |
| `app/modules/calendario/routes.py` | Calendario academico |
| `app/modules/comunicacion/routes.py` | Chat y anuncios |
| `app/modules/evaluaciones/routes.py` | Motor de evaluaciones |
| `app/modules/biblioteca/routes.py` | Biblioteca CRA |
| `app/modules/libro_digital/routes.py` | Libro de clases digital |
| `app/modules/gestion_usuarios/routes.py` | CRUD de usuarios |
| `app/modules/gestion_roles/routes.py` | CRUD de roles y permisos |
| `app/modules/reportes/routes.py` | Reportes y PDFs |
| `app/modules/matricula/routes.py` | Matricula de estudiantes |
| `seed.py` | Datos de prueba y jerarquia MINEDUC |
```

---

## Plan de auditorias especificas por modulo

A continuacion listo cada modulo, los archivos que necesitare y que evaluare:

### Modulo 1: Matricula
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `matricula/routes.py` | SI | Requiere re-lectura detallada |
| `templates/matricula/formulario.html` | NO | **Necesario** - verificar campos del formulario vs modelo, validaciones frontend |
| `templates/matricula/listar.html` | NO | **Necesario** - verificar permisos en template |
| `templates/matricula/ver.html` | NO | **Necesario** - verificar vista de detalle |

### Modulo 2: Gestion de Usuarios
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `gestion_usuarios/routes.py` | SI | Requiere re-lectura detallada |
| `templates/gestion_usuarios/formulario.html` | NO | **Necesario** - verificar campos y validaciones |
| `templates/gestion_usuarios/listar.html` | NO | **Necesario** - verificar vista de listado |

### Modulo 3: Gestion de Roles
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `gestion_roles/routes.py` | SI | Requiere re-lectura detallada |
| `templates/gestion_roles/listar.html` | NO | **Necesario** |
| `templates/gestion_roles/editar_permisos.html` | NO | **Necesario** - verificar interfaz de permisos |
| `templates/gestion_roles/nuevo_rol.html` | NO | **Necesario** |

### Modulo 4: Admin
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `admin/routes.py` | SI | Requiere re-lectura |
| `admin/permissions.py` | SI | Sistema B muerto |
| `templates/admin/dashboard.html` | NO | **Necesario** - verificar interfaz admin |
| `templates/admin/permisos.html` | NO | **Necesario** |
| `templates/admin/roles.html` | NO | **Necesario** |
| `templates/admin/usuarios.html` | NO | **Necesario** |

### Modulo 5: Auth
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `auth/routes.py` | SI | Requiere re-lectura |
| `templates/auth/login.html` | NO | **Necesario** |
| `templates/auth/unauthorized.html` | NO | **Necesario** |

### Modulo 6: Evaluaciones
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `evaluaciones/routes.py` | SI | Requiere re-lectura detallada |
| `templates/evaluaciones/grados.html` | NO | **Necesario** |
| `templates/evaluaciones/asignaturas.html` | NO | **Necesario** |
| `templates/evaluaciones/unidades.html` | NO | **Necesario** |
| `templates/evaluaciones/crear_evaluacion.html` | NO | **Necesario** |
| `templates/evaluaciones/disenar_preguntas.html` | NO | **Necesario** |
| `templates/evaluaciones/rendir.html` | NO | **Necesario** |
| `templates/evaluaciones/resultados.html` | NO | **Necesario** |
| `templates/evaluaciones/imprimir.html` | NO | **Necesario** |

### Modulo 7: Libro Digital
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `libro_digital/routes.py` | SI | Requiere re-lectura detallada |
| `templates/libro_digital/grados.html` | NO | **Necesario** |
| `templates/libro_digital/asignaturas.html` | NO | **Necesario** |
| `templates/libro_digital/unidades.html` | NO | **Necesario** |
| `templates/libro_digital/lista_curso.html` | NO | **Necesario** |
| `templates/libro_digital/registrar_clase.html` | NO | **Necesario** |
| `templates/libro_digital/anotaciones.html` | NO | **Necesario** |

### Modulo 8: Biblioteca
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `biblioteca/routes.py` | SI | Requiere re-lectura |
| `biblioteca/__init__.py` | NO | **Necesario** - verificar init del blueprint |
| `templates/biblioteca/base.html` | NO | **Necesario** |
| `templates/biblioteca/index.html` | NO | **Necesario** |
| `templates/biblioteca/catalogo.html` | NO | **Necesario** |
| `templates/biblioteca/nuevo_libro.html` | NO | **Necesario** |
| `templates/biblioteca/prestamos.html` | NO | **Necesario** |
| `templates/biblioteca/nuevo_prestamo.html` | NO | **Necesario** |

### Modulo 9: Comunicacion
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `comunicacion/routes.py` | SI | Requiere re-lectura |
| `templates/comunicacion/anuncios.html` | NO | **Necesario** |
| `templates/comunicacion/chat_lista.html` | NO | **Necesario** |
| `templates/comunicacion/chat_conversacion.html` | NO | **Necesario** |
| `templates/comunicacion/contactos.html` | NO | **Necesario** |
| `templates/comunicacion/contacto_detalle.html` | NO | **Necesario** |

### Modulo 10: Calendario
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `calendario/routes.py` | SI | Requiere re-lectura |
| `calendario/__init__.py` | NO | **Necesario** - verificar init del blueprint |
| `templates/calendario/index.html` | NO | **Necesario** |

### Modulo 11: Reportes
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `reportes/routes.py` | SI | Requiere re-lectura detallada |
| `templates/reportes/index.html` | NO | **Necesario** |
| `templates/reportes/curso.html` | NO | **Necesario** |
| `templates/reportes/grado.html` | NO | **Necesario** |
| `templates/reportes/notas_sumativas.html` | NO | **Necesario** |
| `templates/reportes/configurar_sumativas.html` | NO | **Necesario** |
| `templates/reportes/apoderado_hijos.html` | NO | **Necesario** |

### Modulo 12: Portada
| Archivo | Ya revisado? | Necesario para auditoria especifica |
|---|---|---|
| `portada/routes.py` | SI | Requiere re-lectura |
| `templates/portada/bienvenida.html` | NO | **Necesario** |
| `templates/portada/reglamento.html` | NO | **Necesario** |

---