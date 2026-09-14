import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from app.routers import auth, doctors, patients, receptionist
from app.seed import seed_demo_data

app = FastAPI(
    title="Adeniran Street Clinic Booking API",
    description=(
        "A clinic booking backend "
        "built with FastAPI, SQLModel, SQLite and "
        "JWT token authentication. Patients book "
        "appointments, doctors manage their appointments, "
        "and receptionists manage the whole diary."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.middleware("http")
async def add_process_time_header(
    request: Request,
    call_next,
):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (
        time.perf_counter()
        - start_time
    )
    response.headers[
        "X-Process-Time"
    ] = str(process_time)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(doctors.router)
app.include_router(receptionist.router)

@app.on_event("startup")
def startup():
    create_db_and_tables()
    seed_demo_data()
@app.get(
    "/",
    tags=["Start Here"],
    response_model=dict,
    status_code=200,
)
def home():
    return {
        "message": (
            "Welcome to Adeniran Street "
            "Clinic Booking API"
        ),
        "docs": "/docs",
        "auth": "JWT Bearer token",
        "roles": [
            "patient",
            "doctor",
            "receptionist",
        ],
    }