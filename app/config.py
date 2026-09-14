"""Central configuration for the Adeniran Street Clinic API.

Every value can be overridden with an environment variable so the same
code runs on a laptop (SQLite) and on a hosted platform (Postgres).
"""

import os
from datetime import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "true" if default else "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """Runtime settings, resolved once at import time."""

    project_name: str = "Adeniran Street Clinic Booking API"
    version: str = "2.0.0"

    # --- Security -------------------------------------------------------
    secret_key: str = _env(
        "CLINIC_SECRET_KEY",
        "adeniran-street-clinic-secret-key",
    )
    algorithm: str = _env("CLINIC_JWT_ALGORITHM", "HS256")
    access_token_minutes: int = _env_int("CLINIC_TOKEN_MINUTES", 60)

    # --- Database -------------------------------------------------------
    # Serverless platforms only allow writes inside /tmp, so a hosted
    # deployment should point CLINIC_DATABASE_URL at a managed database.
    database_url: str = _env(
        "CLINIC_DATABASE_URL",
        f"sqlite:///{(PROJECT_ROOT / 'clinic.db').as_posix()}",
    )

    # --- Behaviour ------------------------------------------------------
    seed_on_startup: bool = _env_bool("CLINIC_SEED_ON_STARTUP", True)

    # --- CORS -----------------------------------------------------------
    cors_origins: list[str] = _env_list(
        "CLINIC_CORS_ORIGINS",
        [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ],
    )
    # Matches Vercel production and preview deployments.
    cors_origin_regex: str = _env(
        "CLINIC_CORS_ORIGIN_REGEX",
        r"https://.*\.vercel\.app",
    )

    # --- Clinic diary ---------------------------------------------------
    slots: tuple[time, ...] = (
        time(9, 0),
        time(10, 0),
        time(11, 0),
        time(14, 0),
        time(15, 0),
        time(16, 0),
    )

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()

# Kept as a module level name because the routers read it directly.
AVAILABLE_SLOTS: list[time] = list(settings.slots)
