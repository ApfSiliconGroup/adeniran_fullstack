"""Demo data.

The clinic ships with four doctors, two receptionists and a few patient
accounts so every screen in the frontend has something real to show.
Seeding is idempotent: it looks each account up by username first, so
restarting the API never creates duplicates.
"""

from dataclasses import dataclass

from sqlmodel import Session, select

from app.database import engine
from app.models import DOCTOR, PATIENT, RECEPTIONIST, Doctor, User
from app.security import hash_password


@dataclass(frozen=True)
class DoctorSeed:
    username: str
    password: str
    name: str
    speciality: str
    bio: str
    years_experience: int
    consulting_room: str


@dataclass(frozen=True)
class StaffSeed:
    username: str
    password: str
    full_name: str
    role: str


DOCTOR_SEEDS: tuple[DoctorSeed, ...] = (
    DoctorSeed(
        username="doctor_ada",
        password="doctor123",
        name="Dr. Ada Okafor",
        speciality="General Medicine",
        bio=(
            "Family physician who handles day to day illnesses, health "
            "checks and referrals for the whole household."
        ),
        years_experience=12,
        consulting_room="Room 1",
    ),
    DoctorSeed(
        username="doctor_emeka",
        password="doctor123",
        name="Dr. Emeka Nwosu",
        speciality="Pediatrics",
        bio=(
            "Children's doctor covering newborn checks, immunisation "
            "schedules and childhood infections."
        ),
        years_experience=9,
        consulting_room="Room 2",
    ),
    # --- Added so the clinic runs a four doctor rota -------------------
    DoctorSeed(
        username="doctor_zainab",
        password="doctor123",
        name="Dr. Zainab Bello",
        speciality="Cardiology",
        bio=(
            "Heart specialist focused on blood pressure management, "
            "ECG review and long term cardiac follow up."
        ),
        years_experience=15,
        consulting_room="Room 3",
    ),
    DoctorSeed(
        username="doctor_tunde",
        password="doctor123",
        name="Dr. Tunde Adeyemi",
        speciality="Dermatology",
        bio=(
            "Skin, hair and nail clinic. Treats eczema, acne and "
            "persistent rashes, with same week follow up."
        ),
        years_experience=7,
        consulting_room="Room 4",
    ),
)

STAFF_SEEDS: tuple[StaffSeed, ...] = (
    StaffSeed(
        username="reception_joy",
        password="reception123",
        full_name="Joy Adebayo",
        role=RECEPTIONIST,
    ),
    # --- Second receptionist so the front desk has cover --------------
    StaffSeed(
        username="reception_grace",
        password="reception123",
        full_name="Grace Uzoma",
        role=RECEPTIONIST,
    ),
    StaffSeed(
        username="patient_david",
        password="patient123",
        full_name="David Orji",
        role=PATIENT,
    ),
    StaffSeed(
        username="patient_amaka",
        password="patient123",
        full_name="Amaka Eze",
        role=PATIENT,
    ),
)


def _upsert_user(
    session: Session,
    *,
    username: str,
    password: str,
    full_name: str,
    role: str,
) -> User:
    user = session.exec(
        select(User).where(User.username == username)
    ).first()

    if user is None:
        user = User(
            username=username,
            full_name=full_name,
            password_hash=hash_password(password),
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    # Backfill details for accounts created by an earlier version.
    changed = False
    if not user.full_name and full_name:
        user.full_name = full_name
        changed = True
    if user.role != role:
        user.role = role
        changed = True
    if changed:
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def seed_demo_data() -> None:
    with Session(engine) as session:
        for staff in STAFF_SEEDS:
            _upsert_user(
                session,
                username=staff.username,
                password=staff.password,
                full_name=staff.full_name,
                role=staff.role,
            )

        for seed in DOCTOR_SEEDS:
            doctor_user = _upsert_user(
                session,
                username=seed.username,
                password=seed.password,
                full_name=seed.name,
                role=DOCTOR,
            )

            profile = session.exec(
                select(Doctor).where(Doctor.user_id == doctor_user.id)
            ).first()

            if profile is None:
                session.add(
                    Doctor(
                        user_id=doctor_user.id,
                        name=seed.name,
                        speciality=seed.speciality,
                        bio=seed.bio,
                        years_experience=seed.years_experience,
                        consulting_room=seed.consulting_room,
                    )
                )
                continue

            # Fill in profile fields introduced after the first release.
            if not profile.bio:
                profile.bio = seed.bio
            if not profile.years_experience:
                profile.years_experience = seed.years_experience
            if not profile.consulting_room:
                profile.consulting_room = seed.consulting_room
            session.add(profile)

        session.commit()
