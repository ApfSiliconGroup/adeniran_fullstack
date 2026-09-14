"""Patient endpoints: browse doctors, book a slot and manage own diary.

Every clinic rule lives in ``app.booking`` so a patient booking and a front
desk booking can never drift apart. This router only handles ownership
checks, filtering and the access log audit trail.
"""

from datetime import date, time

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
    Query,
    status,
)
from sqlmodel import Session, col, desc, select

from app import booking
from app.database import engine
from app.models import PATIENT, AccessLog, Appointment, Doctor, User
from app.schemas import (
    AppointmentCreate,
    AppointmentPublic,
    DoctorPublic,
    PatientRegister,
    UserPublic,
)
from app.security import DbSession, PatientUser, hash_password
from app.serializers import (
    appointment_public,
    appointments_public,
    doctor_public,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


def write_access_log(
    user_id: int,
    appointment_id: int,
    action: str = "patient record opened",
) -> None:
    """Record an audit row after the response has already been sent.

    This runs as a BackgroundTasks callback, by which point the request
    session is closed, so it opens a session of its own.
    """
    with Session(engine) as session:
        session.add(
            AccessLog(
                user_id=user_id,
                appointment_id=appointment_id,
                action=action,
            )
        )
        session.commit()


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_patient(data: PatientRegister, session: DbSession):
    """Kept for backwards compatibility with the original API.

    New clients should call ``POST /auth/register``, which also returns a
    token; this route only creates the account.
    """
    existing = session.exec(
        select(User).where(User.username == data.username)
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
    "/doctors",
    response_model=list[DoctorPublic],
    status_code=status.HTTP_200_OK,
)
def list_doctors(
    session: DbSession,
    user: PatientUser,
    speciality: str | None = Query(
        default=None,
        min_length=2,
        max_length=60,
        description="Optional speciality filter, for example Cardiology",
    ),
):
    """The clinic's doctors, alphabetical, optionally by speciality."""
    statement = select(Doctor)
    if speciality:
        statement = statement.where(Doctor.speciality == speciality)

    doctors = session.exec(statement.order_by(Doctor.name)).all()
    return [doctor_public(doctor) for doctor in doctors]


@router.get(
    "/doctors/{doctor_id}/free-slots",
    response_model=list[time],
    status_code=status.HTTP_200_OK,
)
def free_slots(
    doctor_id: int,
    appointment_date: date,
    session: DbSession,
    user: PatientUser,
):
    """Clinic slots still open for one doctor on one day."""
    booking.get_doctor_or_404(session, doctor_id)
    return booking.free_slots_for(session, doctor_id, appointment_date)


@router.post(
    "/appointments",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    data: AppointmentCreate,
    session: DbSession,
    user: PatientUser,
):
    """Book a slot for the signed in patient."""
    appointment = booking.create_appointment(
        session,
        patient=user,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        reason=data.reason,
    )
    return appointment_public(session, appointment)


@router.get(
    "/appointments",
    response_model=list[AppointmentPublic],
    status_code=status.HTTP_200_OK,
)
def list_my_appointments(
    session: DbSession,
    user: PatientUser,
    status: str | None = Query(
        default=None,
        description="booked, completed or cancelled",
    ),
):
    """The signed in patient's own appointments, newest first."""
    statement = select(Appointment).where(Appointment.patient_id == user.id)
    if status:
        statement = statement.where(Appointment.status == status)

    appointments = session.exec(
        statement.order_by(
            desc(col(Appointment.appointment_date)),
            desc(col(Appointment.appointment_time)),
        )
    ).all()
    return appointments_public(session, list(appointments))


@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def get_my_appointment(
    appointment_id: int,
    background_tasks: BackgroundTasks,
    session: DbSession,
    user: PatientUser,
):
    """One appointment, with the read recorded in the access log."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.patient_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view another patient's appointment.",
        )

    background_tasks.add_task(write_access_log, user.id, appointment.id)
    return appointment_public(session, appointment)


@router.delete(
    "/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def cancel_my_appointment(
    appointment_id: int,
    background_tasks: BackgroundTasks,
    session: DbSession,
    user: PatientUser,
):
    """Cancel one of the signed in patient's own booked appointments."""
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.patient_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own appointment.",
        )

    cancelled = booking.cancel_appointment(session, appointment)
    background_tasks.add_task(
        write_access_log,
        user.id,
        cancelled.id,
        action="patient cancelled appointment",
    )
    return appointment_public(session, cancelled)
