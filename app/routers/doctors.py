"""Doctor endpoints: the clinical diary and completing a consultation."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.models import BOOKED, COMPLETED, Appointment, Note, utc_now
from app.schemas import AppointmentPublic, CompleteAppointment, DoctorPublic
from app.security import DbSession, DoctorUser
from app.serializers import (
    appointment_public,
    appointments_public,
    doctor_profile_for_user,
    doctor_public,
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get(
    "/me",
    response_model=DoctorPublic,
    status_code=status.HTTP_200_OK,
)
def my_profile(session: DbSession, user: DoctorUser):
    """The signed in doctor's own clinical profile."""
    return doctor_public(doctor_profile_for_user(session, user))


@router.get(
    "/appointments",
    response_model=list[AppointmentPublic],
    status_code=status.HTTP_200_OK,
)
def my_appointments(
    session: DbSession,
    user: DoctorUser,
    appointment_date: date | None = Query(
        default=None,
        description="Omit to see the doctor's whole diary",
    ),
    status: str | None = Query(
        default=None,
        description="Optional status filter: booked, completed, cancelled",
    ),
):
    profile = doctor_profile_for_user(session, user)

    statement = select(Appointment).where(
        Appointment.doctor_id == profile.id
    )
    if appointment_date is not None:
        statement = statement.where(
            Appointment.appointment_date == appointment_date
        )
    if status:
        statement = statement.where(Appointment.status == status)

    appointments = session.exec(
        statement.order_by(
            Appointment.appointment_date,
            Appointment.appointment_time,
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
    session: DbSession,
    user: DoctorUser,
):
    profile = doctor_profile_for_user(session, user)
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.doctor_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own appointments.",
        )
    return appointment_public(session, appointment)


@router.patch(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def complete_appointment(
    appointment_id: int,
    data: CompleteAppointment,
    session: DbSession,
    user: DoctorUser,
):
    profile = doctor_profile_for_user(session, user)
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.doctor_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete your own appointments.",
        )
    if appointment.status != BOOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only booked appointments can be completed.",
        )

    appointment.status = COMPLETED
    appointment.note = data.note
    appointment.updated_at = utc_now()
    session.add(appointment)
    # The same text is also stored as a Note so the completion summary
    # appears in the patient's note history.
    session.add(
        Note(
            appointment_id=appointment.id,
            doctor_id=profile.id,
            patient_id=appointment.patient_id,
            body=data.note,
        )
    )
    session.commit()
    session.refresh(appointment)
    return appointment_public(session, appointment)
