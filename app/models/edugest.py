from app.database import db
from datetime import datetime

# ============================================================================
# MÓDULO A: CONFIGURACIÓN Y PERMISOS
# ============================================================================

class EdugestModule(db.Model):
    """Catálogo global para habilitar/deshabilitar módulos de la suite"""
    __tablename__ = 'edugest_module'
    
    ModuleId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ModuleName = db.Column(db.String(100), unique=True, nullable=False)
    IsEnabled = db.Column(db.Boolean, default=True, nullable=False)


class EdugestRolePermission(db.Model):
    """Matriz granular de accesos por Rol (0=No acceso, 1=Lectura, 2=Escritura)"""
    __tablename__ = 'edugest_role_permission'
    
    PermissionId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    RoleId       = db.Column(db.Integer, nullable=False)
    ModuleId     = db.Column(db.Integer, db.ForeignKey('edugest_module.ModuleId', ondelete='CASCADE'), nullable=False)
    PermissionLevel = db.Column(db.Integer, default=0, nullable=False)


class EdugestOrganizationConfig(db.Model):
    """Permite apagar grados sin borrar la data estructural MINEDUC"""
    __tablename__ = 'edugest_organization_config'
    
    ConfigId       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False, unique=True)
    IsActive       = db.Column(db.Boolean, default=True, nullable=False)


# ============================================================================
# MÓDULO B: PLANIFICACIÓN CURRICULAR Y ASISTENCIA POR BLOQUE
# ============================================================================

class EdugestCurriculumPlan(db.Model):
    """CRUD de Unidades vinculado a la Asignatura (RefOrganizationTypeId = 22)"""
    __tablename__ = 'edugest_curriculum_plan'
    
    PlanId      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    UnitTitle   = db.Column(db.String(255), nullable=False)
    Contenido   = db.Column(db.Text, nullable=True)
    Actividad   = db.Column(db.Text, nullable=True)
    DetallesActividad = db.Column(db.Text, nullable=True)
    Objetivo    = db.Column(db.Text, nullable=True)
    CreatedAt   = db.Column(db.DateTime, default=datetime.utcnow)


class EdugestSessionAttendance(db.Model):
    """Asistencia granular con el bloque horario exacto"""
    __tablename__ = 'edugest_session_attendance'
    
    SessionAttendanceId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationCalendarSessionId = db.Column(
        db.Integer,
        db.ForeignKey('OrganizationCalendarSession.OrganizationCalendarSessionId', ondelete='CASCADE'),
        nullable=False
    )
    OrganizationPersonRoleId = db.Column(
        db.Integer,
        db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'),
        nullable=False
    )
    # 1=Presente, 2=Ausente, 3=Atraso
    RefAttendanceStatusId = db.Column(db.Integer, nullable=False)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================================
# MÓDULO C: MOTOR DE EVALUACIONES DIGITALES
# ============================================================================

class EdugestAssessmentInstrument(db.Model):
    """Cabecera de Pruebas, Controles o Cuestionarios vinculados a una planificación"""
    __tablename__ = 'edugest_assessment_instrument'
    
    InstrumentId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 1. Agregamos de manera explícita el OrganizationId que pide tu lógica de rutas
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    # 2. Cambiamos nullable a True para que la evaluación pueda existir sin estar amarrada obligatoriamente a una unidad
    PlanId = db.Column(db.Integer, db.ForeignKey('edugest_curriculum_plan.PlanId', ondelete='CASCADE'), nullable=True)
    Title = db.Column(db.String(255), nullable=False)
    IsDigital = db.Column(db.Boolean, default=True, nullable=False) 
    IsVisible = db.Column(db.Boolean, default=False, nullable=False) 


