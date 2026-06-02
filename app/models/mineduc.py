from app.database import db

# ============================================================================
# TABLAS BASE ESTÁNDAR MINEDUC (EDE)
# ============================================================================

class Person(db.Model):
    """Mapea la identidad básica de usuarios (Alumnos, Profesores, Apoderados)"""
    __tablename__ = 'Person'

    PersonId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    FirstName = db.Column(db.String(100), nullable=False)
    MiddleName = db.Column(db.String(100), nullable=True)
    LastName = db.Column(db.String(100), nullable=False)
    SecondLastName = db.Column(db.String(100), nullable=True)
    RefSexId = db.Column(db.Integer, nullable=True)
    Birthdate = db.Column(db.Date, nullable=True)
    RefTribalAffiliationId = db.Column(db.Integer, nullable=True)

    # Relaciones ORM
    identifiers = db.relationship('PersonIdentifier', backref='person', lazy=True, cascade="all, delete-orphan")
    addresses = db.relationship('PersonAddress', backref='person', lazy=True, cascade="all, delete-orphan")
    telephones = db.relationship('PersonTelephone', backref='person', lazy=True, cascade="all, delete-orphan")
    emails = db.relationship('PersonEmailAddress', backref='person', lazy=True, cascade="all, delete-orphan")
    relationships = db.relationship('PersonRelationship', backref='person', lazy=True, cascade="all, delete-orphan",
                                    foreign_keys='PersonRelationship.PersonId')
    health = db.relationship('PersonHealth', backref='person', lazy=True, cascade="all, delete-orphan")
    status = db.relationship('PersonStatus', backref='person', lazy=True, cascade="all, delete-orphan")


class PersonIdentifier(db.Model):
    """Maneja documentos oficiales como RUT o IPE"""
    __tablename__ = 'PersonIdentifier'

    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), primary_key=True)
    Identifier = db.Column(db.String(50), primary_key=True)
    RefPersonIdentificationSystemId = db.Column(db.Integer, nullable=False)


class Organization(db.Model):
    """Estructura escolar: Colegios (RBD), Cursos o Asignaturas específicas"""
    __tablename__ = 'Organization'

    OrganizationId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(255), nullable=False)
    ShortName = db.Column(db.String(50), nullable=True)
    RefOrganizationTypeId = db.Column(db.Integer, nullable=False)

    # Relaciones
    role_assignments = db.relationship('OrganizationPersonRole', backref='organization', lazy=True)
    parent_relationships = db.relationship('OrganizationRelationship', 
                                           backref='child_org', lazy=True,
                                           foreign_keys='OrganizationRelationship.OrganizationId')
    children = db.relationship('OrganizationRelationship',
                               backref='parent_org', lazy=True,
                               foreign_keys='OrganizationRelationship.ParentOrganizationId')


class OrganizationRelationship(db.Model):
    """Jerarquía padre-hijo entre organizaciones (MINEDUC EDE)"""
    __tablename__ = 'OrganizationRelationship'

    OrganizationRelationshipId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    ParentOrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)


class OrganizationIdentifier(db.Model):
    """Identificadores de organización (RBD, etc.)"""
    __tablename__ = 'OrganizationIdentifier'

    OrganizationIdentifierId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    Identifier = db.Column(db.String(50), nullable=False)
    RefOrganizationIdentificationSystemId = db.Column(db.Integer, nullable=False)
    RefOrganizationIdentifierTypeId = db.Column(db.Integer, nullable=True)


class OrganizationPersonRole(db.Model):
    """Vincula a una persona con un curso o asignatura ejerciendo un rol"""
    __tablename__ = 'OrganizationPersonRole'

    OrganizationPersonRoleId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RoleId = db.Column(db.Integer, nullable=False)
    EntryDate = db.Column(db.Date, nullable=True)
    ExitDate = db.Column(db.Date, nullable=True)

    person = db.relationship('Person', backref='roles', lazy=True)


class RoleAttendanceEvent(db.Model):
    """Registro de asistencia oficial"""
    __tablename__ = 'RoleAttendanceEvent'

    RoleAttendanceEventId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=False)
    Date = db.Column(db.Date, nullable=False)
    RefAttendanceEventTypeId = db.Column(db.Integer, nullable=False)
    RefAttendanceStatusId = db.Column(db.Integer, nullable=False)
    RefAbsentAttendanceCategoryId = db.Column(db.Integer, nullable=True)
    RefPresentAttendanceCategoryId = db.Column(db.Integer, nullable=True)
    VirtualIndicator = db.Column(db.Boolean, default=False)
    fileScanBase64 = db.Column(db.Text, nullable=True)
    digitalRandomKey = db.Column(db.String(255), nullable=True)
    Observaciones = db.Column(db.Text, nullable=True)


