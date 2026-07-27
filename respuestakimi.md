He analizado las 28 capturas de pantalla de **Edugest** como un todo integrado. A continuación presento el análisis estratégico por módulo, la arquitectura de valor por stakeholder y las recomendaciones de presentación comercial.

---

# Análisis Estratégico de Edugest — Consultoría de Preventa

## 1. Análisis por Módulo Funcional

### Módulo: Administración — Gestión de Usuarios y Roles

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Creación de cuentas de usuario a partir de personas ya registradas (alumnos, apoderados) o registro directo de funcionarios; asignación de roles y matriz de permisos por módulo. |
| **Problema que resuelve** | Elimina la duplicidad de identidades (una persona, un RUT, múltiples roles) y evita que usuarios accedan a información sensible fuera de su alcance jerárquico. |
| **Beneficio práctico** | El administrador no crea "usuarios huérfanos"; el sistema hereda datos de matrícula. Los permisos son granulares (lectura, escritura, sin acceso) por módulo. |
| **Características destacables** | Precarga desde personas existentes; RUT como username; roles predefinidos (Profesor, Director, UTP, Inspector, Administrador); activación/desactivación de cuentas sin borrar historial. |
| **Público objetivo** | Administrador del sistema, Director, UTP. |
| **Nivel de importancia** | **Alta** (seguridad y gobernanza del sistema). |

---

### Módulo: Libro Digital — Planificación Curricular

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Habilitación de grados escolares, carga del Plan de Estudios Base MINEDUC, creación de unidades curriculares y clases con objetivos, contenidos y materiales adjuntos. |
| **Problema que resuelve** | Desarticulación entre la planificación curricular formal y su ejecución en el aula; dispersión de recursos didácticos en drives personales. |
| **Beneficio práctico** | La planificación queda vinculada directamente a las evaluaciones y al registro de clases. Un docente nuevo puede replicar la estructura curricular del año anterior. |
| **Características destacables** | Toggle de habilitación por grado; asignaturas precargadas MINEDUC; unidades desplegables tipo acordeón; carga de materiales (PDF, PPT, Excel) por clase; vinculación nativa con el módulo de evaluaciones. |
| **Público objetivo** | Docentes, UTP, Directores. |
| **Nivel de importancia** | **Alta** (eje pedagógico del sistema). |

---

### Módulo: Evaluaciones y Calificaciones

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Creación de evaluaciones sumativas o calificativas vinculadas a clases específicas, registro de notas manuales o automáticas, y publicación de resultados. |
| **Problema que resuelve** | El "papelógrafo" de notas en Excel personales, la pérdida de trazabilidad de qué evaluación corresponde a qué unidad, y el cálculo manual de promedios. |
| **Beneficio práctico** | Las evaluaciones sumativas se promedian automáticamente. El docente puede registrar notas manuales para pruebas presenciales o habilitar evaluaciones digitales remotas con auto-corrección. |
| **Características destacables** | Tipificación Sumativa/Calificativa; vinculación obligatoria a clase específica; fechado con reflejo automático en calendario académico; matriz de notas con checkbox "Nota Manual"; estados visuales (Aprobado/No Rendido). |
| **Público objetivo** | Docentes, UTP, Alumnos (resultados), Apoderados (resultados). |
| **Nivel de importancia** | **Alta** (core académico). |

---

### Módulo: Calendario Académico

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Vista mensual de eventos tipificados (evaluaciones, vacunación, talleres, actividades extracurriculares, reuniones, feriados). |
| **Problema que resuelve** | La falta de una fuente única de verdad sobre la vida escolar; los apoderados y alumnos no saben cuándo hay evaluaciones o reuniones. |
| **Beneficio práctico** | Centraliza la agenda institucional. Una evaluación creada en el módulo académico aparece automáticamente aquí. |
| **Características destacables** | Tipología de eventos con color coding; navegación por mes; botón directo "Nuevo Evento". |
| **Público objetivo** | Toda la comunidad escolar (lectura); Administración/UTP (escritura). |
| **Nivel de importancia** | **Media-Alta** (visibilidad y coordinación familiar). |

---

### Módulo: Comunicaciones — Anuncios, Contactos y Mensajería

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Tablero de anuncios segmentados por curso, directorio de contactos filtrable por rol/curso, y mensajería instantánea tipo chat entre actores del establecimiento. |
| **Problema que resuelve** | La comunicación unidireccional y masiva (grupos de WhatsApp caóticos) sin trazabilidad ni segmentación. |
| **Beneficio práctico** | Los anuncios llegan solo a quienes corresponden. Los apoderados pueden contactar al profesor jefe sin exponer números personales. El colegio conserva registro de las comunicaciones. |
| **Características destacables** | Filtro por curso en anuncios; directorio con íconos de rol; chat con burbuja propia; diferenciación Alumnos/Apoderados vs. Funcionarios. |
| **Público objetivo** | Director, UTP, Docentes, Inspectores, Apoderados. |
| **Nivel de importancia** | **Alta** (engagement familiar y trazabilidad legal). |

