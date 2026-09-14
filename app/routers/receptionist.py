from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.database import get_session
from app.models import (
    Appointment,
    User,
)
from app.schemas import (
    AppointmentPublic,
    UserPublic,
    WalkInPatientCreate,
)
from app.security import (
    hash_password,
    require_role,
)
router = APIRouter(
    prefix="/receptionist",
    tags=["Receptionist"],
)
@router.get(
    "/diary",
    response_model=list[AppointmentPublic],
    status_code=status.HTTP_200_OK,
)
def whole_diary(
    appointment_date: date,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("receptionist"))
    ],
):
    return session.exec(
        select(Appointment).where(
            Appointment.appointment_date
            == appointment_date
        )
    ).all()
@router.delete(
    "/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def cancel_any_appointment(
    appointment_id: int,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("receptionist"))
    ],
):
    appointment = session.get(
        Appointment,
        appointment_id
    )
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found.",
        )
    if appointment.status != "booked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This appointment "
                "cannot be cancelled."
            ),
        )
    appointment.status = "cancelled"
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment
@router.post(
    "/walk-in",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_walk_in_patient(
    data: WalkInPatientCreate,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("receptionist"))
    ],
):
    existing_user = session.exec(
        select(User).where(
            User.username == data.username
        )
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists.",
        )
    patient = User(
        username=data.username,
        password_hash=hash_password(
            data.password
        ),
        role="patient",
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient