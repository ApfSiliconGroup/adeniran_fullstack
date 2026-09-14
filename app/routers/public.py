"""Open endpoints, no token required.

The marketing landing page, the About page and the signup screen all call
these before anyone has signed in, so nothing here touches the current
user and nothing here can raise on an empty database.
"""

from fastapi import APIRouter, Query, status
from sqlmodel import Session, func, select

from app.config import AVAILABLE_SLOTS, settings
from app.models import COMPLETED, Appointment, Doctor, User, utc_now
from app.schemas import ClinicStats, DoctorPublic
from app.security import DbSession
from app.serializers import doctor_public

router = APIRouter(tags=["Public"])


def _distinct_specialities(session: Session) -> list[str]:
    rows = session.exec(select(Doctor.speciality).distinct()).all()
    return sorted({row for row in rows if row})


@router.get("/health", status_code=status.HTTP_200_OK)
def health(session: DbSession) -> dict:
    """Liveness probe for the hosting platform.

    A database outage is reported in the payload rather than as a 5xx, so
    a platform health check does not flap the whole deployment.
    """
    try:
        session.exec(select(func.count(User.id))).one()
        database = "reachable"
    except Exception:
        database = "unreachable"

    return {
        "status": "ok",
        "database": database,
        "version": settings.version,
        "time": utc_now().isoformat(),
    }


@router.get(
    "/public/doctors",
    response_model=list[DoctorPublic],
    status_code=status.HTTP_200_OK,
)
def list_public_doctors(
    session: DbSession,
    speciality: str | None = Query(
        default=None,
        min_length=2,
        max_length=60,
        description="Omit to list every doctor in the clinic",
    ),
):
    """The clinic's doctors, optionally narrowed to one speciality."""
    statement = select(Doctor)
    if speciality:
        statement = statement.where(Doctor.speciality == speciality)

    doctors = session.exec(statement.order_by(Doctor.name)).all()
    return [doctor_public(doctor) for doctor in doctors]


@router.get(
    "/public/specialities",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
def list_public_specialities(session: DbSession) -> list[str]:
    """Every speciality the clinic currently covers, sorted."""
    return _distinct_specialities(session)


@router.get(
    "/public/stats",
    response_model=ClinicStats,
    status_code=status.HTTP_200_OK,
)
def public_stats(session: DbSession):
    """Headline numbers for the landing page."""
    doctors = session.exec(select(func.count(Doctor.id))).one()
    consultations_completed = session.exec(
        select(func.count(Appointment.id)).where(
            Appointment.status == COMPLETED
        )
    ).one()

    return ClinicStats(
        doctors=doctors,
        specialities=_distinct_specialities(session),
        slots_per_day=len(AVAILABLE_SLOTS),
        consultations_completed=consultations_completed,
    )
