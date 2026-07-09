from app.database import db
from datetime import datetime
from zoneinfo import ZoneInfo


def obtener_hora_chile():
    """Retorna la fecha y hora actual en zona horaria de Chile Continental"""
    return datetime.now(ZoneInfo("America/Santiago"))


class EdugestCalendarEvent(db.Model):
    """Eventos del calendario académico del establecimiento"""
    __tablename__ = 'edugest_calendar_event'

    EventId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.String(255), nullable=False)
    Description = db.Column(db.Text, nullable=True)
    EventDate = db.Column(db.Date, nullable=False)
    EventType = db.Column(db.String(50), nullable=False, default='Otro')
    # Tipos: 'Evaluacion', 'Vacunacion', 'Taller', 'ActividadExtracurricular',
    #        'Reunion', 'Feriado', 'Otro'
    TargetOrganizationId = db.Column(
        db.Integer,
        db.ForeignKey('Organization.OrganizationId', ondelete='SET NULL'),
        nullable=True
    )  # NULL = global (todo el establecimiento)
    InstrumentId = db.Column(
        db.Integer,
        db.ForeignKey('edugest_assessment_instrument.InstrumentId', ondelete='SET NULL'),
        nullable=True
    )  # Vínculo opcional a evaluación digital
    CreatedBy = db.Column(
        db.Integer,
        db.ForeignKey('Person.PersonId', ondelete='SET NULL'),
        nullable=True
    )
    CreatedAt = db.Column(db.DateTime, default=obtener_hora_chile)