from datetime import date, datetime, time
from typing import Annotated
from sqlmodel import Field, Relationship, SQLModel
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Annotated[int | None, Field(default=None, primary_key=True)]
    username: str = Field(index=True)
    password_hash: str
    role: str
    doctor: "Doctor" = Relationship(
        back_populates="user"
    )
    appointments: list["Appointment"] = Relationship(
        back_populates="patient"
    )
class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"
    id: Annotated[int | None, Field(default=None, primary_key=True)]
    user_id: int = Field(
        foreign_key="users.id",
        unique=True
    )
    name: str
    speciality: str
    user: "User" = Relationship(
        back_populates="doctor"
    )
    appointments: list["Appointment"] = Relationship(
        back_populates="doctor"
    )
class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"
    id: Annotated[int | None, Field(default=None, primary_key=True)]
    patient_id: int = Field(
        foreign_key="users.id"
    )
    doctor_id: int = Field(
        foreign_key="doctors.id"
    )
    appointment_date: date
    appointment_time: time
    status: str = "booked"
    note: str | None = None
    patient: "User" = Relationship(
        back_populates="appointments"
    )
    doctor: "Doctor" = Relationship(
        back_populates="appointments"
    )
class AccessLog(SQLModel, table=True):
    __tablename__ = "access_logs"

    id: Annotated[int | None, Field(default=None, primary_key=True)]

    user_id: int = Field(
        foreign_key="users.id"
    )
    appointment_id: int = Field(
        foreign_key="appointments.id"
    )

    action: str

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )
