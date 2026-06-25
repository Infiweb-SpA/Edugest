"""
Sistema de Control de Acceso Basado en Roles (RBAC) para Edugest
=================================================================
Este modulo proporciona:
- Helper check_permission() para verificar permisos granulares
- Decorador @require_permission() para proteger rutas
- Context processor para Jinja2 (funcion can())
- Funciones de inicializacion de permisos por defecto
"""

from functools import wraps
from flask import session, flash, redirect, url_for
from app.database import db
from app.models.edugest import (
    EdugestSystemRole, EdugestSystemUser, EdugestFeaturePermission, EdugestModule
)

# ============================================================================
# CATALOGO DE FEATURES (codigos unicos de cada funcionalidad)
# ============================================================================

FEATURE_CATALOG = {
    # === MODULO ADMIN / SOPORTE ===
    'admin_dashboard': {
        'name': 'Panel de Administracion',
        'module': 'Admin',
        'description': 'Acceso al dashboard de administracion'
    },
    'admin_roles_crud': {
        'name': 'CRUD de Roles',
        'module': 'Admin',
        'description': 'Crear, editar, eliminar roles del sistema'
    },
    'admin_users_crud': {
        'name': 'CRUD de Usuarios',
        'module': 'Admin',
        'description': 'Crear, editar, eliminar usuarios del sistema'
    },
    'admin_modules_toggle': {
        'name': 'Habilitar/Deshabilitar Modulos',
        'module': 'Admin',
        'description': 'Activar o desactivar modulos completos del sistema'
    },
    'admin_permissions_matrix': {
        'name': 'Matriz de Permisos',
        'module': 'Admin',
        'description': 'Configurar permisos granulares por rol'
    },

    # === MODULO LIBRO DIGITAL ===
    'libro_grados_list': {
        'name': 'Ver Listado de Grados',
        'module': 'Libro Digital',
        'description': 'Acceso a la vista de grados'
    },
    'libro_grados_estado_column': {
        'name': 'Columna Estado en Grados',
        'module': 'Libro Digital',
        'description': 'Ver columna Habilitar/Deshabilitar en listado de grados'
    },
    'libro_asignaturas_list': {
        'name': 'Ver Asignaturas',
        'module': 'Libro Digital',
        'description': 'Acceso a la vista de asignaturas por grado'
    },
    'libro_asignatura_agregar_manual': {
        'name': 'Agregar Asignatura Manual',
        'module': 'Libro Digital',
        'description': 'Boton para crear asignaturas manualmente'
    },
    'libro_planificar': {
        'name': 'Boton Planificar',
        'module': 'Libro Digital',
        'description': 'Acceso al boton Planificar en asignaturas'
    },
    'libro_abrir_libro': {
        'name': 'Boton Abrir Libro',
        'module': 'Libro Digital',
        'description': 'Acceso al boton Abrir Libro en asignaturas'
    },
    'libro_unidades_ver': {
        'name': 'Ver Unidades Curriculares',
        'module': 'Libro Digital',
        'description': 'Acceso al div de Unidades Curriculares'
    },
    'libro_nueva_evaluacion': {
        'name': 'Nueva Evaluacion',
        'module': 'Libro Digital',
        'description': 'Boton para crear nueva evaluacion'
    },
    'libro_registrar_clase': {
        'name': 'Registrar Clase',
        'module': 'Libro Digital',
        'description': 'Acceso al registro de clase y asistencia'
    },
    'libro_subir_material': {
        'name': 'Subir Material',
        'module': 'Libro Digital',
        'description': 'Subir archivos y materiales a clases'
    },
    'libro_preguntas_resultados': {
        'name': 'Preguntas y Resultados',
        'module': 'Libro Digital',
        'description': 'Acceso a preguntas y resultados de evaluaciones'
    },

    # === MODULO EVALUACIONES ===
    'eval_grados_ver': {
        'name': 'Ver Grados (Evaluaciones)',
        'module': 'Evaluaciones',
        'description': 'Acceso a la vista de grados en evaluaciones'
    },
    'eval_asignaturas_ver': {
        'name': 'Ver Asignaturas (Evaluaciones)',
        'module': 'Evaluaciones',
        'description': 'Acceso a la vista de asignaturas en evaluaciones'
    },
    'eval_unidades_ver': {
        'name': 'Ver Unidades (Evaluaciones)',
        'module': 'Evaluaciones',
        'description': 'Acceso a la vista de unidades en evaluaciones'
    },
    'eval_nueva_evaluacion': {
        'name': 'Nueva Evaluacion',
        'module': 'Evaluaciones',
        'description': 'Crear nueva evaluacion/instrumento'
    },
    'eval_nueva_pregunta': {
        'name': 'Nueva Pregunta',
        'module': 'Evaluaciones',
        'description': 'Bloque para agregar nuevas preguntas'
    },
    'eval_simulacion_rapida': {
        'name': 'Columna Simulacion Rapida',
        'module': 'Evaluaciones',
        'description': 'Ver columna de simulacion rapida en resultados'
    },
    'eval_nota_manual': {
        'name': 'Columna Nota Manual',
        'module': 'Evaluaciones',
        'description': 'Ver columna de nota manual en resultados'
    },
    'eval_guardar_notas_manuales': {
        'name': 'Guardar Notas Manuales',
        'module': 'Evaluaciones',
        'description': 'Boton para guardar notas manuales'
    },
    'eval_publicar': {
        'name': 'Publicar Evaluacion',
        'module': 'Evaluaciones',
        'description': 'Cambiar visibilidad de evaluacion'
    },

    # === MODULO COMUNICACIONES ===
    'com_anuncios_ver': {
        'name': 'Ver Anuncios',
        'module': 'Comunicaciones',
        'description': 'Acceso a la vista de anuncios'
    },
    'com_publicar_anuncio': {
        'name': 'Publicar Nuevo Anuncio',
        'module': 'Comunicaciones',
        'description': 'Bloque para publicar nuevos anuncios'
    },
    'com_contactos_ver': {
        'name': 'Ver Contactos',
        'module': 'Comunicaciones',
        'description': 'Acceso a la vista de contactos'
    },
    'com_comunicacion_apoderados': {
        'name': 'Comunicacion con Apoderados',
        'module': 'Comunicaciones',
        'description': 'Enviar mensajes/comunicaciones a apoderados'
    },

    # === MODULO BIBLIOTECA CRA ===
    'bib_dashboard': {
        'name': 'Dashboard Biblioteca',
        'module': 'Biblioteca CRA',
        'description': 'Acceso al panel principal de biblioteca'
    },
    'bib_nuevo_prestamo': {
        'name': 'Nuevo Prestamo',
        'module': 'Biblioteca CRA',
        'description': 'Boton para registrar nuevo prestamo'
    },
    'bib_agregar_libro': {
        'name': 'Agregar Libro',
        'module': 'Biblioteca CRA',
        'description': 'Boton para agregar nuevo libro al catalogo'
    },
    'bib_catalogo_editar': {
        'name': 'Editar Libro (Catalogo)',
        'module': 'Biblioteca CRA',
        'description': 'Boton editar en listado de catalogo'
    },
    'bib_catalogo_eliminar': {
        'name': 'Eliminar Libro (Catalogo)',
        'module': 'Biblioteca CRA',
        'description': 'Boton eliminar en listado de catalogo'
    },
    'bib_prestamos_ver': {
        'name': 'Ver Prestamos',
        'module': 'Biblioteca CRA',
        'description': 'Acceso a la gestion de prestamos'
    },
    'bib_tip_block': {
        'name': 'Bloque Tip/Recomendacion',
        'module': 'Biblioteca CRA',
        'description': 'Ultimo bloque de tips en la interfaz'
    },

    # === MODULO MATRICULA ===
    'mat_listar_estudiantes': {
        'name': 'Listar Estudiantes',
        'module': 'Matricula',
        'description': 'Acceso al listado de estudiantes'
    },
    'mat_nuevo_estudiante': {
        'name': 'Nuevo Estudiante',
        'module': 'Matricula',
        'description': 'Boton para crear nuevo estudiante'
    },
    'mat_columna_acciones': {
        'name': 'Columna Acciones',
        'module': 'Matricula',
        'description': 'Ver columna de acciones en listado'
    },
    'mat_ver_detalle': {
        'name': 'Ver Detalle Estudiante',
        'module': 'Matricula',
        'description': 'Acceso a ficha detallada del estudiante'
    },

    # === MODULO REPORTES ===
    'rep_index': {
        'name': 'Panel de Reportes',
        'module': 'Reportes',
        'description': 'Acceso al indice de reportes'
    },
    'rep_todo_el_grado': {
        'name': 'Boton Todo el Grado',
        'module': 'Reportes',
        'description': 'Generar reporte consolidado del grado'
    },
    'rep_asignaturas_calificaciones': {
        'name': 'Bloque Asignaturas (Calificaciones)',
        'module': 'Reportes',
        'description': 'Ver bloque de asignaturas con calificaciones'
    },
    'rep_configurar_sumativas': {
        'name': 'Configurar Sumativas',
        'module': 'Reportes',
        'description': 'Boton para configurar evaluaciones sumativas'
    },
    'rep_checkbox_sumativas': {
        'name': 'Checkbox Evaluaciones Sumativas',
        'module': 'Reportes',
        'description': 'Checkbox para seleccionar evaluaciones sumativas'
    },
}


