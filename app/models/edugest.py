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
    QuestionType = db.Column(db.String(50), nullable=False)  # 'Alternativa', 'VerdaderoFalso', 'Desarrollo', 'RelacionColumnas', 'Completar'
    Points = db.Column(db.Integer, default=1, nullable=False)
    ImageUrl = db.Column(db.String(500), nullable=True)  # <-- NUEVO: imagen opcional
    
    opciones = db.relationship('EdugestQuestionOption', backref='question', lazy=True, cascade="all, delete-orphan")


class EdugestQuestionOption(db.Model):
    """Opciones para Alternativa, VF, Relación y Completar"""
    __tablename__ = 'edugest_question_option'
    
    OptionId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    QuestionId = db.Column(db.Integer, db.ForeignKey('edugest_assessment_question.QuestionId', ondelete='CASCADE'), nullable=False)
    OptionText = db.Column(db.String(255), nullable=False)      # Texto mostrado (ej: "Verdadero", "Opción A")
    MatchText = db.Column(db.String(255), nullable=True)       # <-- NUEVO: para Relación de columnas (término a emparejar)
    IsCorrect = db.Column(db.Boolean, default=False, nullable=False)
    OrderIndex = db.Column(db.Integer, default=0, nullable=True) # <-- NUEVO: orden para completar o relación


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
    
    # ← AGREGAR ESTA RELACIÓN
    loans = db.relationship('EdugestBookLoan', backref='book', lazy=True, cascade="all, delete-orphan")


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
    
    # ← AGREGAR ESTA RELACIÓN (opcional pero útil para acceder a la persona)
    person_role = db.relationship('OrganizationPersonRole', backref='book_loans', lazy=True)


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

# ============================================================================
# MÓDULO F: EXTENSIÓN DE MATRÍCULA (Datos adicionales MINEDUC)
# ============================================================================

class EdugestStudentEnrollment(db.Model):
    """Datos adicionales de matrícula del estudiante (1:1 con Person)"""
    __tablename__ = 'edugest_student_enrollment'
    
    EnrollmentId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Datos personales adicionales
    Nacionalidad = db.Column(db.String(100), nullable=True)
    PaisOrigen = db.Column(db.String(100), nullable=True)
    ComunaResidencia = db.Column(db.String(100), nullable=True)
    RegionResidencia = db.Column(db.String(100), nullable=True)
    EmailEstudiante = db.Column(db.String(255), nullable=True)
    TelefonoEstudiante = db.Column(db.String(50), nullable=True)
    
    # Información académica
    ColegioProcedencia = db.Column(db.String(255), nullable=True)
    ComunaColegioAnterior = db.Column(db.String(100), nullable=True)
    RegionColegioAnterior = db.Column(db.String(100), nullable=True)
    UltimoCursoAprobado = db.Column(db.String(50), nullable=True)
    AnioUltimoCursoAprobado = db.Column(db.Integer, nullable=True)
    MotivoTraslado = db.Column(db.Text, nullable=True)
    FechaIngresoEstablecimiento = db.Column(db.Date, nullable=True)
    
    # Flag para mostrar/ocultar info académica en UI
    EsNuevoEnEstablecimiento = db.Column(db.Boolean, default=True, nullable=False)
    
    # Información socioeconómica
    NivelEducacionalMadre = db.Column(db.Integer, nullable=True)
    NivelEducacionalPadre = db.Column(db.Integer, nullable=True)
    NivelEducacionalApoderado = db.Column(db.Integer, nullable=True)
    IngresoFamiliar = db.Column(db.String(50), nullable=True)
    NumIntegrantesHogar = db.Column(db.Integer, nullable=True)
    
    # Información SEP
    AlumnoPrioritario = db.Column(db.Boolean, default=False, nullable=False)
    AlumnoPreferente = db.Column(db.Boolean, default=False, nullable=False)
    BeneficiarioSEP = db.Column(db.Boolean, default=False, nullable=False)
    
    # Información cultural
    PertenecePuebloOriginario = db.Column(db.Boolean, default=False, nullable=False)
    PuebloOriginario = db.Column(db.String(100), nullable=True)
    HablaLenguaIndigena = db.Column(db.Boolean, default=False, nullable=False)
    LenguaIndigena = db.Column(db.String(100), nullable=True)
    NacionalidadExtranjera = db.Column(db.String(100), nullable=True)
    
    # Transporte escolar
    MedioTransporte = db.Column(db.String(100), nullable=True)
    UtilizaTransporteEscolar = db.Column(db.Boolean, default=False, nullable=False)
    NombreTransportista = db.Column(db.String(255), nullable=True)
    TelefonoTransportista = db.Column(db.String(50), nullable=True)
    TiempoEstimadoTraslado = db.Column(db.String(50), nullable=True)
    
    # Autorizaciones
    AutorizaFotografias = db.Column(db.Boolean, default=False, nullable=False)
    AutorizaRedesSociales = db.Column(db.Boolean, default=False, nullable=False)
    AutorizaSalidasPedagogicas = db.Column(db.Boolean, default=False, nullable=False)
    AutorizaTrasladoCentroAsistencial = db.Column(db.Boolean, default=False, nullable=False)
    AutorizaAtencionMedicaUrgencia = db.Column(db.Boolean, default=False, nullable=False)
    
    # Documentación entregada
    EntregaCertificadoNacimiento = db.Column(db.Boolean, default=False, nullable=False)
    EntregaCertificadoAnualEstudios = db.Column(db.Boolean, default=False, nullable=False)
    EntregaInformePersonalidad = db.Column(db.Boolean, default=False, nullable=False)
    EntregaInformeNotas = db.Column(db.Boolean, default=False, nullable=False)
    EntregaInformePIE = db.Column(db.Boolean, default=False, nullable=False)
    EntregaFotocopiaRUNEstudiante = db.Column(db.Boolean, default=False, nullable=False)
    EntregaFotocopiaRUNApoderado = db.Column(db.Boolean, default=False, nullable=False)
    EntregaComprobanteDomicilio = db.Column(db.Boolean, default=False, nullable=False)
    EntregaFichaMedica = db.Column(db.Boolean, default=False, nullable=False)
    
    # Observaciones generales
    ObservacionesAcademicas = db.Column(db.Text, nullable=True)
    ObservacionesMedicas = db.Column(db.Text, nullable=True)
    ObservacionesFamiliares = db.Column(db.Text, nullable=True)
    ComentariosEstablecimiento = db.Column(db.Text, nullable=True)


