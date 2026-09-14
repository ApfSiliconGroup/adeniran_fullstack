/**
 * Mirrors `app/schemas.py` on the FastAPI side, field for field.
 *
 * If an endpoint changes shape, change it here first - every hook and screen
 * is typed off this file, so the compiler will point at what needs updating.
 */

export type UserRole = "patient" | "doctor" | "receptionist";

export type AppointmentStatus = "booked" | "completed" | "cancelled";

/** `YYYY-MM-DD`, as the API sends and expects it. */
export type IsoDate = string;
/** `HH:MM:SS`, as the API sends it. */
export type IsoTime = string;

export interface UserPublic {
  id: number;
  username: string;
  full_name: string;
  role: UserRole;
  created_at: string | null;
}

export interface DoctorPublic {
  id: number;
  name: string;
  speciality: string;
  bio: string;
  years_experience: number;
  consulting_room: string;
  is_accepting: boolean;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserPublic;
}

export interface SessionProfile {
  user: UserPublic;
  doctor: DoctorPublic | null;
}

export interface Appointment {
  id: number;
  patient_id: number;
  doctor_id: number;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
  status: AppointmentStatus;
  note: string | null;
  reason: string;
  created_at: string | null;
  patient_name: string;
  doctor_name: string;
  doctor_speciality: string;
  note_count: number;
}

export interface ConsultationNote {
  id: number;
  appointment_id: number;
  doctor_id: number;
  patient_id: number;
  body: string;
  created_at: string;
  updated_at: string;
  doctor_name: string;
  patient_name: string;
  appointment_date: IsoDate | null;
  appointment_time: IsoTime | null;
}

export interface AccessLogEntry {
  id: number;
  user_id: number;
  appointment_id: number;
  action: string;
  created_at: string;
}

export interface DiaryOverview {
  appointment_date: IsoDate;
  total: number;
  booked: number;
  completed: number;
  cancelled: number;
  doctors_on_duty: number;
  slots_per_doctor: number;
  /** Whole-number percent, 0-100. */
  utilisation: number;
}

export interface ClinicStats {
  doctors: number;
  specialities: string[];
  slots_per_day: number;
  consultations_completed: number;
}

export interface ApiMessage {
  message: string;
}

export interface HealthStatus {
  status: string;
  database: string;
  version: string;
  time: string;
}

// --- Request payloads ------------------------------------------------------

export interface RegisterPayload {
  username: string;
  password: string;
  full_name?: string;
}

export interface BookingPayload {
  doctor_id: number;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
  reason?: string;
}

export interface ReceptionBookingPayload extends BookingPayload {
  patient_id: number;
}
