# Adeniran Street Clinic frontend contract

The FastAPI backend is the source of truth. The frontend does not create a user profile endpoint or infer unsupported metrics.

| Feature | Method and endpoint | Auth / role | Payload / response |
| --- | --- | --- | --- |
| Login | `POST /auth/token` | Public | OAuth2 form fields `username`, `password`; returns `access_token`, `token_type` |
| Patient registration / signup | `POST /patients/register` | Public | `{ username, password }`; returns user `{ id, username, role }`. The frontend signs the patient in immediately afterward. |
| Find doctors | `GET /patients/doctors` | Bearer / patient | Optional `speciality`; returns doctor `{ id, name, speciality }[]` |
| Free appointment slots | `GET /patients/doctors/{doctor_id}/free-slots?appointment_date=YYYY-MM-DD` | Bearer / patient | Returns `time[]` |
| Book appointment | `POST /patients/appointments` | Bearer / patient | `{ doctor_id, appointment_date, appointment_time }`; returns appointment |
| Patient appointments | `GET /patients/appointments` | Bearer / patient | Returns the current patient's appointments |
| Appointment detail | `GET /patients/appointments/{appointment_id}` | Bearer / patient | Returns appointment; backend writes the access log as a background task |
| Cancel own appointment | `DELETE /patients/appointments/{appointment_id}` | Bearer / patient | Returns the cancelled appointment |
| Doctor day | `GET /doctors/appointments?appointment_date=YYYY-MM-DD` | Bearer / doctor | Returns that doctor's appointments for the date |
| Complete appointment and write note | `PATCH /doctors/appointments/{appointment_id}/complete` | Bearer / doctor only | `{ note }`; returns completed appointment. The backend rejects non-doctors and whitespace-only notes. |
| Receptionist diary | `GET /receptionist/diary?appointment_date=YYYY-MM-DD` | Bearer / receptionist | Returns all appointments for the date |
| Cancel any appointment | `DELETE /receptionist/appointments/{appointment_id}` | Bearer / receptionist | Returns the cancelled appointment |
| Register walk-in | `POST /receptionist/walk-in` | Bearer / receptionist | `{ username, password }`; returns the new patient user |

## Authentication

The token is stored in browser local storage under `adeniran_token`. The client decodes only the JWT `sub` and `role` claims to render the session, and attaches the original token as `Authorization: Bearer <token>` to protected requests. Passwords are never persisted or logged. The backend token expires after 60 minutes.

## Role matrix

| Role | Available frontend workflows |
| --- | --- |
| Patient | Find doctors, inspect free slots, book, list, view through the backend-supported appointment flows, and cancel own booked appointments |
| Doctor | Review own appointments for today and complete a booked appointment with a required note |
| Receptionist | Review today's diary, cancel booked appointments, and register walk-in patients |

The backend has no endpoint for listing patients, reading doctor profiles for doctors, listing access logs, or returning current-user details. Those screens are intentionally not fabricated.

## Local setup

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to the FastAPI origin. Run the backend from the repository root with `.venv\Scripts\uvicorn.exe app.main:app --reload`.

Seeded development accounts are `patient_david` / `patient123`, `doctor_ada` / `doctor123`, `doctor_emeka` / `doctor123`, and `reception_joy` / `reception123`.