class EdugestAssessmentQuestion(db.Model):
    """Banco de preguntas dinámico"""
    __tablename__ = 'edugest_assessment_question'
    
    QuestionId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    InstrumentId = db.Column(db.Integer, db.ForeignKey('edugest_assessment_instrument.InstrumentId', ondelete='CASCADE'), nullable=False)
    QuestionText = db.Column(db.Text, nullable=False)
    QuestionType = db.Column(db.String(50), nullable=False) # 'Alternativa', 'Verdadero/Falso', 'Desarrollo'
    Points = db.Column(db.Integer, default=1, nullable=False)

    # NUEVO: Relación automática para acceder a las opciones desde la pregunta
    opciones = db.relationship('EdugestQuestionOption', backref='question', lazy=True, cascade="all, delete-orphan")


class EdugestQuestionOption(db.Model):
    """Opciones de alternativas para el algoritmo de auto-corrección"""
    __tablename__ = 'edugest_question_option'
    
    OptionId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    QuestionId = db.Column(db.Integer, db.ForeignKey('edugest_assessment_question.QuestionId', ondelete='CASCADE'), nullable=False)
    OptionText = db.Column(db.String(255), nullable=False)
    IsCorrect = db.Column(db.Boolean, default=False, nullable=False)


class EdugestStudentResponse(db.Model):
    """Almacena los intentos e ingresos de respuestas por estudiante"""
    __tablename__ = 'edugest_student_response'
    
    ResponseId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=False)
    QuestionId = db.Column(db.Integer, db.ForeignKey('edugest_assessment_question.QuestionId', ondelete='CASCADE'), nullable=False)
    SelectedOptionId = db.Column(db.Integer, db.ForeignKey('edugest_question_option.OptionId', ondelete='CASCADE'), nullable=True)
    TextResponse = db.Column(db.Text, nullable=True) 
    ScoreEarned = db.Column(db.Float, nullable=True)


# ============================================================================
# MÓDULO D: BIBLIOTECA ESCOLAR (CRA)
# ============================================================================

class EdugestBook(db.Model):
    """Inventario de textos de estudio y e-books"""
    __tablename__ = 'edugest_book'
    
    BookId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.String(255), nullable=False)
    Author = db.Column(db.String(255), nullable=False)
    Isbn = db.Column(db.String(50), unique=True, nullable=False)
    TotalStock = db.Column(db.Integer, default=0, nullable=False)
    AvailableStock = db.Column(db.Integer, default=0, nullable=False)
    IsVirtual = db.Column(db.Boolean, default=False, nullable=False)
    FileUrl = db.Column(db.String(500), nullable=True)


class EdugestBookLoan(db.Model):
    """Control de flujos y atrasos de préstamos bibliotecarios"""
    __tablename__ = 'edugest_book_loan'
    
    LoanId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    BookId = db.Column(db.Integer, db.ForeignKey('edugest_book.BookId', ondelete='CASCADE'), nullable=False)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=False)
    LoanDate = db.Column(db.Date, nullable=False)
    DueDate = db.Column(db.Date, nullable=False)
    ReturnDate = db.Column(db.Date, nullable=True)
    Status = db.Column(db.String(50), default='Prestado', nullable=False) 


# ============================================================================
# MÓDULO E: COMUNICACIONES Y COMUNIDAD
# ============================================================================

class EdugestChatMessage(db.Model):
    """Mensajes bidireccionales del chat interno de la plataforma"""
    __tablename__ = 'edugest_chat_message'
    
    MessageId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    SenderPersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    ReceiverPersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    MessageText = db.Column(db.Text, nullable=False)
    SentAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    IsRead = db.Column(db.Boolean, default=False, nullable=False)


class EdugestAnnouncement(db.Model):
    """Muro público / Diario mural de avisos oficiales de la escuela o curso"""
    __tablename__ = 'edugest_announcement'
    
    AnnouncementId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    SenderPersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    TargetOrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=True) 
    Title = db.Column(db.String(255), nullable=False)
    Content = db.Column(db.Text, nullable=False)
    AttachmentUrl = db.Column(db.String(500), nullable=True)
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)