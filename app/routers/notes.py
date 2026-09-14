"""Consultation notes.

A doctor writes a note against one of their own appointments, addressed to
the patient on that appointment. The patient reads it, the author can
correct or withdraw it, and the front desk can see that a note exists
without ever reading the clinical text.
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Session, col, desc, select

from app import serializers
from app.models import (
    CANCELLED,
    DOCTOR,
    PATIENT,
    RECEPTIONIST,
    Appointment,
    Note,
    utc_now,
)
from app.schemas import Message, NoteCreate, NotePublic, NoteUpdate
from app.security import CurrentUser, DbSession, DoctorUser

router = APIRouter(prefix="/notes", tags=["Notes"])

# Receptionists need the diary, never the clinical text.
HIDDEN_BODY = "Clinical note hidden from front desk staff."


def _get_appointment_or_404(
    session: Session,
    appointment_id: int,
) -> Appointment:
    appointment = session.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That appointment could not be found.",
        )
    return appointment


def _get_note_or_404(session: Session, note_id: int) -> Note:
    note = session.get(Note, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That consultation note could not be found.",
        )
    return note


@router.post(
    "/appointments/{appointment_id}",
    response_model=NotePublic,
    status_code=status.HTTP_201_CREATED,
)
def write_note(
    appointment_id: int,
    data: NoteCreate,
    session: DbSession,
    user: DoctorUser,
):
    profile = serializers.doctor_profile_for_user(session, user)
    appointment = _get_appointment_or_404(session, appointment_id)

    if appointment.doctor_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only write notes for your own appointments.",
        )
    if appointment.status == CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot add a note to a cancelled appointment.",
        )

    note = Note(
        appointment_id=appointment_id,
        doctor_id=profile.id,
        patient_id=appointment.patient_id,
        body=data.body,
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return serializers.note_public(session, note)


@router.get(
    "/appointments/{appointment_id}",
    response_model=list[NotePublic],
    status_code=status.HTTP_200_OK,
)
def notes_for_appointment(
    appointment_id: int,
    session: DbSession,
    user: CurrentUser,
):
    appointment = _get_appointment_or_404(session, appointment_id)

    if user.role == DOCTOR:
        profile = serializers.doctor_profile_for_user(session, user)
        allowed = appointment.doctor_id == profile.id
    elif user.role == PATIENT:
        allowed = appointment.patient_id == user.id
    elif user.role == RECEPTIONIST:
        allowed = True
    else:
        allowed = False

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to read notes for this appointment.",
        )

    notes = session.exec(
        select(Note)
        .where(Note.appointment_id == appointment_id)
        .order_by(col(Note.created_at))
    ).all()
    results = serializers.notes_public(session, list(notes))

    if user.role == RECEPTIONIST:
        return [
            item.model_copy(update={"body": HIDDEN_BODY})
            for item in results
        ]
    return results


@router.get(
    "/mine",
    response_model=list[NotePublic],
    status_code=status.HTTP_200_OK,
)
def my_notes(
    session: DbSession,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
):
    if user.role == DOCTOR:
        profile = serializers.doctor_profile_for_user(session, user)
        statement = select(Note).where(Note.doctor_id == profile.id)
    elif user.role == PATIENT:
        statement = select(Note).where(Note.patient_id == user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consultation notes are not available to front desk staff.",
        )

    notes = session.exec(
        statement.order_by(desc(col(Note.created_at))).limit(limit)
    ).all()
    return serializers.notes_public(session, list(notes))


@router.patch(
    "/{note_id}",
    response_model=NotePublic,
    status_code=status.HTTP_200_OK,
)
def edit_note(
    note_id: int,
    data: NoteUpdate,
    session: DbSession,
    user: DoctorUser,
):
    profile = serializers.doctor_profile_for_user(session, user)
    note = _get_note_or_404(session, note_id)

    if note.doctor_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit a note that you wrote.",
        )

    note.body = data.body
    note.updated_at = utc_now()
    session.add(note)
    session.commit()
    session.refresh(note)
    return serializers.note_public(session, note)


@router.delete(
    "/{note_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK,
)
def delete_note(
    note_id: int,
    session: DbSession,
    user: DoctorUser,
):
    profile = serializers.doctor_profile_for_user(session, user)
    note = _get_note_or_404(session, note_id)

    if note.doctor_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit a note that you wrote.",
        )

    session.delete(note)
    session.commit()
    return Message(message="Consultation note deleted.")
