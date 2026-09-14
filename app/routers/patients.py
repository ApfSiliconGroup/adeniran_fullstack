from datetime import date, datetime, time
from typing import Annotated
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlmodel import Session, select
from app.database import engine, get_session
from app.models import (
    AccessLog,
    Appointment,
    Doctor,
    User,
)
from app.schemas import (
    AppointmentCreate,
    AppointmentPublic,
    DoctorPublic,
    PatientRegister,
    UserPublic,
)
from app.security import hash_password, require_role
router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)
AVAILABLE_SLOTS = [
    time(9, 0),
    time(10, 0),
    time(11, 0),
    time(14, 0),
    time(15, 0),
    time(16, 0),
]


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register_patient(
    data: PatientRegister,
    session: Annotated[
        Session,
        Depends(get_session)
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
        password_hash=hash_password(data.password),
        role="patient",
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


def write_access_log(
    user_id: int,
    appointment_id: int,
) -> None:
    with Session(engine) as session:
        log = AccessLog(
            user_id=user_id,
            appointment_id=appointment_id,
            action="patient record opened",
            created_at=datetime.utcnow(),
        )
        session.add(log)
        session.commit()
@router.get(
    "/doctors",
    response_model=list[DoctorPublic],
    status_code=status.HTTP_200_OK,
)
def list_doctors(
    speciality: str | None = Query(
        default=None,
        min_length=2,
        description="Optional speciality filter",
    ),
    session: Annotated[
        Session,
        Depends(get_session)
    ] = None,
    user: Annotated[
        User,
        Depends(require_role("patient"))
    ] = None,
):
    statement = select(Doctor)
    if speciality:
        statement = statement.where(
            Doctor.speciality == speciality
        )
    return session.exec(
        statement
    ).all()
@router.get(
    "/doctors/{doctor_id}/free-slots",
    response_model=list[time],
    status_code=status.HTTP_200_OK,
)
def free_slots(
    doctor_id: int,
    appointment_date: date,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("patient"))
    ],
):
    doctor = session.get(
        Doctor,
        doctor_id
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )
    booked = session.exec(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date
            == appointment_date,
            Appointment.status == "booked",
        )
    ).all()
    booked_times = {
        appointment.appointment_time
        for appointment in booked
    }
    return [
        slot
        for slot in AVAILABLE_SLOTS
        if slot not in booked_times
    ]
@router.post(
    "/appointments",
    response_model=AppointmentPublic,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    data: AppointmentCreate,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("patient"))
    ],
):
    today = date.today()
    current_time = datetime.now().time()
    if (
        data.appointment_date < today
        or (
            data.appointment_date == today
            and data.appointment_time <= current_time
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot book a slot in the past.",
        )
    doctor = session.get(
        Doctor,
        data.doctor_id
    )
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )
    if data.appointment_time not in AVAILABLE_SLOTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "That is not one of the clinic's "
                "available time slots."
            ),
        )
    existing = session.exec(
        select(Appointment).where(
            Appointment.doctor_id
            == data.doctor_id,
            Appointment.appointment_date
            == data.appointment_date,
            Appointment.appointment_time
            == data.appointment_time,
            Appointment.status == "booked",
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That doctor slot is already booked.",
        )
    appointment = Appointment(
        patient_id=user.id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        status="booked",
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    return appointment
@router.get(
    "/appointments",
    response_model=list[AppointmentPublic],
    status_code=status.HTTP_200_OK,
)
def list_my_appointments(
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("patient"))
    ],
):
    return session.exec(
        select(Appointment).where(
            Appointment.patient_id == user.id
        )
    ).all()
@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def get_my_appointment(
    appointment_id: int,
    background_tasks: BackgroundTasks,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("patient"))
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
    if appointment.patient_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You cannot view another "
                "patient's appointment."
            ),
        )
    background_tasks.add_task(
        write_access_log,
        user.id,
        appointment.id,
    )
    return appointment
@router.delete(
    "/appointments/{appointment_id}",
    response_model=AppointmentPublic,
    status_code=status.HTTP_200_OK,
)
def cancel_my_appointment(
    appointment_id: int,
    session: Annotated[
        Session,
        Depends(get_session)
    ],
    user: Annotated[
        User,
        Depends(require_role("patient"))
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
    if appointment.patient_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You can only cancel "
                "your own appointment."
            ),
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