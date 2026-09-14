"use client";

/** Front desk data: the day's diary, capacity, the patient list and the audit trail. */

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { receptionApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import type {
  AppointmentStatus,
  IsoDate,
  ReceptionBookingPayload,
  RegisterPayload,
} from "@/types/api";

export function useDiary(date: IsoDate, status?: AppointmentStatus) {
  return useQuery({
    queryKey: queryKeys.appointments.diary(date, status),
    queryFn: () => receptionApi.diary(date, status),
    placeholderData: keepPreviousData,
  });
}

export function useDiaryOverview(date: IsoDate) {
  return useQuery({
    queryKey: queryKeys.reception.overview(date),
    queryFn: () => receptionApi.overview(date),
    placeholderData: keepPreviousData,
  });
}

export function useReceptionPatients(search?: string) {
  return useQuery({
    queryKey: queryKeys.reception.patients(search),
    queryFn: () => receptionApi.patients({ search }),
    placeholderData: keepPreviousData,
  });
}

export function useReceptionDoctors() {
  return useQuery({
    queryKey: queryKeys.doctors.list("reception"),
    queryFn: receptionApi.doctors,
    staleTime: 10 * 60 * 1000,
  });
}

export function useAccessLogs(limit = 50) {
  return useQuery({
    queryKey: queryKeys.reception.accessLogs(),
    queryFn: () => receptionApi.accessLogs(limit),
  });
}

function useDeskInvalidator() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.appointments.all,
    });
    void queryClient.invalidateQueries({ queryKey: queryKeys.reception.all });
    void queryClient.invalidateQueries({ queryKey: queryKeys.doctors.all });
  };
}

export function useCancelAnyAppointment() {
  const invalidate = useDeskInvalidator();
  return useMutation({
    mutationFn: (id: number) => receptionApi.cancel(id),
    onSuccess: invalidate,
  });
}

export function useRegisterWalkIn() {
  const invalidate = useDeskInvalidator();
  return useMutation({
    mutationFn: (payload: RegisterPayload) =>
      receptionApi.registerWalkIn({
        username: payload.username.trim(),
        password: payload.password,
        full_name: payload.full_name?.trim() || undefined,
      }),
    onSuccess: invalidate,
  });
}

export function useReceptionBooking() {
  const invalidate = useDeskInvalidator();
  return useMutation({
    mutationFn: (payload: ReceptionBookingPayload) =>
      receptionApi.book(payload),
    onSuccess: invalidate,
  });
}
