## Sobre limites de tamano de archivos

Puedo manejar archivos de hasta **varias miles de lineas** sin problemas. Mi ventana de contexto es muy amplia (1 millon de tokens), lo que equivale a decenas de miles de lineas de codigo. Para ponerlo en perspectiva practica:

| Tamano | Manejo |
|--------|--------|
| Hasta 500 lineas | Sin ningun problema, lo proceso completo de una vez |
| 500-1500 lineas | Perfecto, puedo revisarlo y corregirlo completo |
| 1500-3000 lineas | Funciona bien, puedo trabajar modulo por funcion |
| 3000-5000 lineas | Funciona, pero puedo sugerirte dividirlo en bloques logicos si hay muchas correcciones |

Asi que los routes.py largos de evaluaciones (~400 lineas), reportes, libro_digital o gestion_usuarios (~280 lineas) no son ningun problema. Mandamelos completos sin preocuparte.

Dicho esto, ahora vamos con las correcciones de Auth.

---

## Modulo Auth — Correcciones aplicadas

### Archivo 1: `app/modules/auth/routes.py`



**Cambios realizados:**

1. **Import de `urlparse`** al inicio (antes no estaba)
2. **`_es_url_segura()`** nueva funcion helper para validar URLs
3. **`_redirect_por_rol()`** centraliza la logica de redireccion por rol, eliminando duplicacion entre `login` y `login` (cuando ya esta autenticado)
4. **`remember=True`** cambiado a `remember = True if request.form.get('remember') else False`
5. **Open redirect** protegido con `_es_url_segura(next_page)` antes de redirigir
6. **Redireccion post-login** usa `_redirect_por_rol()` en vez de if/elif repetido
7. **`listar_usuarios`** redirige a portada con flash en vez de renderizar unauthorized (evita que un admin sin permisos quede pegado en la misma URL)
8. **N+1 resuelto** con `joinedload(EdugestUser.person)` y acceso directo `u.person`
9. **`verificar_escritura`** tiene el `abort` importado al inicio del archivo (antes lo importaba dentro de la funcion)

---

### Archivo 2: `app/templates/auth/login.html`



**Cambios realizados:**

1. **Checkbox "Recordarme"** agregado despues del campo contrasena, con estilos consistentes con el tema dark del login
2. **Flash messages** ahora maneja 4 categorias: `error`, `warning`, `success`, y fallback azul para cualquier otra (antes `success` caia en el else junto con categorias desconocidas)
3. **Caracteres corruptos** reemplazados por su equivalente correcto (emoji de gorro de graduacion, acentos en espanol, etc.)

---

### Archivo 3: `app/templates/auth/unauthorized.html`



**Cambios realizados:**

1. **Boton condicional por rol**: Admin va a `admin.dashboard`, Profesor a `libro_digital.listar_grados`, Director y demas a `portada.bienvenida`
2. **Caso no autenticado**: Si llega a 403 sin sesion (raro pero posible), muestra "Iniciar Sesion" en vez de "Volver al Panel"
3. **Texto del boton adaptado**: "Volver al Panel" para admin, "Volver al Libro Digital" para profesor, "Volver al Inicio" para el resto

---

## Nota importante sobre `EdugestUser.person`

El cambio del N+1 en `listar_usuarios` asume que `EdugestUser` tiene una relacion `person` definida. Revisando el modelo, `EdugestUser` tiene `PersonId` como ForeignKey pero **podria no tener la relacion ORM definida**. Si al probar te da un error como `AttributeError: 'EdugestUser' object has no attribute 'person'`, necesitamos agregar la relacion al modelo en `app/models/edugest.py`:

```python
# Dentro de la clase EdugestUser, agregar:
person = db.relationship('Person', backref='users', lazy=True)
```

---

## Resumen de cambios aplicados

| # | Hallazgo | Archivo | Estado |
|---|----------|---------|--------|
| 1 | S2: `remember=True` hardcodeado | routes.py + login.html | Resuelto |
| 2 | S3: Open redirect via `next` | routes.py | Resuelto |
| 3 | F4: Boton unauthorized siempre a admin | unauthorized.html | Resuelto |
| 4 | A2: Categorias flash inconsistentes | login.html | Resuelto |
| 5 | F3: Encoding corrupto | login.html | Resuelto |
| 6 | P1: N+1 queries en listar_usuarios | routes.py | Resuelto |
| 7 | A1: Verificacion admin inconsistente | routes.py | Resuelto (con redirect + flash) |

## Lo que queda pendiente para Auth (para despues)

| Hallazgo | Razon de postergacion |
|----------|----------------------|
| S1: Sin CSRF | Requiere Flask-WTF global, lo haremos como paso transversal |
| S4: Sin rate limiting | Requiere Flask-Limiter, funcionalidad nueva |
| S6: Sin gestion de contrasenas | Funcionalidad nueva, no fix |
| P2: Imports locales repetidos | Mejora de mantenimiento, bajo riesgo |

---

