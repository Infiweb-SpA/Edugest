from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import db
from app.modules.biblioteca import biblioteca_bp 
from app.models.edugest import EdugestBook, EdugestBookLoan
from app.models.mineduc import (
    Organization, OrganizationPersonRole, OrganizationRelationship,
    Person, PersonIdentifier
)


# ============================================================================
# CATÁLOGO BIBLIOGRÁFICO (CRUD)
# ============================================================================

@biblioteca_bp.route('/')
def index():
    """Dashboard principal de biblioteca"""
    total_libros = EdugestBook.query.count()
    total_prestados = EdugestBookLoan.query.filter(EdugestBookLoan.Status == 'Prestado').count()
    total_atrasados = EdugestBookLoan.query.filter(EdugestBookLoan.Status == 'Atrasado').count()
    
    # Préstamos recientes para mostrar alertas
    prestamos_recientes = EdugestBookLoan.query.order_by(
        EdugestBookLoan.LoanDate.desc()
    ).limit(5).all()
    
    return render_template('biblioteca/index.html',
                           total_libros=total_libros,
                           total_prestados=total_prestados,
                           total_atrasados=total_atrasados,
                           prestamos_recientes=prestamos_recientes)


@biblioteca_bp.route('/catalogo')
def catalogo():
    """Listado paginado del catálogo bibliográfico"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    
    query = EdugestBook.query
    if search:
        query = query.filter(
            db.or_(
                EdugestBook.Title.ilike(f'%{search}%'),
                EdugestBook.Author.ilike(f'%{search}%'),
                EdugestBook.Isbn.ilike(f'%{search}%')
            )
        )
    
    libros = query.order_by(EdugestBook.Title).paginate(
        page=page, per_page=12, error_out=False
    )
    
    return render_template('biblioteca/catalogo.html',
                           libros=libros,
                           search=search)


@biblioteca_bp.route('/libro/nuevo', methods=['GET', 'POST'])
def nuevo_libro():
    """Alta de nuevo libro al catálogo"""
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        autor = request.form.get('autor', '').strip()
        isbn = request.form.get('isbn', '').strip()
        stock_total = int(request.form.get('stock_total', 1))
        is_virtual = 'is_virtual' in request.form
        file_url = request.form.get('file_url', '').strip() if is_virtual else None
        
        # Validar ISBN único
        if isbn and EdugestBook.query.filter_by(Isbn=isbn).first():
            flash('Ya existe un libro con ese ISBN.', 'warning')
            return redirect(url_for('biblioteca.nuevo_libro'))
        
        nuevo = EdugestBook(
            Title=titulo,
            Author=autor,
            Isbn=isbn or f"EDU-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            TotalStock=stock_total,
            AvailableStock=stock_total,
            IsVirtual=is_virtual,
            FileUrl=file_url
        )
        db.session.add(nuevo)
        db.session.commit()
        flash(f'Libro "{titulo}" registrado correctamente.', 'success')
        return redirect(url_for('biblioteca.catalogo'))
    
    return render_template('biblioteca/nuevo_libro.html')


@biblioteca_bp.route('/libro/<int:book_id>/editar', methods=['GET', 'POST'])
def editar_libro(book_id):
    """Edición de libro existente"""
    libro = EdugestBook.query.get_or_404(book_id)
    
    if request.method == 'POST':
        libro.Title = request.form.get('titulo', '').strip()
        libro.Author = request.form.get('autor', '').strip()
        libro.TotalStock = int(request.form.get('stock_total', libro.TotalStock))
        libro.IsVirtual = 'is_virtual' in request.form
        libro.FileUrl = request.form.get('file_url', '').strip() if libro.IsVirtual else None
        
        # Recalcular disponible (no puede ser mayor que total)
        prestados = EdugestBookLoan.query.filter_by(
            BookId=book_id, Status='Prestado'
        ).count()
        libro.AvailableStock = max(0, libro.TotalStock - prestados)
        
        db.session.commit()
        flash('Libro actualizado correctamente.', 'success')
        return redirect(url_for('biblioteca.catalogo'))
    
    return render_template('biblioteca/nuevo_libro.html', libro=libro, editar=True)


@biblioteca_bp.route('/libro/<int:book_id>/eliminar', methods=['POST'])
def eliminar_libro(book_id):
    """Elimina libro si no tiene préstamos activos"""
    libro = EdugestBook.query.get_or_404(book_id)
    
    prestamos_activos = EdugestBookLoan.query.filter_by(
        BookId=book_id, Status='Prestado'
    ).count()
    
    if prestamos_activos > 0:
        flash('No se puede eliminar: tiene préstamos activos.', 'danger')
        return redirect(url_for('biblioteca.catalogo'))
    
    db.session.delete(libro)
    db.session.commit()
    flash('Libro eliminado del catálogo.', 'success')
    return redirect(url_for('biblioteca.catalogo'))


# ============================================================================
# SISTEMA DE PRÉSTAMOS Y DEVOLUCIONES
# ============================================================================

@biblioteca_bp.route('/prestamos')
def prestamos():
    """Gestión de préstamos activos y devoluciones"""
    # Actualizar automáticamente atrasados
    hoy = datetime.now().date()
    atrasados = EdugestBookLoan.query.filter(
        EdugestBookLoan.DueDate < hoy,
        EdugestBookLoan.Status == 'Prestado'
    ).all()
    for p in atrasados:
        p.Status = 'Atrasado'
    db.session.commit()
    
    # Filtros
    estado = request.args.get('estado', 'todos')
    search = request.args.get('q', '').strip()
    
    query = EdugestBookLoan.query.join(EdugestBook)
    
    if estado != 'todos':
        query = query.filter(EdugestBookLoan.Status == estado.capitalize())
    
    if search:
        query = query.join(
            OrganizationPersonRole,
            EdugestBookLoan.OrganizationPersonRoleId == OrganizationPersonRole.OrganizationPersonRoleId
        ).join(Person).filter(
            db.or_(
                Person.FirstName.ilike(f'%{search}%'),
                Person.LastName.ilike(f'%{search}%'),
                EdugestBook.Title.ilike(f'%{search}%')
            )
        )
    
    prestamos_list = query.order_by(EdugestBookLoan.LoanDate.desc()).all()
    
    return render_template('biblioteca/prestamos.html',
                           prestamos=prestamos_list,
                           estado=estado,
                           search=search)


@biblioteca_bp.route('/prestamo/nuevo', methods=['GET', 'POST'])
def nuevo_prestamo():
    """Registrar nuevo préstamo"""
    if request.method == 'POST':
        book_id = int(request.form.get('book_id'))
        persona_id = int(request.form.get('persona_id'))
        dias_prestamo = int(request.form.get('dias_prestamo', 7))
        
        libro = EdugestBook.query.get_or_404(book_id)
        
        # Verificar stock disponible
        if libro.AvailableStock <= 0:
            flash('No hay ejemplares disponibles de este libro.', 'warning')
            return redirect(url_for('biblioteca.nuevo_prestamo'))
        
        # Buscar OrganizationPersonRole del usuario (estudiante o profesor)
        rol = OrganizationPersonRole.query.filter_by(
            PersonId=persona_id
        ).first()
        
        if not rol:
            flash('La persona no tiene un rol asignado en el sistema.', 'warning')
            return redirect(url_for('biblioteca.nuevo_prestamo'))
        
        # Verificar que no tenga préstamo activo del mismo libro
        prestamo_activo = EdugestBookLoan.query.filter_by(
            BookId=book_id,
            OrganizationPersonRoleId=rol.OrganizationPersonRoleId,
            Status='Prestado'
        ).first()
        
        if prestamo_activo:
            flash('Esta persona ya tiene un préstamo activo de este libro.', 'warning')
            return redirect(url_for('biblioteca.nuevo_prestamo'))
        
        hoy = datetime.now().date()
        nuevo = EdugestBookLoan(
            BookId=book_id,
            OrganizationPersonRoleId=rol.OrganizationPersonRoleId,
            LoanDate=hoy,
            DueDate=hoy + timedelta(days=dias_prestamo),
            Status='Prestado'
        )
        
        libro.AvailableStock -= 1
        db.session.add(nuevo)
        db.session.commit()
        
        flash(f'Préstamo registrado. Devolución: {nuevo.DueDate.strftime("%d/%m/%Y")}', 'success')
        return redirect(url_for('biblioteca.prestamos'))
    
    # GET: cargar libros disponibles y personas
    libros_disponibles = EdugestBook.query.filter(EdugestBook.AvailableStock > 0).order_by(EdugestBook.Title).all()
    
    # Buscar estudiantes y profesores
    personas = Person.query.join(
        OrganizationPersonRole,
        Person.PersonId == OrganizationPersonRole.PersonId
    ).filter(
        OrganizationPersonRole.RoleId.in_([6, 21])  # 6=Estudiante, 21=Profesor (ajusta según tus roles)
    ).order_by(Person.LastName).all()
    
    return render_template('biblioteca/nuevo_prestamo.html',
                           libros=libros_disponibles,
                           personas=personas)


@biblioteca_bp.route('/prestamo/<int:loan_id>/devolver', methods=['POST'])
def devolver_prestamo(loan_id):
    """Registrar devolución de libro"""
    prestamo = EdugestBookLoan.query.get_or_404(loan_id)
    
    if prestamo.Status == 'Devuelto':
        flash('Este préstamo ya fue devuelto.', 'info')
        return redirect(url_for('biblioteca.prestamos'))
    
    prestamo.Status = 'Devuelto'
    prestamo.ReturnDate = datetime.now().date()
    
    # Recuperar stock
    libro = EdugestBook.query.get(prestamo.BookId)
    libro.AvailableStock = min(libro.TotalStock, libro.AvailableStock + 1)
    
    db.session.commit()
    flash('Devolución registrada correctamente.', 'success')
    return redirect(url_for('biblioteca.prestamos'))


@biblioteca_bp.route('/prestamo/<int:loan_id>/renovar', methods=['POST'])
def renovar_prestamo(loan_id):
    """Extender fecha de devolución"""
    prestamo = EdugestBookLoan.query.get_or_404(loan_id)
    
    if prestamo.Status != 'Prestado':
        flash('Solo se pueden renovar préstamos activos.', 'warning')
        return redirect(url_for('biblioteca.prestamos'))
    
    dias_extra = int(request.form.get('dias_extra', 7))
    prestamo.DueDate = prestamo.DueDate + timedelta(days=dias_extra)
    prestamo.Status = 'Prestado'  # Asegurar que no quede como Atrasado
    
    db.session.commit()
    flash(f'Préstamo renovado. Nueva fecha: {prestamo.DueDate.strftime("%d/%m/%Y")}', 'success')
    return redirect(url_for('biblioteca.prestamos'))


# ============================================================================
# HISTORIAL Y REPORTES
# ============================================================================

@biblioteca_bp.route('/historial')
def historial():
    """Historial completo de movimientos"""
    page = request.args.get('page', 1, type=int)
    filtro_libro = request.args.get('libro', type=int)
    filtro_persona = request.args.get('persona', type=int)
    
    query = EdugestBookLoan.query
    
    if filtro_libro:
        query = query.filter_by(BookId=filtro_libro)
    if filtro_persona:
        query = query.filter_by(OrganizationPersonRoleId=filtro_persona)
    
    movimientos = query.order_by(EdugestBookLoan.LoanDate.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('biblioteca/historial.html', movimientos=movimientos)


# ============================================================================
# BIBLIOTECAS OPEN SOURCE (Enlaces externos)
# ============================================================================

@biblioteca_bp.route('/recursos-digitales')
def recursos_digitales():
    """Página de recursos digitales open source"""
    return render_template('biblioteca/recursos.html')