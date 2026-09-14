"""Public signup, sign in and the current session profile.

Both ``/auth/register`` and ``/auth/token`` hand back the same ``Token``
envelope so the frontend has the signed in user in one round trip.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import func, select

from app.config import settings
from app.models import DOCTOR, PATIENT, Doctor, User
from app.schemas import (
    DoctorPublic,
    PatientRegister,
    SessionProfile,
    Token,
    UserPublic,
)
from app.security import (
    CurrentUser,
    DbSession,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue(user: User) -> Token:
    """Wrap a freshly signed JWT together with the user it belongs to."""
    return Token(
        access_token=create_access_token(user),
        token_type="bearer",
        expires_in=settings.access_token_minutes * 60,
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient account",
)
def register_patient(data: PatientRegister, session: DbSession) -> Token:
    existing = session.exec(
        select(User).where(
            func.lower(User.username) == data.username.lower()
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "That username is already taken. "
                "Please choose another one."
            ),
        )

    user = User(
        username=data.username,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=PATIENT,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    # Signing up signs you in, so the UI never bounces to a login form.
    return _issue(user)


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Exchange a username and password for a token",
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: DbSession,
) -> Token:
    user = session.exec(
        select(User).where(User.username == form_data.username)
    ).first()

    # An unknown username and a wrong password must be indistinguishable.
    if user is None or not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    return _issue(user)


@router.get(
    "/me",
    response_model=SessionProfile,
    status_code=status.HTTP_200_OK,
    summary="The signed in user plus their doctor profile",
)
def read_current_session(
    user: CurrentUser,
    session: DbSession,
) -> SessionProfile:
    doctor: DoctorPublic | None = None
    if user.role == DOCTOR:
        row = session.exec(
            select(Doctor).where(Doctor.user_id == user.id)
        ).first()
        # A doctor user with no clinical row is broken data, not a 404 here.
        if row is not None:
            doctor = DoctorPublic.model_validate(row)

    return SessionProfile(
        user=UserPublic.model_validate(user),
        doctor=doctor,
    )
