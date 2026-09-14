from datetime import date, datetime, time
from typing import Annotated
from pydantic import BaseModel, Field, field_validator

class PatientRegister(BaseModel):
    username: Annotated[
        str,
        Field(
            min_length=3,
            examples=["Silicon Group"],
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=6,
            examples=["silicon100"],
        ),
    ]

    @field_validator("username")
    @classmethod
    def username_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be blank.")
        return value

class UserPublic(BaseModel):
    id: int
    username: str
    role: str

class AppointmentCreate(BaseModel):
    doctor_id: Annotated[
        int,
        Field(
            examples=[1],
        ),
    ]
    appointment_date: Annotated[
        date,
        Field(
            examples=["2026-09-15"],
        ),
    ]
    appointment_time: Annotated[
        time,
        Field(
            examples=["09:00"],
        ),
    ]

class AppointmentPublic(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    status: str
    note: Annotated[
        str | None,
        Field(default=None),
    ]
class DoctorPublic(BaseModel):
    id: int
    name: str
    speciality: str
class CompleteAppointment(BaseModel):
    note: Annotated[
        str,
        Field(
            min_length=1,
            max_length=500,
            examples=[
                "Patient completed consultation successfully."
            ],
        ),
    ]

    @field_validator("note")
    @classmethod
    def note_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Appointment note cannot be blank.")
        return value
class WalkInPatientCreate(BaseModel):
    username: Annotated[
        str,
        Field(
            min_length=3,
            examples=["walkin_patient"],
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=6,
            examples=["walkin123"],
        ),
    ]
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AccessLogPublic(BaseModel):
    id: int
    user_id: int
    appointment_id: int
    action: str
    created_at: datetime