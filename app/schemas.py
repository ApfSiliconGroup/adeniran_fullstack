"""Pydantic request and response models.

These are the API contract the Next.js frontend is generated from, so the
field names here match `frontend/src/types/api.ts` exactly.
"""

from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["patient", "doctor", "receptionist"]


def _clean(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be blank.")
    return value


# --------------------------------------------------------------------------
# Accounts and authentication
# --------------------------------------------------------------------------
class PatientRegister(BaseModel):
    username: Annotated[
        str,
        Field(min_length=3, max_length=40, examples=["silicon_group"]),
    ]
    password: Annotated[
        str,
        Field(min_length=6, max_length=72, examples=["silicon100"]),
    ]
    full_name: Annotated[
        str,
        Field(default="", max_length=120, examples=["Silicon Group"]),
    ] = ""

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = _clean(value, "Username")
        if " " in value:
            raise ValueError("Username cannot contain spaces.")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return value.strip()


class WalkInPatientCreate(PatientRegister):
    """Same shape as a self-service signup, created by a receptionist."""


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str = ""
    role: str
    created_at: datetime | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class SessionProfile(BaseModel):
    """`GET /auth/me` - the signed in user plus their doctor profile."""

    user: UserPublic
    doctor: "DoctorPublic | None" = None


# --------------------------------------------------------------------------
# Doctors
# --------------------------------------------------------------------------
class DoctorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    speciality: str
    bio: str = ""
    years_experience: int = 0
    consulting_room: str = ""
    is_accepting: bool = True


# --------------------------------------------------------------------------
# Appointments
# --------------------------------------------------------------------------
class AppointmentCreate(BaseModel):
    doctor_id: Annotated[int, Field(examples=[1], ge=1)]
    appointment_date: Annotated[date, Field(examples=["2026-09-15"])]
    appointment_time: Annotated[time, Field(examples=["09:00"])]
    reason: Annotated[
        str,
        Field(
            default="",
            max_length=280,
            examples=["Persistent headache for four days."],
        ),
    ] = ""

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return value.strip()


class AppointmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    status: str
    note: str | None = None
    reason: str = ""
    created_at: datetime | None = None
    # Joined, read only labels so the UI never has to guess a name.
    patient_name: str = ""
    doctor_name: str = ""
    doctor_speciality: str = ""
    note_count: int = 0


class CompleteAppointment(BaseModel):
    note: Annotated[
        str,
        Field(
            min_length=1,
            max_length=1000,
            examples=["Consultation completed. Review in two weeks."],
        ),
    ]

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _clean(value, "Appointment note")


class ReceptionistBooking(AppointmentCreate):
    """A front desk booking made on behalf of an existing patient."""

    patient_id: Annotated[int, Field(examples=[4], ge=1)]


# --------------------------------------------------------------------------
# Consultation notes
# --------------------------------------------------------------------------
class NoteCreate(BaseModel):
    body: Annotated[
        str,
        Field(
            min_length=1,
            max_length=4000,
            examples=[
                "Blood pressure 120/80. Advised rest and fluids. "
                "Prescribed paracetamol 500mg twice daily for three days."
            ],
        ),
    ]

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        return _clean(value, "Note")


class NoteUpdate(NoteCreate):
    """A doctor correcting a note they wrote."""


class NotePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    doctor_id: int
    patient_id: int
    body: str
    created_at: datetime
    updated_at: datetime
    doctor_name: str = ""
    patient_name: str = ""
    appointment_date: date | None = None
    appointment_time: time | None = None


# --------------------------------------------------------------------------
# Operations
# --------------------------------------------------------------------------
class AccessLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    appointment_id: int
    action: str
    created_at: datetime


class DiaryOverview(BaseModel):
    appointment_date: date
    total: int
    booked: int
    completed: int
    cancelled: int
    doctors_on_duty: int
    slots_per_doctor: int
    utilisation: int


class ClinicStats(BaseModel):
    doctors: int
    specialities: list[str]
    slots_per_day: int
    consultations_completed: int


class Message(BaseModel):
    message: str


SessionProfile.model_rebuild()
