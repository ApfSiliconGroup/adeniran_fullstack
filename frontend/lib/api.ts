import type { ApiError, Appointment, Doctor, Token, User } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiRequestError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData) && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = (await response.json()) as ApiError;
      if (body.detail) message = body.detail;
    } catch { /* Keep the friendly fallback for non-JSON errors. */ }
    throw new ApiRequestError(response.status, message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    return request<Token>("/auth/token", { method: "POST", body });
  },
  registerPatient: (username: string, password: string) =>
    request<User>("/patients/register", { method: "POST", body: JSON.stringify({ username, password }) }),
  doctors: (token: string, speciality?: string) =>
    request<Doctor[]>(`/patients/doctors${speciality ? `?speciality=${encodeURIComponent(speciality)}` : ""}`, {}, token),
  freeSlots: (token: string, doctorId: number, date: string) =>
    request<string[]>(`/patients/doctors/${doctorId}/free-slots?appointment_date=${date}`, {}, token),
  patientAppointments: (token: string) => request<Appointment[]>("/patients/appointments", {}, token),
  book: (token: string, data: { doctor_id: number; appointment_date: string; appointment_time: string }) =>
    request<Appointment>("/patients/appointments", { method: "POST", body: JSON.stringify(data) }, token),
  cancelPatientAppointment: (token: string, id: number) =>
    request<Appointment>(`/patients/appointments/${id}`, { method: "DELETE" }, token),
  doctorAppointments: (token: string, date: string) =>
    request<Appointment[]>(`/doctors/appointments?appointment_date=${date}`, {}, token),
  complete: (token: string, id: number, note: string) =>
    request<Appointment>(`/doctors/appointments/${id}/complete`, { method: "PATCH", body: JSON.stringify({ note }) }, token),
  diary: (token: string, date: string) => request<Appointment[]>(`/receptionist/diary?appointment_date=${date}`, {}, token),
  cancelAnyAppointment: (token: string, id: number) =>
    request<Appointment>(`/receptionist/appointments/${id}`, { method: "DELETE" }, token),
  walkIn: (token: string, username: string, password: string) =>
    request<User>("/receptionist/walk-in", { method: "POST", body: JSON.stringify({ username, password }) }, token),
};