from sqlmodel import Session, select
from app.database import engine
from app.models import Doctor, User
from app.security import hash_password

def seed_demo_data() -> None:
    with Session(engine) as session:
        receptionist = session.exec(
            select(User).where(
                User.username == "reception_joy"
            )
        ).first()
        if receptionist is None:
            receptionist = User(
                username="reception_joy",
                password_hash=hash_password(
                    "reception123"
                ),
                role="receptionist",
            )
            session.add(receptionist)

        patient = session.exec(
            select(User).where(
                User.username == "patient_david"
            )
        ).first()
        if patient is None:
            patient = User(
                username="patient_david",
                password_hash=hash_password(
                    "patient123"
                ),
                role="patient",
            )
            session.add(patient)

        doctor_user = session.exec(
            select(User).where(
                User.username == "doctor_ada"
            )
        ).first()
        if doctor_user is None:
            doctor_user = User(
                username="doctor_ada",
                password_hash=hash_password(
                    "doctor123"
                ),
                role="doctor",
            )
            session.add(doctor_user)
            session.commit()
            session.refresh(doctor_user)
        doctor = session.exec(
            select(Doctor).where(
                Doctor.user_id == doctor_user.id
            )
        ).first()

        if doctor is None:

            doctor = Doctor(
                user_id=doctor_user.id,
                name="Dr. Ada Okafor",
                speciality="General Medicine",
            )
            session.add(doctor)
        doctor_user_2 = session.exec(
            select(User).where(
                User.username == "doctor_emeka"
            )
        ).first()
        if doctor_user_2 is None:
            doctor_user_2 = User(
                username="doctor_emeka",
                password_hash=hash_password(
                    "doctor123"
                ),
                role="doctor",
            )
            session.add(doctor_user_2)
            session.commit()
            session.refresh(doctor_user_2)
        doctor_2 = session.exec(
            select(Doctor).where(
                Doctor.user_id == doctor_user_2.id
            )
        ).first()
        if doctor_2 is None:
            doctor_2 = Doctor(
                user_id=doctor_user_2.id,
                name="Dr. Emeka Nwosu",
                speciality="Pediatrics",
            )
            session.add(doctor_2)
        session.commit()