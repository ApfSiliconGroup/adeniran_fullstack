from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.database import get_session
from app.models import User


SECRET_KEY = "adeniran-street-clinic-secret-key"

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token"
)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    salt = bcrypt.gensalt()

    hashed = bcrypt.hashpw(
        password_bytes,
        salt
    )

    return hashed.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=60
    )

    to_encode.update(
        {
            "exp": expire
        }
    )

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(
    token: Annotated[
        str,
        Depends(oauth2_scheme)
    ],
    session: Annotated[
        Session,
        Depends(get_session)
    ],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_id = int(user_id)
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception

    user = session.exec(
        select(User).where(User.id == user_id)
    ).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(required_role: str):
    def role_checker(
        user: Annotated[
            User,
            Depends(get_current_user)
        ],
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




























# import time
# from typing import Annotated
# import bcrypt
# import jwt
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from sqlmodel import Session, select
# from app.database import get_session
# from app.models import User

# JWT_SECRET = "adeniran-clinic-teaching-secret"

# JWT_ALGORITHM = "HS256"

# TOKEN_MINUTES = 60

# oauth2_scheme = OAuth2PasswordBearer(
#     tokenUrl="/auth/token"
# )
# def hash_password(password: str) -> str:
#     return bcrypt.hashpw(
#         password.encode("utf-8"),
#         bcrypt.gensalt(),
#     ).decode("utf-8")
# def verify_password(
#     password: str,
#     password_hash: str,
# ) -> bool:
#     return bcrypt.checkpw(
#         password.encode("utf-8"),
#         password_hash.encode("utf-8"),
#     )
# def authenticate_user(
#     session: Session,
#     username: str,
#     password: str,
# ) -> User | None:
#     user = session.exec(
#         select(User).where(
#             User.username == username
#         )
#     ).first()

#     if user is None:
#         return None
#     if not verify_password(
#         password,
#         user.password_hash,
#     ):
#         return None
#     return user
# def create_access_token(user: User) -> str:
#     payload = {
#         "sub": user.username,
#         "role": user.role,
#         "exp": time.time()
#         + TOKEN_MINUTES * 60,
#     }
#     return jwt.encode(
#         payload,
#         JWT_SECRET,
#         algorithm=JWT_ALGORITHM,
#     )
# def get_current_user(
#     token: Annotated[
#         str,
#         Depends(oauth2_scheme)
#     ],
#     session: Annotated[
#         Session,
#         Depends(get_session)
#     ],
# ) -> User:
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={
#             "WWW-Authenticate": "Bearer"
#         },
#     )
#     try:
#         payload = jwt.decode(
#             token,
#             JWT_SECRET,
#             algorithms=[JWT_ALGORITHM],
#         )
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token has expired. Please sign in again.",
#             headers={
#                 "WWW-Authenticate": "Bearer"
#             },
#         )
#     except jwt.InvalidTokenError:
#         raise credentials_exception
#     username = payload.get("sub")
#     if not username:
#         raise credentials_exception
#     user = session.exec(
#         select(User).where(
#             User.username == username
#         )
#     ).first()

#     if user is None:
#         raise credentials_exception
#     return user
# def require_role(required_role: str):
#     def role_checker(
#         user: Annotated[
#             User,
#             Depends(get_current_user)
#         ],
#     ) -> User:
#         if user.role != required_role:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail=(
#                     f"Only the {required_role} role "
#                     "can perform this action."
#                 ),
#             )
#         return user
#     return role_checker