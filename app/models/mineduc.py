from app.database import db

class Person(db.Model):
    """Mapea la identidad básica de usuarios (Alumnos, Profesores, Apoderados)"""
    __tablename__ = 'Person'
    
    PersonId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    FirstName = db.Column(db.String(100), nullable=False)
    MiddleName = db.Column(db.String(100), nullable=True)
    LastName = db.Column(db.String(100), nullable=False)
    SecondLastName = db.Column(db.String(100), nullable=True)
    RefSexId = db.Column(db.Integer, nullable=True)

    # Relaciones ORM para consultas ágiles en plantillas
    identifiers = db.relationship('PersonIdentifier', backref='person', lazy=True, cascade="all, delete-orphan")
    # NOTA: La relación 'roles' se define desde OrganizationPersonRole con backref


class PersonIdentifier(db.Model):
    """Maneja documentos oficiales como RUT o IPE"""
    __tablename__ = 'PersonIdentifier'
    
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), primary_key=True)
    Identifier = db.Column(db.String(50), primary_key=True)  # Composite PK común en EDE
    RefPersonIdentificationSystemId = db.Column(db.Integer, nullable=False) # 51=RUT, 52=IPE


class Organization(db.Model):
    """Estructura escolar: Colegios (RBD), Cursos o Asignaturas específicas"""
    __tablename__ = 'Organization'
    
    OrganizationId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(255), nullable=False)
    ShortName = db.Column(db.String(50), nullable=True)
    RefOrganizationTypeId = db.Column(db.Integer, nullable=False) # 10=Colegio, 21=Curso, 22=Asignatura


class OrganizationPersonRole(db.Model):
    """Vincula a una persona con un curso o asignatura ejerciendo un rol (Matrícula/Carga horaria)"""
    __tablename__ = 'OrganizationPersonRole'
    
    OrganizationPersonRoleId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RoleId = db.Column(db.Integer, nullable=False) # 6=Estudiante, 17=Apoderado, X=Profesor
    EntryDate = db.Column(db.Date, nullable=True)
    ExitDate = db.Column(db.Date, nullable=True)

    # Relaciones ORM - backref crea 'roles' en Person y 'role_assignments' en Organization
    person = db.relationship('Person', backref='roles', lazy=True)
    organization = db.relationship('Organization', backref='role_assignments', lazy=True)


class RoleAttendanceEvent(db.Model):
    """Registro de asistencia oficial diaria o por bloques por estudiante"""
    __tablename__ = 'RoleAttendanceEvent'
    
    RoleAttendanceEventId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=False)
    Date = db.Column(db.Date, nullable=False)
    RefAttendanceEventTypeId = db.Column(db.Integer, nullable=False) # 1=Por clase, 2=Diaria
    RefAttendanceStatusId = db.Column(db.Integer, nullable=False)    # 1=Presente, 2=Ausente
    fileScanBase64 = db.Column(db.Text, nullable=True)  
    digitalRandomKey = db.Column(db.String(255), nullable=True) 


class OrganizationCalendarSession(db.Model):
    """Leccionario Oficial MINEDUC: Bloques horarios dictados en la asignatura"""
    __tablename__ = 'OrganizationCalendarSession'
    
    OrganizationCalendarSessionId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    BeginDate = db.Column(db.String(10), nullable=False)  # ISO8601 YYYY-MM-DD
    EndDate = db.Column(db.String(10), nullable=False)
    SessionStartTime = db.Column(db.String(8), nullable=True) # HH:MM:SS
    SessionEndTime = db.Column(db.String(8), nullable=True)
    Description = db.Column(db.Text, nullable=True)       # Contenido del Leccionario
    MarkingTermIndicator = db.Column(db.Boolean, default=False, nullable=False)   
    SchedulingTermIndicator = db.Column(db.Boolean, default=False, nullable=False) 
    
    # EXTENSIÓN EDUGEST: Enlace dinámico no obligatorio hacia la planificación anual
    PlanId = db.Column(db.Integer, db.ForeignKey('edugest_curriculum_plan.PlanId', ondelete='SET NULL'), nullable=True)


class AssessmentResult(db.Model):
    """Acta final de calificaciones oficiales"""
    __tablename__ = 'AssessmentResult'
    
    AssessmentResultId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=False)
    ScoreValue = db.Column(db.String(20), nullable=False)