---

### Módulo: Biblioteca CRA (Centro de Recursos de Aprendizaje)

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Catálogo de libros físicos y digitales, registro de préstamos con control de días y morosidad, e integración con repositorios open source. |
| **Problema que resuelve** | El control de préstamos en papel o Excel, la pérdida de ejemplares, y la falta de acceso a recursos digitales gratuitos. |
| **Beneficio práctico** | El bibliotecario/inspector sabe en tiempo real qué está prestado, atrasado o disponible. Los estudiantes acceden a Gutenberg, Internet Archive, Open Library y Wikisource sin salir de la plataforma. |
| **Características destacables** | Dashboard con KPIs (Total, Prestados, Atrasados); ISBN con autogeneración; flag de e-book; préstamo con selección de días; integración open source. |
| **Público objetivo** | Bibliotecario, Inspectores, Alumnos, Docentes. |
| **Nivel de importancia** | **Media** (diferenciador en colegios con CRA activo). |

---

### Módulo: Matrícula y Ficha del Estudiante

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Formulario wizard de matrícula con precarga de datos históricos y ficha integral del estudiante (identidad, datos personales, residencia, apoderados, emergencia, salud, PIE, académica, socioeconómica, transporte). |
| **Problema que resuelve** | La recolección dispersa de datos en inicio de año; la duplicidad de fichas en distintos departamentos (secretaría, inspectoría, UTP). |
| **Beneficio práctico** | Una sola ficha única por estudiante, actualizable en línea. La precarga desde matrícula anterior acelera el proceso y reduce errores de tipeo. |
| **Características destacables** | Wizard por pasos con validación; precarga inteligente por RUT/nombre; ficha visual tipo "tarjeta de identidad" con todos los datos consolidados. |
| **Público objetivo** | Secretaría, Inspectores, UTP, Director. |
| **Nivel de importancia** | **Alta** (operación crítica de inicio de año). |

---

### Módulo: Reportes — Curso y Consolidado por Grado

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Panel de reportes con asistencia (Presente/Ausente/Atrasado), calificaciones sumativas/calificativas, promedios generales y anotaciones disciplinarias; exportable a CSV. |
| **Problema que resuelve** | La imposibilidad de tener una radiografía instantánea del rendimiento de un curso o grado completo para la toma de decisiones pedagógicas o de convivencia. |
| **Beneficio práctico** | El director o UTP detecta cursos con bajo rendimiento o alta ausentismo en segundos, sin esperar a que cada docente entregue su planilla. |
| **Características destacables** | Vista curso con detalle por alumno; vista grado consolidada con promedio general; badges de color (P/A/T); conteo de anotaciones positivas/negativas; exportación CSV. |
| **Público objetivo** | Director, UTP, Inspectores. |
| **Nivel de importancia** | **Alta** (inteligencia de gestión). |

---

### Módulo: Informe de Calificaciones Oficial (PDF)

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Generación del informe de calificaciones en formato oficial chileno (2° Semestre), con asignaturas, N1, promedio, asistencia, inasistencias, atrasos, anotaciones y observaciones. |
| **Problema que resuelve** | La elaboración manual de informes en Word o planillas heredadas, con alto riesgo de error y falta de estandarización. |
| **Beneficio práctico** | El colegio entrega un documento formal, homogéneo y legalmente sólido en segundos, firmado por profesor jefe y director. |
| **Características destacables** | Formato regulatorio chileno; campos de firma digital/escaneada; datos auto-completados desde el módulo de evaluaciones. |
| **Público objetivo** | Secretaría, Profesores Jefes, Director. |
| **Nivel de importancia** | **Alta** (cumplimiento normativo y cierre de semestre). |

---

### Módulo: Portal del Alumno

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Panel de bienvenida personalizado con acceso rápido a calificaciones por asignatura, unidades y clases, próximas actividades evaluativas y recursos útiles. |
| **Problema que resuelve** | El alumno no sabe cuándo evalúan ni cuál es su situación académica actual hasta que el profesor se lo comunica. |
| **Beneficio práctico** | Autogestión del aprendizaje. El alumno puede anticipar evaluaciones y revisar su progreso sin intermediarios. |
| **Características destacables** | Banner personalizado con nombre, curso y rol; tarjetas por asignatura; widget de próximas actividades con fechas; acceso a calendario académico y reglamento. |
| **Público objetivo** | Alumnos. |
| **Nivel de importancia** | **Media-Alta** (experiencia de usuario y engagement). |

