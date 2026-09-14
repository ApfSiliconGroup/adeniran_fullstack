"""Read helpers shared by the routers.

They exist so every endpoint returns the same enriched shape (with doctor
and patient names attached) and so list endpoints avoid N+1 queries.
"""

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.models import Appointment, Doctor, Note, User
from app.schemas import AppointmentPublic, DoctorPublic, NotePublic


def doctor_profile_for_user(session: Session, user: User) -> Doctor:
    """The Doctor row that belongs to a signed in doctor user."""
    doctor = session.exec(
        select(Doctor).where(Doctor.user_id == user.id)
    ).first()
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for this account.",
        )
    return doctor


def _name_maps(
    session: Session,
    patient_ids: set[int],
    doctor_ids: set[int],
) -> tuple[dict[int, str], dict[int, Doctor]]:
    patients: dict[int, str] = {}
    if patient_ids:
        rows = session.exec(
            select(User).where(User.id.in_(patient_ids))  # type: ignore[attr-defined]
        ).all()
        patients = {
            row.id: (row.full_name or row.username)
            for row in rows
            if row.id is not None
        }

    doctors: dict[int, Doctor] = {}
    if doctor_ids:
        rows = session.exec(
            select(Doctor).where(Doctor.id.in_(doctor_ids))  # type: ignore[attr-defined]
        ).all()
        doctors = {row.id: row for row in rows if row.id is not None}

    return patients, doctors


def _note_counts(
    session: Session,
    appointment_ids: set[int],
) -> dict[int, int]:
    if not appointment_ids:
        return {}
    rows = session.exec(
        select(Note.appointment_id, func.count(Note.id))
        .where(Note.appointment_id.in_(appointment_ids))  # type: ignore[attr-defined]
        .group_by(Note.appointment_id)
    ).all()
    return {appointment_id: count for appointment_id, count in rows}


def appointments_public(
    session: Session,
    appointments: list[Appointment],
) -> list[AppointmentPublic]:
    """Serialise a list of appointments with joined labels, in 3 queries."""
    if not appointments:
        return []

    patient_names, doctors = _name_maps(
        session,
        {item.patient_id for item in appointments},
        {item.doctor_id for item in appointments},
    )
    counts = _note_counts(
        session,
        {item.id for item in appointments if item.id is not None},
    )

    results: list[AppointmentPublic] = []
    for item in appointments:
        doctor = doctors.get(item.doctor_id)
        results.append(
            AppointmentPublic(
                id=item.id or 0,
                patient_id=item.patient_id,
                doctor_id=item.doctor_id,
                appointment_date=item.appointment_date,
                appointment_time=item.appointment_time,
                status=item.status,
                note=item.note,
                reason=item.reason or "",
                created_at=item.created_at,
                patient_name=patient_names.get(item.patient_id, "Patient"),
                doctor_name=doctor.name if doctor else "Doctor",
                doctor_speciality=doctor.speciality if doctor else "",
                note_count=counts.get(item.id or 0, 0),
            )
        )
    return results


def appointment_public(
    session: Session,
    appointment: Appointment,
) -> AppointmentPublic:
    return appointments_public(session, [appointment])[0]


def notes_public(
    session: Session,
    notes: list[Note],
) -> list[NotePublic]:
    if not notes:
        return []

    patient_names, doctors = _name_maps(
        session,
        {item.patient_id for item in notes},
        {item.doctor_id for item in notes},
    )

    appointment_ids = {item.appointment_id for item in notes}
    appointments = session.exec(
        select(Appointment).where(
            Appointment.id.in_(appointment_ids)  # type: ignore[attr-defined]
        )
    ).all()
    diary = {row.id: row for row in appointments if row.id is not None}

    results: list[NotePublic] = []
    for item in notes:
        doctor = doctors.get(item.doctor_id)
        appointment = diary.get(item.appointment_id)
        results.append(
            NotePublic(
                id=item.id or 0,
                appointment_id=item.appointment_id,
                doctor_id=item.doctor_id,
                patient_id=item.patient_id,
                body=item.body,
                created_at=item.created_at,
                updated_at=item.updated_at,
                doctor_name=doctor.name if doctor else "Doctor",
                patient_name=patient_names.get(item.patient_id, "Patient"),
                appointment_date=(
                    appointment.appointment_date if appointment else None
                ),
                appointment_time=(
                    appointment.appointment_time if appointment else None
                ),
            )
        )
    return results


def note_public(session: Session, note: Note) -> NotePublic:
    return notes_public(session, [note])[0]


def doctor_public(doctor: Doctor) -> DoctorPublic:
    return DoctorPublic.model_validate(doctor)