# ============================================================================
# HELPERS DE AUTENTICACION Y PERMISOS
# ============================================================================

def get_current_user():
    """Obtiene el usuario actual desde la sesion"""
    if 'user_id' not in session:
        return None
    return EdugestSystemUser.query.get(session['user_id'])


def get_current_user_role():
    """Obtiene el rol del usuario actual"""
    user = get_current_user()
    if not user:
        return None
    return EdugestSystemRole.query.get(user.RoleId)


def get_current_role_id():
    """Obtiene el ID del rol del usuario actual"""
    user = get_current_user()
    return user.RoleId if user else None


def check_permission(feature_code, permission_type='view'):
    """
    Verifica si el usuario actual tiene permiso para una funcionalidad.

    Args:
        feature_code: Codigo de la funcionalidad (ej: 'libro_nueva_evaluacion')
        permission_type: 'view', 'edit', o 'delete'

    Returns:
        bool: True si tiene permiso, False si no
    """
    # Si no hay sesion, no tiene permiso
    role_id = get_current_role_id()
    if role_id is None:
        return False

    # El rol Admin (RoleId=1) siempre tiene todos los permisos
    if role_id == 1:
        return True

    # Buscar permiso en la base de datos
    perm = EdugestFeaturePermission.query.filter_by(
        RoleId=role_id,
        FeatureCode=feature_code
    ).first()

    if not perm:
        return False

    if permission_type == 'view':
        return perm.CanView
    elif permission_type == 'edit':
        return perm.CanEdit
    elif permission_type == 'delete':
        return perm.CanDelete

    return False