---

### Módulo: Portal del Apoderado

| Atributo | Detalle |
|----------|---------|
| **Funcionalidad principal** | Vista unificada de todos los hijos matriculados, con acceso a sus reportes académicos, asistencia y anotaciones. |
| **Problema que resuelve** | El apoderado con múltiples hijos en el mismo colegio debe iniciar sesión con distintas cuentas o solicitar información por separado. |
| **Beneficio práctico** | Visión 360° de la familia en una sola pantalla. Transparencia inmediata sobre rendimiento y convivencia. |
| **Características destacables** | Selector de hijo con RUT y curso; acceso directo a reportes individuales. |
| **Público objetivo** | Apoderados/Tutores. |
| **Nivel de importancia** | **Alta** (fidelización y confianza familiar). |

---

## 2. Arquitectura de Valor por Stakeholder

### Para el Colegio (Institución)
- **Centralización operativa**: Toda la gestión académica, administrativa y de comunicación en una sola plataforma.
- **Trazabilidad legal**: Registro inmutable de comunicaciones, anotaciones, asistencias y calificaciones.
- **Cumplimiento normativo**: Informes oficiales alineados con la normativa chilena (Decreto 1358/2011, Decreto 67/2018).
- **Reducción de costos**: Menor dependencia de papel, planillas Excel y sistemas paralelos.

### Para el Director
- **Visión estratégica**: Reportes consolidados por grado y curso con indicadores de asistencia, rendimiento y convivencia.
- **Control de gestión**: Matriz de permisos que le permite delegar sin perder soberanía sobre la información sensible.
- **Toma de decisiones**: Detección temprana de cursos con problemas académicos o disciplinarios.

### Para la UTP (Unidad Técnico Pedagógica)
- **Seguimiento curricular**: Supervisión de la planificación en el Libro Digital sin depender de revisiones físicas.
- **Coordinación docente**: Visión de qué evaluaciones se han creado, publicado y calificado por asignatura.
- **Reportes académicos**: Acceso a promedios y estadísticas sin solicitar información a cada docente.

### Para los Docentes
- **Planificación integrada**: El Libro Digital vincula unidades, clases y evaluaciones en un flujo continuo.
- **Registro ágil de notas**: Matriz de calificaciones con edición manual o automática, evitando Excel.
- **Comunicación directa**: Contacto con apoderados vía mensajería interna sin exponer datos personales.

### Para los Inspectores
- **Control de asistencia y atrasos**: Registro sistemático con impacto directo en el informe oficial del alumno.
- **Anotaciones disciplinarias**: Registro positivo y negativo trazable en el tiempo.
- **Gestión de préstamos**: Control de la Biblioteca CRA y morosidad de libros.

### Para los Apoderados
- **Transparencia total**: Acceso a notas, asistencia, anotaciones y próximas evaluaciones en tiempo real.
- **Comunicación institucional**: Anuncios segmentados y mensajería directa con docentes.
- **Gestión familiar**: Un solo login para ver a todos sus hijos matriculados.

### Para los Alumnos
- **Autogestión**: Conocimiento anticipado de evaluaciones y entregas.
- **Acceso a recursos**: Biblioteca digital open source y materiales de clase subidos por los profesores.
- **Visión de progreso**: Calificaciones por asignatura y estado académico.

---

## 3. Recomendaciones de Presentación Comercial

### Capturas Repetidas o Redundantes
| Captura | Razón |
|---------|-------|
| **Evaluaciones 02** y **Libro Digital 02** | Muestran la misma estructura de "Unidades Curriculares y Clases". Son la misma funcionalidad accedida desde menús distintos. En una presentación, basta mostrar una sola. |

### Capturas Poco Útiles para Preventa
| Captura | Razón |
|---------|-------|
| **login 00.png** | Es un login estándar. Aporta branding pero no diferenciación funcional. Úsala solo si se quiere mostrar la experiencia de acceso. |
| **Biblioteca 03.png** (Recursos Open Source) | Es una pantalla de links externos. Aporta valor pero no es core; puede mencionarse verbalmente. |

### Capturas Imprescindibles (deben ir en la presentación)
| Captura | Por qué |
|---------|---------|
| **Matricula.png** / **Matricula 01.png** | Muestra la profundidad del dato y la ficha única. Diferenciador frente a sistemas livianos. |
| **Evaluaciones 03.png** / **Evaluaciones 04.png** | El flujo de creación de evaluación y la matriz de notas es el corazón académico. |
| **Reportes 01.png** / **Reportes 02.png** | La radiografía de curso y grado es lo que vende la "inteligencia" del sistema al director. |
| **alumno 00.png** | La experiencia del estudiante es emocionalmente persuasiva para apoderados y directores. |
| **apoderados 00.jpeg** | Muestra la visión familiar unificada, un dolor real que pocos sistemas resuelven bien. |
| **Comunicaciones 02.png** | El chat interno demuestra que no es solo un "avisador", es una plataforma de comunicación bidireccional. |
| **informe 00.png** | El documento oficial chileno genera confianza regulatoria inmediata. |

