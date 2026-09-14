"""Password hashing, JWT issuing and the role based dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import DOCTOR, PATIENT, RECEPTIONIST, User

# bcrypt refuses anything longer than 72 bytes, so both hashing and
# verification truncate identically instead of raising at runtime.
BCRYPT_MAX_BYTES = 72

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # A malformed stored hash must fail closed, not crash the request.
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_minutes
    )
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise CREDENTIALS_EXCEPTION

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise CREDENTIALS_EXCEPTION
    try:
        user_id = int(raw_user_id)
    except (TypeError, ValueError):
        raise CREDENTIALS_EXCEPTION

    user = session.exec(select(User).where(User.id == user_id)).first()
    if user is None:
        raise CREDENTIALS_EXCEPTION
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )
    return user


def require_role(required_role: str):
    """Dependency factory that allows exactly one role through."""

    def role_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Only the {required_role} role "
                    "can perform this action."
                ),
            )
        return user

    return role_checker


def require_any_role(*allowed_roles: str):
    """Dependency factory for endpoints shared by several roles."""

    def role_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "This action is limited to: "
                    + ", ".join(allowed_roles)
                    + "."
                ),
            )
        return user

    return role_checker


CurrentUser = Annotated[User, Depends(get_current_user)]
PatientUser = Annotated[User, Depends(require_role(PATIENT))]
DoctorUser = Annotated[User, Depends(require_role(DOCTOR))]
ReceptionistUser = Annotated[User, Depends(require_role(RECEPTIONIST))]
DbSession = Annotated[Session, Depends(get_session)]
