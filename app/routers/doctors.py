from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.database import get_session
from app.models import (
    Appointment,
    Doctor,
    User,
)
from app.schemas import (
    AppointmentPublic,
    CompleteAppointment,
)
from app.security import require_role
router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)
@router.get(
    "/appointments",
    response_model=list[AppointmentPublic],
    status_code=status.HTTP_200_OK,
)
def my_appointments(
    appointment_date: date,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("doctor"))
    ],
):
    doctor = session.exec(
        select(Doctor).where(
            Doctor.user_id == user.id
        )
    ).first()
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    return session.exec(
        select(Appointment).where(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date
            == appointment_date,
        )
    ).all()
@router.patch(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def complete_appointment(
    appointment_id: int,
    data: CompleteAppointment,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("doctor"))
    ],
):
    if user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can write appointment notes.",
        )
    doctor = session.exec(
        select(Doctor).where(
            Doctor.user_id == user.id
        )
    ).first()
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found.",
        )
    appointment = session.get(
        Appointment,
        appointment_id
    )
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You can only complete "
                "your own appointments."
            ),
        )
    if appointment.status != "booked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Only booked appointments "
                "can be completed."
            ),
        )
    appointment.status = "completed"
    appointment.note = data.note.strip()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    return appointment