### Capturas que Deberían Ir Juntas en una Diapositiva
| Grupo | Capturas | Narrativa |
|-------|----------|-----------|
| **Administración y Gobernanza** | `admintracion - gestion de usuarios 00.png` + `admintracion - Roles y Permisos.png` | "Cree usuarios con herencia de datos y permisos granulares por módulo." |
| **Planificación Curricular** | `Libro Digital 00.png` + `Libro Digital 01.png` + `Libro Digital 02.png` | "Del grado a la clase: planificación MINEDUC integrada." |
| **Flujo Evaluativo Completo** | `Evaluaciones 02.png` + `Evaluaciones 03.png` + `Evaluaciones 04.png` | "Desde la clase hasta la nota final: un solo flujo." |
| **Ecosistema de Comunicación** | `Comunicaciones 00.png` + `Comunicaciones 01.png` + `Comunicaciones 02.png` | "Anuncios segmentados, directorio filtrable y mensajería directa." |
| **Biblioteca Integral** | `Biblioteca 00.png` + `Biblioteca 01.png` + `Biblioteca 02.png` | "Control de inventario, préstamos y recursos digitales." |
| **Reportes Consolidados** | `Reportes 01.png` + `Reportes 02.png` | "Del curso al grado: visión táctica y estratégica." |

### Capturas que Cuentan un Flujo de Trabajo (Storytelling de Preventa)

#### Flujo 1: "El Ciclo de una Evaluación"
1. `Evaluaciones 00.png` → El docente elige el grado.
2. `Evaluaciones 01.png` → Selecciona la asignatura.
3. `Evaluaciones 02.png` → Ve la unidad y la clase.
4. `Evaluaciones 03.png` → Crea la evaluación (sumativa, vinculada a clase, con fecha).
5. `Evaluaciones 04.png` → Registra notas y publica.
6. `Calendario 00.png` → La evaluación aparece automáticamente en la agenda.
7. `alumno 00.png` → El alumno la ve en "Próximas Actividades".
8. `informe 00.png` → La nota alimenta el informe oficial de semestre.

#### Flujo 2: "De la Matrícula al Reporte Familiar"
1. `Matricula.png` → Se matricula al estudiante con precarga de datos.
2. `Matricula 01.png` → La ficha queda consolidada.
3. `admintracion - gestion de usuarios 00.png` → Se crea la cuenta de apoderado desde la persona existente.
4. `apoderados 00.jpeg` → El apoderado ve a sus hijos.
5. `Reportes 01.png` → Accede al reporte de asistencia, notas y anotaciones.

#### Flujo 3: "La Comunicación Institucional Cerrada"
1. `Comunicaciones 00.png` → La UTP publica un anuncio para 1° Básico A.
2. `Comunicaciones 01.png` → El apoderado encuentra al profesor jefe en el directorio.
3. `Comunicaciones 02.png` → Le envía un mensaje privado sin salir de la plataforma.

---

## 4. Matriz de Priorización para la Demostración Comercial

| Módulo | Prioridad en Demo | Justificación |
|--------|-------------------|---------------|
| Matrícula + Ficha | **1°** | Diferenciador de profundidad de datos. |
| Libro Digital + Evaluaciones | **2°** | Core pedagógico; donde pasan el 80% del tiempo los docentes. |
| Reportes (Curso + Grado) | **3°** | Lo que el Director quiere ver para decidir la compra. |
| Portal Apoderado + Alumno | **4°** | Impacto emocional; vende la "transparencia". |
| Comunicaciones | **5°** | Cierra el ciclo de engagement familiar. |
| Calendario | **6°** | Complemento visual agradable. |
| Biblioteca CRA | **7°** | Diferenciador en colegios con foco en lectura. |
| Administración/Roles | **8°** | Tema de mesa técnica, no de demo emocional. |

---

**Conclusión del consultor**: Edugest no es un simple "registro de notas". Es una plataforma de **gestión integral del ecosistema escolar** con especial fortaleza en la trazabilidad curricular (Libro Digital → Evaluación → Calendario → Informe oficial) y la transparencia familiar (Apoderado multi-hijo + reportes en tiempo real). Su mayor argumento de venta frente a competidores livianos es la **ficha única del estudiante** y la **generación automática de informes regulatorios chilenos**. Recomiendo estructurar la presentación comercial en torno a los tres flujos de trabajo identificados, no en torno a los módulos aislados.