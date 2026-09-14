/**
 * One place for every React Query key.
 *
 * Keys are hierarchical so a mutation can invalidate a whole branch, e.g.
 * `queryClient.invalidateQueries({ queryKey: queryKeys.appointments.all })`.
 */

import type { AppointmentStatus, IsoDate } from "@/types/api";

export const queryKeys = {
  session: ["session"] as const,

  clinic: {
    all: ["clinic"] as const,
    health: () => ["clinic", "health"] as const,
    stats: () => ["clinic", "stats"] as const,
    specialities: () => ["clinic", "specialities"] as const,
  },

  doctors: {
    all: ["doctors"] as const,
    list: (scope: "public" | "patient" | "reception", speciality?: string) =>
      ["doctors", "list", scope, speciality ?? "all"] as const,
    profile: () => ["doctors", "profile"] as const,
    freeSlots: (doctorId: number | null, date: IsoDate) =>
      ["doctors", "free-slots", doctorId, date] as const,
  },

  appointments: {
    all: ["appointments"] as const,
    patient: (status?: AppointmentStatus) =>
      ["appointments", "patient", status ?? "all"] as const,
    doctor: (date?: IsoDate, status?: AppointmentStatus) =>
      ["appointments", "doctor", date ?? "all", status ?? "all"] as const,
    diary: (date: IsoDate, status?: AppointmentStatus) =>
      ["appointments", "diary", date, status ?? "all"] as const,
    detail: (id: number) => ["appointments", "detail", id] as const,
  },

  notes: {
    all: ["notes"] as const,
    forAppointment: (appointmentId: number) =>
      ["notes", "appointment", appointmentId] as const,
    mine: () => ["notes", "mine"] as const,
  },

  reception: {
    all: ["reception"] as const,
    overview: (date: IsoDate) => ["reception", "overview", date] as const,
    patients: (search?: string) =>
      ["reception", "patients", search ?? "all"] as const,
    accessLogs: () => ["reception", "access-logs"] as const,
  },
} as const;
