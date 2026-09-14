"""Front desk operations: the whole clinic diary, walk-ins and the audit trail.

A receptionist sees every doctor's day at once, books on behalf of patients
who phone or walk in, and is the only role that can read the access log.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import col, func, select

from app import booking
from app.config import AVAILABLE_SLOTS
from app.models import (
    BOOKED,
    CANCELLED,
    COMPLETED,
    PATIENT,
    AccessLog,
    Appointment,
    Doctor,
    User,
)
from app.schemas import (
    AccessLogPublic,
    AppointmentPublic,
    DiaryOverview,
    DoctorPublic,
    ReceptionistBooking,
    UserPublic,
    WalkInPatientCreate,
)
from app.security import DbSession, ReceptionistUser, hash_password
from app.serializers import (
    appointment_public,
    appointments_public,
    doctor_public,
)

router = APIRouter(prefix="/receptionist", tags=["Receptionist"])


@router.get(
    "/diary",
    response_model=list[AppointmentPublic],
    status_code=status.HTTP_200_OK,
)
def whole_diary(
    appointment_date: date,
    session: DbSession,
    user: ReceptionistUser,
    # Named "status" because that is the query key the frontend sends; the
    # fastapi status module is only used in the decorators above.
    status: str | None = Query(
        default=None,
        description="Optional status filter: booked, completed or cancelled.",
    ),
) -> list[AppointmentPublic]:
    statement = select(Appointment).where(
        Appointment.appointment_date == appointment_date
    )
    if status:
        statement = statement.where(
            Appointment.status == status.strip().lower()
        )
    appointments = session.exec(
        statement.order_by(
            col(Appointment.appointment_time),
            col(Appointment.id),
        )
    ).all()
    return appointments_public(session, list(appointments))


@router.get(
    "/overview",
    response_model=DiaryOverview,
    status_code=status.HTTP_200_OK,
)
def diary_overview(
    appointment_date: date,
    session: DbSession,
    user: ReceptionistUser,
) -> DiaryOverview:
    appointments = session.exec(
        select(Appointment).where(
            Appointment.appointment_date == appointment_date
        )
    ).all()

    booked = sum(1 for item in appointments if item.status == BOOKED)
    completed = sum(1 for item in appointments if item.status == COMPLETED)
    cancelled = sum(1 for item in appointments if item.status == CANCELLED)
    doctors_on_duty = len(
        {
            item.doctor_id
            for item in appointments
            if item.status != CANCELLED
        }
    )

    slots_per_doctor = len(AVAILABLE_SLOTS)
    total_doctors = session.exec(select(func.count(col(Doctor.id)))).one()
    capacity = total_doctors * slots_per_doctor
    # An empty clinic has no capacity, so utilisation stays 0 rather than
    # dividing by zero.
    utilisation = (
        min(100, max(0, round(100 * (booked + completed) / capacity)))
        if capacity
        else 0
    )

    return DiaryOverview(
        appointment_date=appointment_date,
        total=len(appointments),
        booked=booked,
        completed=completed,
        cancelled=cancelled,
        doctors_on_duty=doctors_on_duty,
        slots_per_doctor=slots_per_doctor,
        utilisation=utilisation,
    )


@router.post(
    "/appointments",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
def book_for_patient(
    data: ReceptionistBooking,
    session: DbSession,
    user: ReceptionistUser,
) -> AppointmentPublic:
    patient = session.get(User, data.patient_id)
    if patient is None or patient.role != PATIENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found.",
        )

    appointment = booking.create_appointment(
        session,
        patient=patient,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        reason=data.reason,
    )
    return appointment_public(session, appointment)


@router.delete(
    "/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def cancel_any_appointment(
    appointment_id: int,
    session: DbSession,
    user: ReceptionistUser,
) -> AppointmentPublic:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    appointment = booking.cancel_appointment(session, appointment)
    return appointment_public(session, appointment)


@router.post(
    "/walk-in",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_walk_in_patient(
    data: WalkInPatientCreate,
    session: DbSession,
    user: ReceptionistUser,
) -> User:
    existing = session.exec(
        select(User).where(
            func.lower(User.username) == data.username.lower()
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "That username is already taken. "
                "Please choose another one."
            ),
        )

    patient = User(
        username=data.username,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=PATIENT,
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.get(
    "/patients",
    response_model=list[UserPublic],
    status_code=status.HTTP_200_OK,
)
def list_patients(
    session: DbSession,
    user: ReceptionistUser,
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=60,
        description="Match part of a username or full name.",
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[User]:
    statement = select(User).where(User.role == PATIENT)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            col(User.username).ilike(pattern)
            | col(User.full_name).ilike(pattern)
        )
    patients = session.exec(
        statement.order_by(col(User.username)).limit(limit)
    ).all()
    return list(patients)


@router.get(
    "/doctors",
    response_model=list[DoctorPublic],
    status_code=status.HTTP_200_OK,
)
def list_doctors(
    session: DbSession,
    user: ReceptionistUser,
) -> list[DoctorPublic]:
    doctors = session.exec(select(Doctor).order_by(col(Doctor.name))).all()
    return [doctor_public(doctor) for doctor in doctors]


@router.get(
    "/access-logs",
    response_model=list[AccessLogPublic],
    status_code=status.HTTP_200_OK,
)
def list_access_logs(
    session: DbSession,
    user: ReceptionistUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AccessLog]:
    logs = session.exec(
        select(AccessLog)
        .order_by(col(AccessLog.created_at).desc(), col(AccessLog.id).desc())
        .limit(limit)
    ).all()
    return list(logs)
