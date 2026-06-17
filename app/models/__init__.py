from app.models.mineduc import (
    Person, PersonIdentifier, Organization, OrganizationRelationship,
    OrganizationIdentifier, OrganizationPersonRole,
    RoleAttendanceEvent, OrganizationCalendarSession,
    AssessmentResult, Incident, IncidentPerson, K12StudentDiscipline,
    PersonAddress, PersonTelephone, PersonEmailAddress,
    PersonRelationship, PersonHealth, PersonStatus,
    PersonDegreeOrCertificate, PersonBirthplace, PersonAllergy
)

from app.models.edugest import (
    EdugestModule, EdugestRolePermission, EdugestOrganizationConfig,
    EdugestCurriculumPlan, EdugestSessionAttendance, EdugestStudentObservation,
    EdugestAssessmentInstrument, EdugestAssessmentQuestion, EdugestQuestionOption,
    EdugestStudentResponse, EdugestBook, EdugestBookLoan,
    EdugestChatMessage, EdugestAnnouncement,
    EdugestStudentEnrollment, EdugestEmergencyContact,
    EdugestStudentHealth, EdugestStudentPIE,
    EdugestPersonRelationshipDetail, EdugestManualGrade,
    EdugestUser
)