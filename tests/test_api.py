"""End to end tests for the Adeniran Street Clinic API.

Every test drives the real FastAPI app over a real SQLite database. There
are no mocks: a "the patient cannot read someone else's note" test really
signs two patients in and really asks for the note.
"""

from __future__ import annotations

CLINIC_SLOTS = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]


# ==========================================================================
# Public endpoints
# ==========================================================================
def test_home_advertises_the_api(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Welcome to Adeniran Street Clinic Booking API"
    assert body["docs"] == "/docs"
    assert body["roles"] == ["patient", "doctor", "receptionist"]


def test_health_reports_the_database_is_reachable(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "reachable"


def test_public_doctors_lists_the_four_seeded_doctors(client):
    response = client.get("/public/doctors")

    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) == 4
    assert [doctor["name"] for doctor in doctors] == [
        "Dr. Ada Okafor",
        "Dr. Emeka Nwosu",
        "Dr. Tunde Adeyemi",
        "Dr. Zainab Bello",
    ]


def test_public_doctors_can_be_filtered_by_speciality(client):
    response = client.get("/public/doctors", params={"speciality": "Cardiology"})

    assert response.status_code == 200
    doctors = response.json()
    assert len(doctors) == 1
    assert doctors[0]["name"] == "Dr. Zainab Bello"


def test_public_specialities_lists_every_speciality_sorted(client):
    response = client.get("/public/specialities")

    assert response.status_code == 200
    assert response.json() == [
        "Cardiology",
        "Dermatology",
        "General Medicine",
        "Pediatrics",
    ]


def test_public_stats_report_the_clinic_headline_numbers(client, db_session):
    from sqlmodel import func, select

    from app.models import COMPLETED, Appointment

    response = client.get("/public/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["doctors"] == 4
    assert stats["slots_per_day"] == len(CLINIC_SLOTS)
    assert stats["specialities"] == [
        "Cardiology",
        "Dermatology",
        "General Medicine",
        "Pediatrics",
    ]
    completed = db_session.exec(
        select(func.count(Appointment.id)).where(
            Appointment.status == COMPLETED
        )
    ).one()
    assert stats["consultations_completed"] == completed


# ==========================================================================
# Seeding
# ==========================================================================
def test_seeding_creates_exactly_four_doctors(db_session):
    from sqlmodel import func, select

    from app.models import Doctor

    assert db_session.exec(select(func.count(Doctor.id))).one() == 4


def test_seeding_creates_exactly_two_receptionists(db_session):
    from sqlmodel import func, select

    from app.models import RECEPTIONIST, User

    count = db_session.exec(
        select(func.count(User.id)).where(User.role == RECEPTIONIST)
    ).one()
    assert count == 2


def test_seeding_adds_the_cardiologist_and_the_dermatologist(client):
    doctors = client.get("/public/doctors").json()
    by_name = {doctor["name"]: doctor for doctor in doctors}

    assert by_name["Dr. Zainab Bello"]["speciality"] == "Cardiology"
    assert by_name["Dr. Zainab Bello"]["consulting_room"] == "Room 3"
    assert by_name["Dr. Tunde Adeyemi"]["speciality"] == "Dermatology"
    assert by_name["Dr. Tunde Adeyemi"]["consulting_room"] == "Room 4"


def test_seeding_adds_the_second_receptionist(client, auth):
    from tests.conftest import SEEDED_SECOND_RECEPTIONIST, sign_in

    token = sign_in(client, *SEEDED_SECOND_RECEPTIONIST)
    profile = client.get("/auth/me", headers=auth(token)).json()

    assert profile["user"]["username"] == "reception_grace"
    assert profile["user"]["full_name"] == "Grace Uzoma"
    assert profile["user"]["role"] == "receptionist"


# ==========================================================================
# Authentication
# ==========================================================================
def test_signup_returns_a_usable_token(client, auth, new_patient):
    account = new_patient(full_name="Silicon Group")

    assert account["user"]["role"] == "patient"
    assert account["user"]["full_name"] == "Silicon Group"

    me = client.get("/auth/me", headers=auth(account["token"]))
    assert me.status_code == 200
    assert me.json()["user"]["username"] == account["username"]


def test_signup_with_a_duplicate_username_is_rejected(client, new_patient):
    account = new_patient()

    response = client.post(
        "/auth/register",
        json={
            "username": account["username"],
            "password": "another-password",
            "full_name": "Impostor",
        },
    )

    assert response.status_code == 409
    assert "already taken" in response.json()["detail"]


def test_sign_in_with_the_wrong_password_is_rejected(client):
    response = client.post(
        "/auth/token",
        data={"username": "patient_david", "password": "not-my-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_auth_me_returns_the_signed_in_patient(client, auth, patient_token):
    response = client.get("/auth/me", headers=auth(patient_token))

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "patient_david"
    assert body["user"]["role"] == "patient"
    assert body["doctor"] is None


def test_auth_me_returns_the_doctor_profile_for_a_doctor(
    client,
    auth,
    doctor_token,
):
    response = client.get("/auth/me", headers=auth(doctor_token))

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "doctor_ada"
    assert body["user"]["role"] == "doctor"
    assert body["doctor"]["name"] == "Dr. Ada Okafor"
    assert body["doctor"]["speciality"] == "General Medicine"


# ==========================================================================
# Role based access control
# ==========================================================================
def test_patient_cannot_open_the_doctor_diary(client, auth, patient_token):
    response = client.get(
        "/doctors/appointments",
        headers=auth(patient_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Only the doctor role can perform this action."
    )


def test_doctor_cannot_open_the_patient_appointment_list(
    client,
    auth,
    doctor_token,
):
    response = client.get(
        "/patients/appointments",
        headers=auth(doctor_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Only the patient role can perform this action."
    )


def test_patient_cannot_open_the_front_desk_diary(
    client,
    auth,
    patient_token,
    future_date,
):
    response = client.get(
        "/receptionist/diary",
        params={"appointment_date": future_date},
        headers=auth(patient_token),
    )

    assert response.status_code == 403


def test_a_request_with_no_token_is_unauthorised(client):
    response = client.get("/patients/appointments")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


# ==========================================================================
# Booking
# ==========================================================================
def test_a_fresh_clinic_day_offers_every_slot(
    free_slots,
    patient_token,
    doctor_id,
    future_date,
):
    assert free_slots(patient_token, doctor_id, future_date) == CLINIC_SLOTS


def test_patient_books_a_free_slot(
    book,
    patient_token,
    doctor_id,
    future_date,
):
    response = book(patient_token, doctor_id, future_date, "10:00")

    assert response.status_code == 201
    appointment = response.json()
    assert appointment["status"] == "booked"
    assert appointment["appointment_date"] == future_date
    assert appointment["appointment_time"] == "10:00:00"
    assert appointment["doctor_name"] == "Dr. Ada Okafor"
    assert appointment["patient_name"] == "David Orji"
    assert appointment["reason"] == "Persistent headache for four days."


def test_patient_cannot_book_a_taken_slot(
    book,
    new_patient,
    doctor_id,
    booked_appointment,
    future_date,
):
    rival = new_patient()

    response = book(rival["token"], doctor_id, future_date, "09:00")

    assert response.status_code == 409
    assert response.json()["detail"] == "That doctor slot is already booked."


def test_patient_cannot_book_a_time_outside_the_clinic_slots(
    book,
    patient_token,
    doctor_id,
    future_date,
):
    response = book(patient_token, doctor_id, future_date, "09:30")

    assert response.status_code == 422
    assert "not one of the clinic's available time slots" in (
        response.json()["detail"]
    )


def test_patient_cannot_book_a_date_in_the_past(
    book,
    patient_token,
    doctor_id,
    past_date,
):
    response = book(patient_token, doctor_id, past_date, "09:00")

    assert response.status_code == 422
    assert response.json()["detail"] == "You cannot book a slot in the past."


def test_a_booked_slot_disappears_from_free_slots(
    book,
    free_slots,
    patient_token,
    doctor_id,
    future_date,
):
    assert "11:00" in free_slots(patient_token, doctor_id, future_date)

    assert book(patient_token, doctor_id, future_date, "11:00").status_code == 201

    assert "11:00" not in free_slots(patient_token, doctor_id, future_date)


def test_patient_lists_their_own_appointment(
    client,
    auth,
    patient_token,
    booked_appointment,
):
    response = client.get(
        "/patients/appointments",
        params={"status": "booked"},
        headers=auth(patient_token),
    )

    assert response.status_code == 200
    identifiers = [item["id"] for item in response.json()]
    assert booked_appointment["id"] in identifiers


# ==========================================================================
# Consultation notes
# ==========================================================================
def test_doctor_sees_the_booking_on_their_diary(
    client,
    auth,
    doctor_token,
    booked_appointment,
    future_date,
):
    response = client.get(
        "/doctors/appointments",
        params={"appointment_date": future_date},
        headers=auth(doctor_token),
    )

    assert response.status_code == 200
    diary = response.json()
    assert [item["id"] for item in diary] == [booked_appointment["id"]]
    assert diary[0]["patient_name"] == "David Orji"


def test_doctor_writes_a_note_on_their_own_appointment(
    written_note,
    booked_appointment,
    doctor_id,
):
    assert written_note["appointment_id"] == booked_appointment["id"]
    assert written_note["doctor_id"] == doctor_id
    assert written_note["patient_id"] == booked_appointment["patient_id"]
    assert written_note["doctor_name"] == "Dr. Ada Okafor"
    assert written_note["body"] == (
        "Blood pressure 120/80. Advised rest and fluids."
    )


def test_patient_reads_the_note_on_their_appointment(
    client,
    auth,
    patient_token,
    booked_appointment,
    written_note,
):
    response = client.get(
        f"/notes/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )

    assert response.status_code == 200
    notes = response.json()
    assert [note["id"] for note in notes] == [written_note["id"]]
    assert notes[0]["body"] == written_note["body"]


def test_another_patient_cannot_read_someone_elses_note(
    client,
    auth,
    other_patient_token,
    booked_appointment,
    written_note,
):
    response = client.get(
        f"/notes/appointments/{booked_appointment['id']}",
        headers=auth(other_patient_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You are not allowed to read notes for this appointment."
    )


def test_receptionist_only_sees_the_redacted_note_body(
    client,
    auth,
    reception_token,
    booked_appointment,
    written_note,
):
    from app.routers.notes import HIDDEN_BODY

    response = client.get(
        f"/notes/appointments/{booked_appointment['id']}",
        headers=auth(reception_token),
    )

    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 1
    assert notes[0]["id"] == written_note["id"]
    assert notes[0]["body"] == HIDDEN_BODY


def test_note_author_can_correct_their_note(
    client,
    auth,
    doctor_token,
    written_note,
):
    response = client.patch(
        f"/notes/{written_note['id']}",
        headers=auth(doctor_token),
        json={"body": "Correction: blood pressure 130/85. Review in a week."},
    )

    assert response.status_code == 200
    assert response.json()["body"] == (
        "Correction: blood pressure 130/85. Review in a week."
    )


def test_doctor_cannot_write_a_note_on_another_doctors_appointment(
    client,
    auth,
    other_doctor_token,
    booked_appointment,
):
    response = client.post(
        f"/notes/appointments/{booked_appointment['id']}",
        headers=auth(other_doctor_token),
        json={"body": "Not my patient."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can only write notes for your own appointments."
    )


def test_notes_mine_returns_the_doctors_own_notes(
    client,
    auth,
    doctor_token,
    written_note,
):
    response = client.get("/notes/mine", headers=auth(doctor_token))

    assert response.status_code == 200
    assert written_note["id"] in [note["id"] for note in response.json()]


def test_notes_mine_returns_the_patients_own_notes(
    client,
    auth,
    patient_token,
    written_note,
):
    response = client.get("/notes/mine", headers=auth(patient_token))

    assert response.status_code == 200
    assert written_note["id"] in [note["id"] for note in response.json()]


def test_notes_mine_is_closed_to_the_front_desk(client, auth, reception_token):
    response = client.get("/notes/mine", headers=auth(reception_token))

    assert response.status_code == 403


# ==========================================================================
# Completing a consultation
# ==========================================================================
def test_doctor_completes_an_appointment_and_a_note_is_stored(
    client,
    auth,
    doctor_token,
    booked_appointment,
):
    response = client.patch(
        f"/doctors/appointments/{booked_appointment['id']}/complete",
        headers=auth(doctor_token),
        json={"note": "Consultation completed. Review in two weeks."},
    )

    assert response.status_code == 200
    appointment = response.json()
    assert appointment["status"] == "completed"
    assert appointment["note"] == (
        "Consultation completed. Review in two weeks."
    )
    assert appointment["note_count"] >= 1


def test_completion_note_is_readable_by_the_patient(
    client,
    auth,
    doctor_token,
    patient_token,
    booked_appointment,
):
    client.patch(
        f"/doctors/appointments/{booked_appointment['id']}/complete",
        headers=auth(doctor_token),
        json={"note": "Consultation completed. Review in two weeks."},
    )

    response = client.get(
        f"/notes/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )

    assert response.status_code == 200
    bodies = [note["body"] for note in response.json()]
    assert "Consultation completed. Review in two weeks." in bodies


def test_an_appointment_cannot_be_completed_twice(
    client,
    auth,
    doctor_token,
    booked_appointment,
):
    first = client.patch(
        f"/doctors/appointments/{booked_appointment['id']}/complete",
        headers=auth(doctor_token),
        json={"note": "All done."},
    )
    assert first.status_code == 200

    second = client.patch(
        f"/doctors/appointments/{booked_appointment['id']}/complete",
        headers=auth(doctor_token),
        json={"note": "All done again."},
    )

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "Only booked appointments can be completed."
    )


def test_doctor_cannot_complete_another_doctors_appointment(
    client,
    auth,
    other_doctor_token,
    booked_appointment,
):
    response = client.patch(
        f"/doctors/appointments/{booked_appointment['id']}/complete",
        headers=auth(other_doctor_token),
        json={"note": "Not mine to finish."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can only complete your own appointments."
    )


# ==========================================================================
# Cancelling
# ==========================================================================
def test_patient_cancels_their_own_appointment(
    client,
    auth,
    patient_token,
    booked_appointment,
):
    response = client.delete(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_an_appointment_cannot_be_cancelled_twice(
    client,
    auth,
    patient_token,
    booked_appointment,
):
    first = client.delete(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )
    assert first.status_code == 200

    second = client.delete(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "This appointment is already cancelled and cannot be cancelled."
    )


def test_another_patient_cannot_cancel_your_appointment(
    client,
    auth,
    other_patient_token,
    booked_appointment,
):
    response = client.delete(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(other_patient_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "You can only cancel your own appointment."
    )


def test_receptionist_can_cancel_any_booked_appointment(
    client,
    auth,
    reception_token,
    booked_appointment,
):
    response = client.delete(
        f"/receptionist/appointments/{booked_appointment['id']}",
        headers=auth(reception_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_a_cancelled_slot_is_free_again(
    client,
    auth,
    free_slots,
    patient_token,
    doctor_id,
    booked_appointment,
    future_date,
):
    assert "09:00" not in free_slots(patient_token, doctor_id, future_date)

    client.delete(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )

    assert "09:00" in free_slots(patient_token, doctor_id, future_date)


# ==========================================================================
# Front desk
# ==========================================================================
def test_receptionist_diary_shows_the_whole_clinic_day(
    client,
    auth,
    reception_token,
    booked_appointment,
    future_date,
):
    response = client.get(
        "/receptionist/diary",
        params={"appointment_date": future_date},
        headers=auth(reception_token),
    )

    assert response.status_code == 200
    diary = response.json()
    assert [item["id"] for item in diary] == [booked_appointment["id"]]
    assert diary[0]["doctor_name"] == "Dr. Ada Okafor"


def test_receptionist_overview_reports_utilisation(
    client,
    auth,
    reception_token,
    booked_appointment,
    future_date,
):
    response = client.get(
        "/receptionist/overview",
        params={"appointment_date": future_date},
        headers=auth(reception_token),
    )

    assert response.status_code == 200
    overview = response.json()
    assert overview["appointment_date"] == future_date
    assert overview["total"] == 1
    assert overview["booked"] == 1
    assert overview["cancelled"] == 0
    assert overview["doctors_on_duty"] == 1
    assert overview["slots_per_doctor"] == len(CLINIC_SLOTS)
    assert 0 <= overview["utilisation"] <= 100


def test_receptionist_registers_a_walk_in_who_can_then_sign_in(
    client,
    auth,
    reception_token,
):
    from tests.conftest import sign_in

    response = client.post(
        "/receptionist/walk-in",
        headers=auth(reception_token),
        json={
            "username": "walkin_ngozi",
            "password": "walkin100",
            "full_name": "Ngozi Eze",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["role"] == "patient"
    assert created["full_name"] == "Ngozi Eze"

    token = sign_in(client, "walkin_ngozi", "walkin100")
    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["user"]["id"] == created["id"]


def test_receptionist_books_on_behalf_of_a_patient(
    client,
    auth,
    reception_token,
    patient_id,
    doctor_id,
    future_date,
):
    response = client.post(
        "/receptionist/appointments",
        headers=auth(reception_token),
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": future_date,
            "appointment_time": "14:00",
            "reason": "Phoned the front desk.",
        },
    )

    assert response.status_code == 201
    appointment = response.json()
    assert appointment["patient_id"] == patient_id
    assert appointment["doctor_id"] == doctor_id
    assert appointment["appointment_time"] == "14:00:00"
    assert appointment["status"] == "booked"
    assert appointment["reason"] == "Phoned the front desk."


def test_receptionist_booking_obeys_the_clinic_slot_rule(
    client,
    auth,
    reception_token,
    patient_id,
    doctor_id,
    future_date,
):
    response = client.post(
        "/receptionist/appointments",
        headers=auth(reception_token),
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": future_date,
            "appointment_time": "09:30",
        },
    )

    assert response.status_code == 422
    assert "not one of the clinic's available time slots" in (
        response.json()["detail"]
    )


def test_receptionist_lists_patients_and_can_search_them(
    client,
    auth,
    reception_token,
):
    everyone = client.get(
        "/receptionist/patients",
        headers=auth(reception_token),
    )
    assert everyone.status_code == 200
    usernames = [person["username"] for person in everyone.json()]
    assert "patient_david" in usernames
    assert "patient_amaka" in usernames
    assert all(person["role"] == "patient" for person in everyone.json())

    search = client.get(
        "/receptionist/patients",
        params={"search": "amaka"},
        headers=auth(reception_token),
    )
    assert search.status_code == 200
    assert [person["username"] for person in search.json()] == [
        "patient_amaka"
    ]


def test_receptionist_lists_the_clinic_doctors(
    client,
    auth,
    reception_token,
):
    response = client.get(
        "/receptionist/doctors",
        headers=auth(reception_token),
    )

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_access_logs_are_limited_to_the_front_desk(
    client,
    auth,
    patient_token,
):
    response = client.get(
        "/receptionist/access-logs",
        headers=auth(patient_token),
    )

    assert response.status_code == 403


# ==========================================================================
# Audit trail
# ==========================================================================
def test_opening_an_appointment_writes_an_access_log_row(
    client,
    auth,
    patient_token,
    patient_id,
    reception_token,
    booked_appointment,
):
    read = client.get(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )
    assert read.status_code == 200

    logs = client.get(
        "/receptionist/access-logs",
        params={"limit": 200},
        headers=auth(reception_token),
    )
    assert logs.status_code == 200

    matching = [
        row
        for row in logs.json()
        if row["appointment_id"] == booked_appointment["id"]
    ]
    assert len(matching) == 1
    assert matching[0]["user_id"] == patient_id
    assert matching[0]["action"] == "patient record opened"


def test_cancelling_writes_its_own_access_log_row(
    client,
    auth,
    patient_token,
    reception_token,
    booked_appointment,
):
    cancelled = client.delete(
        f"/patients/appointments/{booked_appointment['id']}",
        headers=auth(patient_token),
    )
    assert cancelled.status_code == 200

    logs = client.get(
        "/receptionist/access-logs",
        params={"limit": 200},
        headers=auth(reception_token),
    )

    actions = [
        row["action"]
        for row in logs.json()
        if row["appointment_id"] == booked_appointment["id"]
    ]
    assert actions == ["patient cancelled appointment"]
