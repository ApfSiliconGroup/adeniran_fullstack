"""Vercel serverless entry point for the Adeniran Street Clinic API.

The `@vercel/python` runtime imports this module and looks for a module
level `app` (an ASGI application) or `handler`, so both names are exported
below and point at the same `FastAPI` instance defined in `app/main.py`.

Routing
-------
The root `vercel.json` sends `/api/*`, `/docs*` and `/openapi.json` to this
function and everything else to the Next.js build in `frontend/`. Vercel
forwards the *original* request path, so a call to `/api/patients/register`
arrives here as `/api/patients/register` even though the router declares
`/patients/register`. Declaring `root_path = "/api"` lets Starlette strip
that mount prefix, so the very same code answers on `/api/...` behind
Vercel and on `/...` when it is run directly with uvicorn.

Storage
-------
The Vercel filesystem is read-only apart from `/tmp`, and `/tmp` is wiped
whenever the underlying instance is recycled. The bundled `clinic.db` is
therefore not writable in production: point `CLINIC_DATABASE_URL` at a
managed database (for example a Postgres connection string) so that
registrations, bookings and consultation notes actually persist. A value of
`sqlite:////tmp/clinic.db` will boot, but it is only suitable for a
throwaway demo - every cold start begins from an empty database.
"""

from app.main import app

# This function is mounted under /api by the root vercel.json.
app.root_path = "/api"

# Vercel accepts either name; keep both bound to the same ASGI app.
handler = app

__all__ = ["app", "handler"]
