/**
 * Every backend endpoint, as a typed function.
 *
 * Grouped by the role that owns it, which mirrors the FastAPI routers:
 * public / auth / patients / doctors / notes / receptionist.
 */

import { apiRequest } from "./client";
import type {
  AccessLogEntry,
  Appointment,
  AppointmentStatus,
  ClinicStats,
  ConsultationNote,
  DiaryOverview,
  DoctorPublic,
  HealthStatus,
  IsoDate,
  IsoTime,
  ApiMessage,
  BookingPayload,
  ReceptionBookingPayload,
  RegisterPayload,
  SessionProfile,
  Token,
  UserPublic,
} from "@/types/api";

export const publicApi = {
  health: () => apiRequest<HealthStatus>("/health", { auth: false }),

  doctors: (speciality?: string) =>
    apiRequest<DoctorPublic[]>("/public/doctors", {
      auth: false,
      query: { speciality },
    }),

  specialities: () =>
    apiRequest<string[]>("/public/specialities", { auth: false }),

  stats: () => apiRequest<ClinicStats>("/public/stats", { auth: false }),
};

export const authApi = {
  /** Public patient signup. Returns a token, so the user lands signed in. */
  register: (payload: RegisterPayload) =>
    apiRequest<Token>("/auth/register", {
      method: "POST",
      json: payload,
      auth: false,
    }),

  /** OAuth2 password flow - the backend expects form encoding, not JSON. */
  login: (username: string, password: string) =>
    apiRequest<Token>("/auth/token", {
      method: "POST",
      form: { username, password },
      auth: false,
    }),

  me: () => apiRequest<SessionProfile>("/auth/me"),
};

export const patientApi = {
  doctors: (speciality?: string) =>
    apiRequest<DoctorPublic[]>("/patients/doctors", { query: { speciality } }),

  freeSlots: (doctorId: number, appointmentDate: IsoDate) =>
    apiRequest<IsoTime[]>(`/patients/doctors/${doctorId}/free-slots`, {
      query: { appointment_date: appointmentDate },
    }),

  appointments: (status?: AppointmentStatus) =>
    apiRequest<Appointment[]>("/patients/appointments", { query: { status } }),

  appointment: (id: number) =>
    apiRequest<Appointment>(`/patients/appointments/${id}`),

  book: (payload: BookingPayload) =>
    apiRequest<Appointment>("/patients/appointments", {
      method: "POST",
      json: payload,
    }),

  cancel: (id: number) =>
    apiRequest<Appointment>(`/patients/appointments/${id}`, {
      method: "DELETE",
    }),
};

export const doctorApi = {
  profile: () => apiRequest<DoctorPublic>("/doctors/me"),

  /** Omit the date to load the doctor's whole diary. */
  appointments: (params: {
    appointmentDate?: IsoDate;
    status?: AppointmentStatus;
  } = {}) =>
    apiRequest<Appointment[]>("/doctors/appointments", {
      query: {
        appointment_date: params.appointmentDate,
        status: params.status,
      },
    }),

  appointment: (id: number) =>
    apiRequest<Appointment>(`/doctors/appointments/${id}`),

  /** Closes the visit and files the summary as a consultation note too. */
  complete: (id: number, note: string) =>
    apiRequest<Appointment>(`/doctors/appointments/${id}/complete`, {
      method: "PATCH",
      json: { note },
    }),
};

export const notesApi = {
  forAppointment: (appointmentId: number) =>
    apiRequest<ConsultationNote[]>(`/notes/appointments/${appointmentId}`),

  create: (appointmentId: number, body: string) =>
    apiRequest<ConsultationNote>(`/notes/appointments/${appointmentId}`, {
      method: "POST",
      json: { body },
    }),

  update: (noteId: number, body: string) =>
    apiRequest<ConsultationNote>(`/notes/${noteId}`, {
      method: "PATCH",
      json: { body },
    }),

  remove: (noteId: number) =>
    apiRequest<ApiMessage>(`/notes/${noteId}`, { method: "DELETE" }),

  /** Doctors get the notes they wrote; patients get the notes about them. */
  mine: (limit = 50) => apiRequest<ConsultationNote[]>("/notes/mine", {
    query: { limit },
  }),
};

export const receptionApi = {
  diary: (appointmentDate: IsoDate, status?: AppointmentStatus) =>
    apiRequest<Appointment[]>("/receptionist/diary", {
      query: { appointment_date: appointmentDate, status },
    }),

  overview: (appointmentDate: IsoDate) =>
    apiRequest<DiaryOverview>("/receptionist/overview", {
      query: { appointment_date: appointmentDate },
    }),

  book: (payload: ReceptionBookingPayload) =>
    apiRequest<Appointment>("/receptionist/appointments", {
      method: "POST",
      json: payload,
    }),

  cancel: (id: number) =>
    apiRequest<Appointment>(`/receptionist/appointments/${id}`, {
      method: "DELETE",
    }),

  registerWalkIn: (payload: RegisterPayload) =>
    apiRequest<UserPublic>("/receptionist/walk-in", {
      method: "POST",
      json: payload,
    }),

  patients: (params: { search?: string; limit?: number } = {}) =>
    apiRequest<UserPublic[]>("/receptionist/patients", {
      query: { search: params.search, limit: params.limit },
    }),

  doctors: () => apiRequest<DoctorPublic[]>("/receptionist/doctors"),

  accessLogs: (limit = 50) =>
    apiRequest<AccessLogEntry[]>("/receptionist/access-logs", {
      query: { limit },
    }),
};
