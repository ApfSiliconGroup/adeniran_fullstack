export type UserRole = "patient" | "doctor" | "receptionist";

export type User = { id: number; username: string; role: UserRole };
export type Token = { access_token: string; token_type: string };
export type Doctor = { id: number; name: string; speciality: string };
export type Appointment = {
  id: number;
  patient_id: number;
  doctor_id: number;
  appointment_date: string;
  appointment_time: string;
  status: string;
  note: string | null;
};

export type ApiError = { detail?: string };