"""Booking rules, shared by patient self-service and the front desk.

Keeping the validation in one place means a receptionist booking on
behalf of a patient can never bypass a rule the patient flow enforces.
"""

from datetime import date, datetime, time

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.config import AVAILABLE_SLOTS
from app.models import BOOKED, Appointment, Doctor, User, utc_now


def free_slots_for(
    session: Session,
    doctor_id: int,
    appointment_date: date,
) -> list[time]:
    """Clinic slots that are still open for one doctor on one day."""
    today = date.today()
    if appointment_date < today:
        return []

    booked = session.exec(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status == BOOKED,
        )
    ).all()
    taken = {item.appointment_time for item in booked}

    now = datetime.now().time()
    return [
        slot
        for slot in AVAILABLE_SLOTS
        if slot not in taken
        and not (appointment_date == today and slot <= now)
    ]


def get_doctor_or_404(session: Session, doctor_id: int) -> Doctor:
    doctor = session.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )
    return doctor


def create_appointment(
    session: Session,
    *,
    patient: User,
    doctor_id: int,
    appointment_date: date,
    appointment_time: time,
    reason: str = "",
) -> Appointment:
    """Validate every clinic rule, then persist the appointment."""
    today = date.today()
    now = datetime.now().time()

    if appointment_date < today or (
        appointment_date == today and appointment_time <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot book a slot in the past.",
        )

    if appointment_time not in AVAILABLE_SLOTS:
        readable = ", ".join(
            slot.strftime("%H:%M") for slot in AVAILABLE_SLOTS
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "That is not one of the clinic's available time slots. "
                f"Open slots are {readable}."
            ),
        )

    doctor = get_doctor_or_404(session, doctor_id)
    if not doctor.is_accepting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{doctor.name} is not accepting new appointments "
                "at the moment."
            ),
        )

    doctor_clash = session.exec(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status == BOOKED,
        )
    ).first()
    if doctor_clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That doctor slot is already booked.",
        )

    patient_clash = session.exec(
        select(Appointment).where(
            Appointment.patient_id == patient.id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status == BOOKED,
        )
    ).first()
    if patient_clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This patient already has an appointment "
                "at that time."
            ),
        )

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status=BOOKED,
        reason=reason.strip(),
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment


def cancel_appointment(
    session: Session,
    appointment: Appointment,
) -> Appointment:
    if appointment.status != BOOKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This appointment is already {appointment.status} "
                "and cannot be cancelled."
            ),
        )
    appointment.status = "cancelled"
    appointment.updated_at = utc_now()
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment
