"""Shared fixtures for the Adeniran Street Clinic API test suite.

``app.database`` builds its SQLAlchemy engine at *import* time from
``settings.database_url``, which is itself resolved when ``app.config`` is
imported. So the environment has to be in place before anything under
``app`` is imported at all.

That is why every ``app.*`` / ``fastapi.testclient`` import in this suite
lives inside a fixture or a test body, never at module level: pytest
imports the test modules during collection, long before any fixture runs.

An in-memory SQLite URL is deliberately *not* used. ``sqlite://`` gives
each new connection its own private database, and the audit trail
(``write_access_log``) opens a second connection of its own from a
background task, so it would write into a database nobody can read back.
A throwaway file under ``tmp_path_factory`` is shared by every connection
and is thrown away with the rest of the temporary directory.
"""

from __future__ import annotations

import itertools
import os
from datetime import date, timedelta

import pytest

# Seeded credentials, straight from app/seed.py.
SEEDED_PATIENT = ("patient_david", "patient123")
SEEDED_OTHER_PATIENT = ("patient_amaka", "patient123")
SEEDED_DOCTOR = ("doctor_ada", "doctor123")
SEEDED_OTHER_DOCTOR = ("doctor_emeka", "doctor123")
SEEDED_RECEPTIONIST = ("reception_joy", "reception123")
SEEDED_SECOND_RECEPTIONIST = ("reception_grace", "reception123")

# Every test gets its own clinic day and its own usernames, so no test can
# be broken by a slot another test happened to book first.
_day_counter = itertools.count()
_name_counter = itertools.count()


# --------------------------------------------------------------------------
# Application under test
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def clinic_app(tmp_path_factory):
    """Point the app at a throwaway SQLite file, then import it."""
    database_file = tmp_path_factory.mktemp("clinic-db") / "test_clinic.db"
    os.environ["CLINIC_DATABASE_URL"] = (
        f"sqlite:///{database_file.as_posix()}"
    )
    os.environ["CLINIC_SEED_ON_STARTUP"] = "1"
    os.environ["CLINIC_SECRET_KEY"] = "clinic-test-secret-key"

    from app.main import app

    return app


@pytest.fixture(scope="session")
def client(clinic_app):
    """A TestClient used as a context manager, so the lifespan runs.

    Entering the context triggers ``create_db_and_tables`` and
    ``seed_demo_data``, and makes Starlette's background tasks run
    synchronously inside each request.
    """
    from fastapi.testclient import TestClient

    with TestClient(clinic_app) as test_client:
        yield test_client


@pytest.fixture
def db_session(client):
    """A real session on the same engine the app uses, for assertions."""
    from sqlmodel import Session

    from app.database import engine

    with Session(engine) as session:
        yield session


# --------------------------------------------------------------------------
# Authentication helpers
# --------------------------------------------------------------------------
def sign_in(client, username: str, password: str) -> str:
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth():
    """Turn a raw token into the Authorization header dict."""

    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _auth


@pytest.fixture
def patient_token(client) -> str:
    return sign_in(client, *SEEDED_PATIENT)


@pytest.fixture
def other_patient_token(client) -> str:
    return sign_in(client, *SEEDED_OTHER_PATIENT)


@pytest.fixture
def doctor_token(client) -> str:
    return sign_in(client, *SEEDED_DOCTOR)


@pytest.fixture
def other_doctor_token(client) -> str:
    return sign_in(client, *SEEDED_OTHER_DOCTOR)


@pytest.fixture
def reception_token(client) -> str:
    return sign_in(client, *SEEDED_RECEPTIONIST)


@pytest.fixture
def second_reception_token(client) -> str:
    return sign_in(client, *SEEDED_SECOND_RECEPTIONIST)


@pytest.fixture
def session_profile(client, auth):
    """``GET /auth/me`` for any token."""

    def _profile(token: str) -> dict:
        response = client.get("/auth/me", headers=auth(token))
        assert response.status_code == 200, response.text
        return response.json()

    return _profile


@pytest.fixture
def patient_id(session_profile, patient_token) -> int:
    return session_profile(patient_token)["user"]["id"]


@pytest.fixture
def doctor_id(session_profile, doctor_token) -> int:
    return session_profile(doctor_token)["doctor"]["id"]


@pytest.fixture
def other_doctor_id(session_profile, other_doctor_token) -> int:
    return session_profile(other_doctor_token)["doctor"]["id"]


@pytest.fixture
def new_patient(client):
    """Register a brand new patient and return its credentials + token."""

    def _new_patient(full_name: str = "Silicon Tester") -> dict:
        username = f"tester_{next(_name_counter)}"
        password = "silicon100"
        response = client.post(
            "/auth/register",
            json={
                "username": username,
                "password": password,
                "full_name": full_name,
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        return {
            "username": username,
            "password": password,
            "token": payload["access_token"],
            "user": payload["user"],
        }

    return _new_patient


# --------------------------------------------------------------------------
# Diary helpers
# --------------------------------------------------------------------------
@pytest.fixture
def future_date() -> str:
    """A clinic day a few days ahead, unique to this test, as ISO text.

    The clinic refuses bookings in the past, and refuses a slot that is
    already taken, so a fresh day per test keeps every booking test
    independent of the ones before it.
    """
    return (date.today() + timedelta(days=3 + next(_day_counter))).isoformat()


@pytest.fixture
def past_date() -> str:
    return (date.today() - timedelta(days=5)).isoformat()


@pytest.fixture
def free_slots(client, auth):
    """``GET /patients/doctors/{id}/free-slots`` as ``HH:MM`` strings."""

    def _free_slots(token: str, doctor: int, day: str) -> list[str]:
        response = client.get(
            f"/patients/doctors/{doctor}/free-slots",
            params={"appointment_date": day},
            headers=auth(token),
        )
        assert response.status_code == 200, response.text
        return [slot[:5] for slot in response.json()]

    return _free_slots


@pytest.fixture
def book(client, auth):
    """Book as a patient. Returns the raw response so tests can assert."""

    def _book(
        token: str,
        doctor: int,
        day: str,
        slot: str = "09:00",
        reason: str = "Persistent headache for four days.",
    ):
        return client.post(
            "/patients/appointments",
            headers=auth(token),
            json={
                "doctor_id": doctor,
                "appointment_date": day,
                "appointment_time": slot,
                "reason": reason,
            },
        )

    return _book


@pytest.fixture
def booked_appointment(book, patient_token, doctor_id, future_date) -> dict:
    """One booked appointment: seeded patient with Dr. Ada, 09:00."""
    response = book(patient_token, doctor_id, future_date)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def written_note(client, auth, doctor_token, booked_appointment) -> dict:
    """A consultation note the appointment's own doctor wrote."""
    response = client.post(
        f"/notes/appointments/{booked_appointment['id']}",
        headers=auth(doctor_token),
        json={"body": "Blood pressure 120/80. Advised rest and fluids."},
    )
    assert response.status_code == 201, response.text
    return response.json()
