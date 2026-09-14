"""Application entry point for the Adeniran Street Clinic API."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_db_and_tables
from app.routers import auth, doctors, notes, patients, public, receptionist
from app.seed import seed_demo_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    if settings.seed_on_startup:
        seed_demo_data()
    yield


app = FastAPI(
    title=settings.project_name,
    description=(
        "A clinic booking backend built with FastAPI, SQLModel, SQLite "
        "and JWT authentication. Patients book appointments, doctors "
        "manage their diary and write consultation notes, and "
        "receptionists run the whole front desk."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Start Here", "description": "Service discovery."},
        {"name": "Public", "description": "Open endpoints, no token needed."},
        {"name": "Authentication", "description": "Sign up and sign in."},
        {"name": "Patients", "description": "Booking and self service."},
        {"name": "Doctors", "description": "The clinical day."},
        {"name": "Notes", "description": "Consultation notes."},
        {"name": "Receptionist", "description": "Front desk operations."},
    ],
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = (
        f"{time.perf_counter() - start_time:.4f}"
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exception: RequestValidationError,
):
    """Return one readable sentence instead of a nested error tree.

    The frontend renders `detail` directly, so a 422 has to be as
    friendly as any other error.
    """
    errors = exception.errors()
    if errors:
        first = errors[0]
        location = [
            str(part)
            for part in first.get("loc", [])
            if part not in ("body", "query", "path")
        ]
        field = " ".join(location).replace("_", " ") or "request"
        message = first.get("msg", "is not valid")
        message = message.removeprefix("Value error, ")
        detail = f"{field.capitalize()}: {message}"
    else:
        detail = "That request could not be processed."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail, "errors": errors},
    )


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(notes.router)
app.include_router(receptionist.router)


@app.get("/", tags=["Start Here"], status_code=status.HTTP_200_OK)
def home() -> dict:
    return {
        "message": "Welcome to Adeniran Street Clinic Booking API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
        "auth": "JWT Bearer token",
        "roles": ["patient", "doctor", "receptionist"],
    }
