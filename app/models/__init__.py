# Importamos la instancia de la base de datos para centralizar accesos
from app.database import db

# Importamos todos los modelos para exponerlos al motor de SQLAlchemy
from app.models.mineduc import (
    Person, PersonIdentifier, Organization, 
    OrganizationPersonRole, RoleAttendanceEvent, 
    OrganizationCalendarSession, AssessmentResult,
    OrganizationRelationship, OrganizationIdentifier,
    PersonAddress, PersonTelephone, PersonEmailAddress,
    PersonRelationship, PersonHealth, PersonStatus,
    PersonDegreeOrCertificate, PersonBirthplace, PersonAllergy,
    Incident, IncidentPerson, K12StudentDiscipline
)
from app.models.edugest import (
    EdugestModule, EdugestRolePermission, EdugestCurriculumPlan,
    EdugestAssessmentInstrument, EdugestAssessmentQuestion, 
    EdugestQuestionOption, EdugestStudentResponse, 
    EdugestBook, EdugestBookLoan, EdugestChatMessage, EdugestAnnouncement
)