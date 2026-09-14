"""SQLModel tables for the clinic.

Four entities carry the whole domain:

* ``User``        - one row per person, with a role of patient/doctor/receptionist.
* ``Doctor``      - the clinical profile that hangs off a doctor's user row.
* ``Appointment`` - a booked slot in the clinic diary.
* ``Note``        - a consultation note a doctor writes for the patient
                    attached to an appointment.
"""

from datetime import date, datetime, time, timezone
from typing import Annotated

from sqlmodel import Field, Relationship, SQLModel

PATIENT = "patient"
DOCTOR = "doctor"
RECEPTIONIST = "receptionist"
ROLES = (PATIENT, DOCTOR, RECEPTIONIST)

BOOKED = "booked"
COMPLETED = "completed"
CANCELLED = "cancelled"


def utc_now() -> datetime:
    """Timezone aware ``now``; ``datetime.utcnow`` is deprecated."""
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Annotated[int | None, Field(default=None, primary_key=True)]
    username: str = Field(index=True, unique=True)
    full_name: str = Field(default="")
    password_hash: str
    role: str = Field(default=PATIENT, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)

    doctor: "Doctor" = Relationship(back_populates="user")
    appointments: list["Appointment"] = Relationship(
        back_populates="patient",
        sa_relationship_kwargs={
            "foreign_keys": "Appointment.patient_id",
        },
    )

    @property
    def display_name(self) -> str:
        return self.full_name or self.username


class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"

    id: Annotated[int | None, Field(default=None, primary_key=True)]
    user_id: int = Field(foreign_key="users.id", unique=True)
    name: str
    speciality: str = Field(index=True)
    bio: str = Field(default="")
    years_experience: int = Field(default=0)
    consulting_room: str = Field(default="")
    is_accepting: bool = Field(default=True)

    user: "User" = Relationship(back_populates="doctor")
    appointments: list["Appointment"] = Relationship(
        back_populates="doctor"
    )
    notes: list["Note"] = Relationship(back_populates="doctor")


class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"

    id: Annotated[int | None, Field(default=None, primary_key=True)]
    patient_id: int = Field(foreign_key="users.id", index=True)
    doctor_id: int = Field(foreign_key="doctors.id", index=True)
    appointment_date: date = Field(index=True)
    appointment_time: time
    status: str = Field(default=BOOKED, index=True)
    # Short outcome summary captured when the doctor completes the visit.
    note: str | None = Field(default=None)
    # Why the patient booked, supplied at booking time.
    reason: str = Field(default="")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    patient: "User" = Relationship(
        back_populates="appointments",
        sa_relationship_kwargs={
            "foreign_keys": "Appointment.patient_id",
        },
    )
    doctor: "Doctor" = Relationship(back_populates="appointments")
    notes: list["Note"] = Relationship(
        back_populates="appointment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Note(SQLModel, table=True):
    """A consultation note written by a doctor for a patient."""

    __tablename__ = "notes"

    id: Annotated[int | None, Field(default=None, primary_key=True)]
    appointment_id: int = Field(
        foreign_key="appointments.id",
        index=True,
    )
    doctor_id: int = Field(foreign_key="doctors.id", index=True)
    patient_id: int = Field(foreign_key="users.id", index=True)
    body: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    appointment: "Appointment" = Relationship(back_populates="notes")
    doctor: "Doctor" = Relationship(back_populates="notes")


class AccessLog(SQLModel, table=True):
    __tablename__ = "access_logs"

    id: Annotated[int | None, Field(default=None, primary_key=True)]
    user_id: int = Field(foreign_key="users.id", index=True)
    appointment_id: int = Field(foreign_key="appointments.id")
    action: str
    created_at: datetime = Field(default_factory=utc_now)