def require_permission(feature_code, permission_type='view', redirect_url='admin.dashboard'):
    """
    Decorador para proteger rutas Flask.

    Uso:
        @require_permission('libro_nueva_evaluacion', 'edit')
        def mi_ruta():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_permission(feature_code, permission_type):
                flash('No tienes permisos para acceder a esta funcionalidad.', 'danger')
                return redirect(url_for(redirect_url))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_module_enabled(module_name):
    """Decorador que verifica si un modulo esta habilitado globalmente"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            module = EdugestModule.query.filter_by(ModuleName=module_name).first()
            if not module or not module.IsEnabled:
                flash(f'El modulo {module_name} se encuentra deshabilitado.', 'warning')
                return redirect(url_for('admin.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# INICIALIZACION DE PERMISOS POR DEFECTO
# ============================================================================

def init_default_roles():
    """Crea los roles por defecto del sistema si no existen"""
    roles_default = [
        ('Administrador', 'Control total del sistema'),
        ('Soporte', 'Soporte tecnico y configuracion'),
        ('UTP', 'Unidad Tecnico Pedagogica'),
        ('Profesor', 'Docente del establecimiento'),
        ('Apoderado', 'Padre, madre o tutor legal'),
        ('Estudiante', 'Alumno matriculado'),
    ]

    for name, desc in roles_default:
        if not EdugestSystemRole.query.filter_by(RoleName=name).first():
            db.session.add(EdugestSystemRole(
                RoleName=name,
                RoleDescription=desc,
                IsActive=True
            ))

    db.session.commit()


def init_default_permissions():
    """
    Inicializa los permisos por defecto para cada rol.

    Matriz de permisos:
    - Administrador: Todo (view, edit, delete)
    - Soporte: Todo excepto algunas funciones pedagogicas
    - UTP: Todo lo pedagogico, nada de admin
    - Profesor: Lo pedagogico de sus cursos, lectura en reportes
    - Apoderado: Solo lectura de sus hijos, comunicaciones
    - Estudiante: Solo lectura de sus evaluaciones, biblioteca
    """
    roles = {r.RoleName: r.RoleId for r in EdugestSystemRole.query.all()}

    if not roles:
        return

    # Definir permisos por rol: (view, edit, delete)
    permissions_matrix = {
        'Administrador': 'all',
        'Soporte': {
            'admin_dashboard': (1,1,0), 'admin_roles_crud': (1,1,0), 'admin_users_crud': (1,1,0),
            'admin_modules_toggle': (1,1,0), 'admin_permissions_matrix': (1,1,0),
            'libro_grados_list': (1,0,0), 'libro_grados_estado_column': (1,1,0),
            'libro_asignaturas_list': (1,0,0), 'libro_asignatura_agregar_manual': (1,1,0),
            'libro_planificar': (1,1,0), 'libro_abrir_libro': (1,1,0),
            'libro_unidades_ver': (1,0,0), 'libro_nueva_evaluacion': (1,1,0),
            'libro_registrar_clase': (1,1,0), 'libro_subir_material': (1,1,0),
            'libro_preguntas_resultados': (1,0,0),
            'eval_grados_ver': (1,0,0), 'eval_asignaturas_ver': (1,0,0),
            'eval_unidades_ver': (1,0,0), 'eval_nueva_evaluacion': (1,1,0),
            'eval_nueva_pregunta': (1,1,0), 'eval_simulacion_rapida': (1,0,0),
            'eval_nota_manual': (1,1,0), 'eval_guardar_notas_manuales': (1,1,0),
            'eval_publicar': (1,1,0),
            'com_anuncios_ver': (1,0,0), 'com_publicar_anuncio': (1,1,0),
            'com_contactos_ver': (1,0,0), 'com_comunicacion_apoderados': (1,1,0),
            'bib_dashboard': (1,0,0), 'bib_nuevo_prestamo': (1,1,0),
            'bib_agregar_libro': (1,1,0), 'bib_catalogo_editar': (1,1,0),
            'bib_catalogo_eliminar': (1,0,1), 'bib_prestamos_ver': (1,0,0),
            'bib_tip_block': (1,0,0),
            'mat_listar_estudiantes': (1,0,0), 'mat_nuevo_estudiante': (1,1,0),
            'mat_columna_acciones': (1,0,0), 'mat_ver_detalle': (1,0,0),
            'rep_index': (1,0,0), 'rep_todo_el_grado': (1,0,0),
            'rep_asignaturas_calificaciones': (1,0,0),
            'rep_configurar_sumativas': (1,1,0), 'rep_checkbox_sumativas': (1,1,0),
        },
        'UTP': {
            'libro_grados_list': (1,0,0), 'libro_grados_estado_column': (1,1,0),
            'libro_asignaturas_list': (1,0,0), 'libro_asignatura_agregar_manual': (1,1,0),
            'libro_planificar': (1,1,0), 'libro_abrir_libro': (1,1,0),
            'libro_unidades_ver': (1,0,0), 'libro_nueva_evaluacion': (1,1,0),
            'libro_registrar_clase': (1,1,0), 'libro_subir_material': (1,1,0),
            'libro_preguntas_resultados': (1,0,0),
            'eval_grados_ver': (1,0,0), 'eval_asignaturas_ver': (1,0,0),
            'eval_unidades_ver': (1,0,0), 'eval_nueva_evaluacion': (1,1,0),
            'eval_nueva_pregunta': (1,1,0), 'eval_simulacion_rapida': (1,0,0),
            'eval_nota_manual': (1,1,0), 'eval_guardar_notas_manuales': (1,1,0),
            'eval_publicar': (1,1,0),
            'com_anuncios_ver': (1,0,0), 'com_publicar_anuncio': (1,1,0),
            'com_contactos_ver': (1,0,0), 'com_comunicacion_apoderados': (1,1,0),
            'bib_dashboard': (1,0,0), 'bib_nuevo_prestamo': (1,1,0),
            'bib_agregar_libro': (1,1,0), 'bib_catalogo_editar': (1,1,0),
            'bib_catalogo_eliminar': (1,0,1), 'bib_prestamos_ver': (1,0,0),
            'bib_tip_block': (1,0,0),
            'mat_listar_estudiantes': (1,0,0), 'mat_nuevo_estudiante': (1,1,0),
            'mat_columna_acciones': (1,0,0), 'mat_ver_detalle': (1,0,0),
            'rep_index': (1,0,0), 'rep_todo_el_grado': (1,0,0),
            'rep_asignaturas_calificaciones': (1,0,0),
            'rep_configurar_sumativas': (1,1,0), 'rep_checkbox_sumativas': (1,1,0),
        },
        'Profesor': {
            'libro_grados_list': (1,0,0), 'libro_asignaturas_list': (1,0,0),
            'libro_planificar': (1,1,0), 'libro_abrir_libro': (1,1,0),
            'libro_unidades_ver': (1,0,0), 'libro_nueva_evaluacion': (1,1,0),
            'libro_registrar_clase': (1,1,0), 'libro_subir_material': (1,1,0),
            'libro_preguntas_resultados': (1,0,0),
            'eval_grados_ver': (1,0,0), 'eval_asignaturas_ver': (1,0,0),
            'eval_unidades_ver': (1,0,0), 'eval_nueva_evaluacion': (1,1,0),
            'eval_nueva_pregunta': (1,1,0), 'eval_simulacion_rapida': (1,0,0),
            'eval_nota_manual': (1,1,0), 'eval_guardar_notas_manuales': (1,1,0),
            'eval_publicar': (1,1,0),
            'com_anuncios_ver': (1,0,0), 'com_publicar_anuncio': (1,1,0),
            'com_contactos_ver': (1,0,0), 'com_comunicacion_apoderados': (1,1,0),
            'bib_dashboard': (1,0,0), 'bib_nuevo_prestamo': (1,1,0),
            'bib_prestamos_ver': (1,0,0), 'bib_tip_block': (1,0,0),
            'mat_listar_estudiantes': (1,0,0), 'mat_ver_detalle': (1,0,0),
            'rep_index': (1,0,0), 'rep_asignaturas_calificaciones': (1,0,0),
        },
        'Apoderado': {
            'com_anuncios_ver': (1,0,0), 'com_contactos_ver': (1,0,0),
            'bib_dashboard': (1,0,0), 'bib_prestamos_ver': (1,0,0),
            'mat_ver_detalle': (1,0,0),
            'rep_index': (1,0,0), 'rep_asignaturas_calificaciones': (1,0,0),
        },
        'Estudiante': {
            'eval_grados_ver': (1,0,0), 'eval_asignaturas_ver': (1,0,0),
            'eval_unidades_ver': (1,0,0),
            'com_anuncios_ver': (1,0,0),
            'bib_dashboard': (1,0,0), 'bib_prestamos_ver': (1,0,0),
            'rep_index': (1,0,0), 'rep_asignaturas_calificaciones': (1,0,0),
        },
    }

    for role_name, perms in permissions_matrix.items():
        role_id = roles.get(role_name)
        if not role_id:
            continue

        if perms == 'all':
            for code, info in FEATURE_CATALOG.items():
                existing = EdugestFeaturePermission.query.filter_by(
                    RoleId=role_id, FeatureCode=code
                ).first()
                if not existing:
                    db.session.add(EdugestFeaturePermission(
                        RoleId=role_id, FeatureCode=code, FeatureName=info['name'],
                        ModuleName=info['module'], CanView=True, CanEdit=True, CanDelete=True
                    ))
            continue

        for code, (v, e, d) in perms.items():
            info = FEATURE_CATALOG.get(code)
            if not info:
                continue
            existing = EdugestFeaturePermission.query.filter_by(
                RoleId=role_id, FeatureCode=code
            ).first()
            if not existing:
                db.session.add(EdugestFeaturePermission(
                    RoleId=role_id, FeatureCode=code, FeatureName=info['name'],
                    ModuleName=info['module'], CanView=bool(v), CanEdit=bool(e), CanDelete=bool(d)
                ))

    db.session.commit()


def init_default_admin_user():
    """Crea un usuario admin por defecto si no existe ninguno"""
    from werkzeug.security import generate_password_hash

    if EdugestSystemUser.query.first():
        return

    admin_role = EdugestSystemRole.query.filter_by(RoleName='Administrador').first()
    if not admin_role:
        return

    from app.models.mineduc import Person
    person = Person.query.first()
    if not person:
        person = Person(FirstName='Admin', LastName='Sistema')
        db.session.add(person)
        db.session.flush()

    db.session.add(EdugestSystemUser(
        PersonId=person.PersonId, Username='admin',
        PasswordHash=generate_password_hash('admin123'),
        RoleId=admin_role.RoleId, IsActive=True
    ))
    db.session.commit()


def init_rbac_system():
    """Inicializa todo el sistema RBAC (roles, permisos, usuario admin)"""
    init_default_roles()
    init_default_permissions()
    init_default_admin_user()