class OrganizationCalendarSession(db.Model):
    """Leccionario Oficial MINEDUC"""
    __tablename__ = 'OrganizationCalendarSession'

    OrganizationCalendarSessionId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=False)
    BeginDate = db.Column(db.String(10), nullable=False)
    EndDate = db.Column(db.String(10), nullable=False)
    SessionStartTime = db.Column(db.String(8), nullable=True)
    SessionEndTime = db.Column(db.String(8), nullable=True)
    Description = db.Column(db.Text, nullable=True)
    MarkingTermIndicator = db.Column(db.Boolean, default=False)
    SchedulingTermIndicator = db.Column(db.Boolean, default=False)
    PlanId = db.Column(db.Integer, db.ForeignKey('edugest_curriculum_plan.PlanId', ondelete='SET NULL'), nullable=True)


class AssessmentResult(db.Model):
    """Acta final de calificaciones"""
    __tablename__ = 'AssessmentResult'

    AssessmentResultId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=False)
    ScoreValue = db.Column(db.String(20), nullable=False)


class Incident(db.Model):
    """Incidentes, anotaciones y reuniones"""
    __tablename__ = 'Incident'

    IncidentId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    OrganizationId = db.Column(db.Integer, db.ForeignKey('Organization.OrganizationId', ondelete='CASCADE'), nullable=True)
    IncidentDate = db.Column(db.Date, nullable=True)
    IncidentTime = db.Column(db.Time, nullable=True)
    IncidentDescription = db.Column(db.Text, nullable=True)
    RefIncidentBehaviorId = db.Column(db.Integer, nullable=True)


class IncidentPerson(db.Model):
    """Personas involucradas en un incidente"""
    __tablename__ = 'IncidentPerson'

    IncidentPersonId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    IncidentId = db.Column(db.Integer, db.ForeignKey('Incident.IncidentId', ondelete='CASCADE'), nullable=False)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RefIncidentPersonRoleTypeId = db.Column(db.Integer, nullable=True)
    fileScanBase64 = db.Column(db.Text, nullable=True)
    digitalRandomKey = db.Column(db.String(255), nullable=True)
    Date = db.Column(db.Date, nullable=True)


class K12StudentDiscipline(db.Model):
    """Medidas disciplinarias"""
    __tablename__ = 'K12StudentDiscipline'

    K12StudentDisciplineId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    IncidentId = db.Column(db.Integer, db.ForeignKey('Incident.IncidentId', ondelete='CASCADE'), nullable=False)
    OrganizationPersonRoleId = db.Column(db.Integer, db.ForeignKey('OrganizationPersonRole.OrganizationPersonRoleId', ondelete='CASCADE'), nullable=True)


# ============================================================================
# TABLAS DE PERSONA (EXTENSIÓN)
# ============================================================================

class PersonAddress(db.Model):
    """Dirección de persona"""
    __tablename__ = 'PersonAddress'

    PersonAddressId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    StreetNumberAndName = db.Column(db.String(255), nullable=True)
    RefCountyId = db.Column(db.Integer, nullable=True)


class PersonTelephone(db.Model):
    """Teléfono de persona"""
    __tablename__ = 'PersonTelephone'

    PersonTelephoneId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    TelephoneNumber = db.Column(db.String(50), nullable=True)


class PersonEmailAddress(db.Model):
    """Email de persona"""
    __tablename__ = 'PersonEmailAddress'

    PersonEmailAddressId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    EmailAddress = db.Column(db.String(255), nullable=True)


class PersonRelationship(db.Model):
    """Relaciones entre personas (padre, madre, apoderado)"""
    __tablename__ = 'PersonRelationship'

    PersonRelationshipId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RelatedPersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RefPersonRelationshipId = db.Column(db.Integer, nullable=False)


class PersonHealth(db.Model):
    """Datos de salud del estudiante"""
    __tablename__ = 'PersonHealth'

    PersonHealthId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    Description = db.Column(db.Text, nullable=True)


class PersonStatus(db.Model):
    """Estados de la persona (matrícula, retiro, etc.)"""
    __tablename__ = 'PersonStatus'

    PersonStatusId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RefPersonStatusTypeId = db.Column(db.Integer, nullable=True)
    StatusStartDate = db.Column(db.Date, nullable=True)
    StatusEndDate = db.Column(db.Date, nullable=True)
    Description = db.Column(db.Text, nullable=True)
    docNumber = db.Column(db.String(100), nullable=True)
    fileScanBase64 = db.Column(db.Text, nullable=True)
    recordEndDateTime = db.Column(db.Date, nullable=True)


class PersonDegreeOrCertificate(db.Model):
    """Nivel educacional"""
    __tablename__ = 'PersonDegreeOrCertificate'

    PersonDegreeOrCertificateId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RefDegreeOrCertificateTypeId = db.Column(db.Integer, nullable=True)


class PersonBirthplace(db.Model):
    """Lugar de nacimiento"""
    __tablename__ = 'PersonBirthplace'

    PersonBirthplaceId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    RefCountryId = db.Column(db.Integer, nullable=True)


class PersonAllergy(db.Model):
    """Alergias"""
    __tablename__ = 'PersonAllergy'

    PersonAllergyId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    PersonId = db.Column(db.Integer, db.ForeignKey('Person.PersonId', ondelete='CASCADE'), nullable=False)
    AllergyDescription = db.Column(db.String(255), nullable=True)