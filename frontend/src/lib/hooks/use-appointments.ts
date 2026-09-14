"use client";

/**
 * Appointment reads and mutations for both the patient and doctor sides.
 *
 * Mutations invalidate whole branches of the key tree rather than patching
 * individual entries, because the backend decides status transitions and slot
 * availability - re-reading is always correct, guessing is not.
 */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { doctorApi, patientApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import type {
  AppointmentStatus,
  BookingPayload,
  IsoDate,
} from "@/types/api";

// --- Patient ---------------------------------------------------------------

export function usePatientAppointments(status?: AppointmentStatus) {
  return useQuery({
    queryKey: queryKeys.appointments.patient(status),
    queryFn: () => patientApi.appointments(status),
    placeholderData: keepPreviousData,
  });
}

export function usePatientDoctors(speciality?: string) {
  return useQuery({
    queryKey: queryKeys.doctors.list("patient", speciality),
    queryFn: () => patientApi.doctors(speciality),
    staleTime: 5 * 60 * 1000,
  });
}

/** Open slots for one doctor on one day. Disabled until a doctor is chosen. */
export function useFreeSlots(doctorId: number | null, date: IsoDate) {
  return useQuery({
    queryKey: queryKeys.doctors.freeSlots(doctorId, date),
    queryFn: () => patientApi.freeSlots(doctorId as number, date),
    enabled: doctorId !== null && Boolean(date),
    placeholderData: keepPreviousData,
    // Slots go stale the moment somebody else books, so never serve a cache.
    staleTime: 0,
  });
}

export function useBookAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: BookingPayload) => patientApi.book(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.appointments.all,
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.doctors.all });
    },
  });
}

export function useCancelPatientAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => patientApi.cancel(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.appointments.all,
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.doctors.all });
    },
  });
}

// --- Doctor ----------------------------------------------------------------

export function useDoctorProfile(enabled = true) {
  return useQuery({
    queryKey: queryKeys.doctors.profile(),
    queryFn: doctorApi.profile,
    enabled,
    staleTime: 10 * 60 * 1000,
  });
}

/** Pass no date to load the doctor's whole diary rather than a single day. */
export function useDoctorAppointments(
  appointmentDate?: IsoDate,
  status?: AppointmentStatus,
) {
  return useQuery({
    queryKey: queryKeys.appointments.doctor(appointmentDate, status),
    queryFn: () => doctorApi.appointments({ appointmentDate, status }),
    placeholderData: keepPreviousData,
  });
}

export function useCompleteAppointment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) =>
      doctorApi.complete(id, note),
    onSuccess: (appointment) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.appointments.all,
      });
      // Completing a visit also files a consultation note.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notes.forAppointment(appointment.id),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.notes.mine() });
    },
  });
}
