from app import create_app, db
from app.models.mineduc import OrganizationPersonRole
from sqlalchemy import desc

app = create_app()
with app.app_context():
    estudiantes = db.session.query(OrganizationPersonRole.PersonId).filter(
        OrganizationPersonRole.RoleId == 6,
        OrganizationPersonRole.ExitDate == None
    ).distinct().all()
    
    for (person_id,) in estudiantes:
        roles = OrganizationPersonRole.query.filter(
            OrganizationPersonRole.PersonId == person_id,
            OrganizationPersonRole.RoleId == 6,
            OrganizationPersonRole.ExitDate == None
        ).order_by(desc(OrganizationPersonRole.EntryDate)).all()
        if len(roles) > 1:
            # El primero es el más reciente, los demás se cierran
            for rol in roles[1:]:
                rol.ExitDate = roles[0].EntryDate  # o la fecha actual
            print(f"Cerrados {len(roles)-1} roles antiguos para PersonId {person_id}")
    db.session.commit()