class EdugestEmergencyContact(db.Model):
    """Contactos de emergencia del estudiante (1:N) — ahora con misma estructura que apoderado"""
    __tablename__ = 'edugest_emergency_contact'
    
    ContactId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    Orden = db.Column(db.Integer, nullable=False, default=1)
    
    # Campos individuales (igual que apoderado)
    FirstName = db.Column(db.String(100), nullable=True)
    LastName = db.Column(db.String(100), nullable=True)
    SecondLastName = db.Column(db.String(100), nullable=True)
    NombreCompleto = db.Column(db.String(255), nullable=True)  # Legacy / computado
    RUN = db.Column(db.String(20), nullable=True)
    Parentesco = db.Column(db.String(50), nullable=True)
    TelefonoPrincipal = db.Column(db.String(50), nullable=True)
    TelefonoAlternativo = db.Column(db.String(50), nullable=True)
    Email = db.Column(db.String(255), nullable=True)
    ProfesionOcupacion = db.Column(db.String(255), nullable=True)
    NivelEducacional = db.Column(db.Integer, nullable=True)


class EdugestStudentHealth(db.Model):
    """Información médica detallada del estudiante (1:1)"""
    __tablename__ = 'edugest_student_health'
    
    HealthId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False, unique=True)
    
    GrupoSanguineo = db.Column(db.String(10), nullable=True)
    SistemaSalud = db.Column(db.String(20), nullable=True)
    EnfermedadesPermanentes = db.Column(db.Text, nullable=True)
    Alergias = db.Column(db.Text, nullable=True)
    MedicamentosPermanentes = db.Column(db.Text, nullable=True)
    RestriccionesAlimentarias = db.Column(db.Text, nullable=True)
    NecesidadesMedicasEspeciales = db.Column(db.Text, nullable=True)
    ObservacionesMedicasDetalle = db.Column(db.Text, nullable=True)
    CentroSaludHabitual = db.Column(db.String(255), nullable=True)
    MedicoTratante = db.Column(db.String(255), nullable=True)
    TelefonoMedicoTratante = db.Column(db.String(50), nullable=True)


class EdugestStudentPIE(db.Model):
    """Programa de Integración Escolar (1:1)"""
    __tablename__ = 'edugest_student_pie'
    
    PieId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False, unique=True)
    
    PertenecePIE = db.Column(db.Boolean, default=False, nullable=False)
    DiagnosticoPIE = db.Column(db.Text, nullable=True)
    FechaDiagnostico = db.Column(db.Date, nullable=True)
    ProfesionalTratante = db.Column(db.String(255), nullable=True)
    ObservacionesPIE = db.Column(db.Text, nullable=True)


class EdugestPersonRelationshipDetail(db.Model):
    """Detalles adicionales de la relación apoderado-estudiante (1:1 con PersonRelationship)"""
    __tablename__ = 'edugest_person_relationship_detail'
    
    DetailId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonRelationshipId = db.Column(db.Integer, db.ForeignKey('PersonRelationship.PersonRelationshipId', ondelete='CASCADE'), nullable=False, unique=True)
    
    Parentesco = db.Column(db.String(50), nullable=True)
    ProfesionOcupacion = db.Column(db.String(255), nullable=True)
    LugarTrabajo = db.Column(db.String(255), nullable=True)
    Direccion = db.Column(db.Text, nullable=True)
    CorreoElectronico = db.Column(db.String(255), nullable=True)