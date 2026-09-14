from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import get_session
from app.models import User
from app.security import create_access_token, verify_password


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/token",
    status_code=status.HTTP_200_OK
)
def login_for_access_token(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends()
    ],
    session: Annotated[
        Session,
        Depends(get_session)
    ]
):
    user = session.exec(
        select(User).where(
            User.username == form_data.username
        )
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not verify_password(
        form_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


































# from typing import Annotated
# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlmodel import Session, select
# from app.database import get_session
# from app.models import User
# from app.schemas import (
#     PatientRegister,
#     Token,
#     UserPublic,
# )
# from app.security import (
#     authenticate_user,
#     create_access_token,
#     hash_password,
# )

# router = APIRouter(
#     prefix="/auth",
#     tags=["Authentication"],
# )
# @router.post(
#     "/register",
#     response_model=UserPublic,
#     status_code=status.HTTP_201_CREATED,
# )
# def register_patient(
#     data: PatientRegister,
#     session: Annotated[
#         Session,
#         Depends(get_session)
#     ],
# ):
#     existing_user = session.exec(
#         select(User).where(
#             User.username == data.username
#         )
#     ).first()
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="Username already exists.",
#         )
#     user = User(
#         username=data.username,
#         password_hash=hash_password(
#             data.password
#         ),
#         role="patient",
#     )
#     session.add(user)
#     session.commit()
#     session.refresh(user)
#     return user
# @router.post(
#     "/token",
#     response_model=Token,
#     status_code=status.HTTP_200_OK,
# )
# def login_for_token(
#     form: Annotated[
#         OAuth2PasswordRequestForm,
#         Depends()
#     ],
#     session: Annotated[
#         Session,
#         Depends(get_session)
#     ],
# ):
#     user = authenticate_user(
#         session,
#         form.username,
#         form.password,
#     )
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password.",
#             headers={
#                 "WWW-Authenticate": "Bearer"
#             },
#         )
#     token = create_access_token(user)
#     return Token(
#         access_token=token


