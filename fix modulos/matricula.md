# Especificación Técnica: Refactorización y Sincronización MINEDUC/EDE - Módulo de Matrícula

## 📌 Contexto del Proyecto
El módulo de **Matrícula** gestiona el registro y actualización de estudiantes, apoderados y contactos en el sistema escolar. Debe cumplir con el estándar **EDE (Estructura de Datos de Educación)** definido por el **MINEDUC (Chile)**.

Actualmente existen discrepancias entre el almacenamiento en las tablas del modelo oficial MINEDUC (`mineduc.py`) y las tablas auxiliares de la aplicación (`edugest.py`), además de limitaciones en la validación de identificadores extranjeros (IPE) e inconsistencias en la actualización de apoderados.

---

## 🎯 Objetivo General
Refactorizar el controlador (`matricula.py`), los modelos ORM (`mineduc.py`, `edugest.py`) y la vista (`formulario.html`) para garantizar:
1. Soporte completo a estudiantes con **RUT** o **IPE (Identificador Provisorio Escolar)**.
2. Sincronización 1:1 y persistencia limpia de todos los campos en las tablas oficiales EDE/MINEDUC.
3. Gestión robusta de apoderados (Titular, Suplentes) evitando la sobreescritura accidental.
4. Endpoints de búsqueda AJAX y precarga de datos 100% operativos para re-matrículas.

---

## 📂 Archivos Involucrados
* `controllers/matricula.py` (o ubicación correspondiente de la lógica del módulo)
* `models/mineduc.py` (Modelos ORM del estándar MINEDUC)
* `models/edugest.py` (Modelos ORM auxiliares de la aplicación)
* `templates/matricula/formulario.html` (Vista Jinja2 + JS frontend)

---

## 📋 Requerimientos Detallados de Implementación

### 1. Gestión de Identificación Oficial (RUT / IPE / DNI Extranjero)
* **Flexibilizar obligatoriedad**:
  * Modificar la validación de entrada en el servidor. El campo `rut` ya NO debe ser estrictamente obligatorio si se proporciona un `ipe` o pasaporte.
  * `RefPersonIdentificationSystemId = 51` para **RUT**.
  * `RefPersonIdentificationSystemId = 52` para **IPE** (o el código correspondiente según la tabla de catálogo MINEDUC).
* **Validación completa de RUTs**:
  * Aplicar la función `validar_rut()` con algoritmo Módulo 11 tanto al estudiante (si presenta RUT) como a **todos** los apoderados (Titular, Suplente 1, Suplente 2) y contactos de emergencia.

---

### 2. Sincronización Directa con Tablas MINEDUC (EDE)
Asegurar que la persistencia en base de datos registre/actualice las siguientes tablas del esquema MINEDUC:

* **Lugar de Nacimiento (`PersonBirthplace`)**:
  * Habilitar el guardado de `RefCountryId` (País de origen) en la tabla `PersonBirthplace` asociada al `PersonId` del estudiante.
* **Comuna de Residencia (`PersonAddress`)**:
  * Guardar el código territorial de la comuna (`RefCountyId`) en la tabla `PersonAddress`, además de la calle y número (`StreetNumberAndName`).
* **Pueblos Originarios (`Person.RefTribalAffiliationId`)**:
  * Mapear la selección del formulario al atributo `RefTribalAffiliationId` de la entidad `Person`.
* **Teléfono del Estudiante (`PersonTelephone`)**:
  * Crear o actualizar el registro oficial en `PersonTelephone` para el estudiante, no limitándolo únicamente a la tabla auxiliar de Edugest.
* **Historial de Estado del Alumno (`PersonStatus`)**:
  * Al realizar una matriculación o re-matriculación, gestionar adecuadamente los estados anteriores en `PersonStatus` definiendo `StatusEndDate` en registros previos si correspondiera antes de crear un nuevo estado activo (`RefPersonStatusTypeId = 1`).

---

### 3. Lógica y Estructura de Apoderados
* **Tipificación del Vínculo (`PersonRelationship`)**:
  * En lugar de usar un valor hardcodeado genérico (ej. `31`), mapear dinámicamente `RefPersonRelationshipId` segun el parentesco seleccionado (Padre, Madre, Tutor Legal, Abuelo/a, etc.).
* **Asignación Explícita de Rol/Slot**:
  * Eliminar la dependencia de índices por orden de lista (`slot_index`) para prevenir sobreescrituras al actualizar apoderados.
  * Identificar de forma unívoca el rol del apoderado (Apoderado Titular, Suplente 1, Suplente 2) en el guardado.
* **Patrón UPSERT Seguro**:
  * Para teléfonos (`PersonTelephone`), direcciones (`PersonAddress`) y correos (`PersonEmailAddress`) de los apoderados, utilizar un patrón de actualización o inserción basado en identificadores explícitos de la persona (`PersonId`).

---

### 4. Ciclo de Vida del Rol Escolar (`OrganizationPersonRole`)
* Al re-matricular a un estudiante:
  * Desactivar o cerrar únicamente el `OrganizationPersonRole` perteneciente al **periodo lectivo/año académico anterior** estableciendo su `ExitDate`.
  * Crear un nuevo `OrganizationPersonRole` asociado al nuevo curso y año lectivo activo.
  * **No** cerrar roles si la transacción es una simple actualización de datos del periodo vigente.

---

### 5. Endpoints AJAX, Búsqueda y Precarga
* **Búsqueda Extendida (`ajax_buscar_estudiante`)**:
  * Modificar la consulta SQL / SQLAlchemy para buscar estudiantes no solo por RUT (`RefPersonIdentificationSystemId == 51`), sino también por **IPE** (`RefPersonIdentificationSystemId == 52`) y por coincidencia de Nombres/Apellidos.
* **Serialización Completa (`_serialize_estudiante`)**:
  * Asegurar que la respuesta JSON incluya todos los campos requeridos para repoblar el formulario:
    * `pais_nacimiento` / `RefCountryId`
    * `comuna_residencia` / `RefCountyId`
    * `pueblo_originario_id` / `RefTribalAffiliationId`
    * Datos completos de apoderados titular y suplentes.

---

### 6. Interfaz de Usuario y Formulario (HTML / JS)
* **Campos Dinámicos de Identificación**:
  * Implementar un selector (Radio button / Dropdown) para alternar el tipo de documento del estudiante entre **RUT** e **IPE / Documento Extranjero**.
  * Ajustar las máscaras y validaciones JS según la opción seleccionada.
* **Campos Faltantes**:
  * Agregar el input/select para **País / Lugar de Nacimiento**.
  * Asegurar que el selector de **Comuna** envíe el código oficial MINEDUC/CUT.
* **Validaciones Frontend**:
  * Aplicar formateo (puntos y guion) y validación de dígito verificador en tiempo real mediante JavaScript para todos los inputs de RUT presentes en el formulario.

---

## 🛠️ Instrucciones para la IA / Desarrollador
1. Analiza el código actual en `matricula.py`, `mineduc.py`, `edugest.py` y `formulario.html`.
2. Implementa las modificaciones manteniendo el estilo de código existente (PEP 8 para Python, Jinja2/JS limpio para el frontend).
3. Asegúrate de que las consultas ORM utilicen transacciones seguras (`db.session.commit()`, `db.session.rollback()`).
4. Conserva la compatibilidad con los datos previamente registrados en la base de datos.