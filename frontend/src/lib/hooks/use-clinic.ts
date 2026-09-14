"use client";

/** Public clinic data: the doctor directory, specialities and headline stats. */

import { useQuery } from "@tanstack/react-query";
import { publicApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";

const HOUR = 60 * 60 * 1000;

export function usePublicDoctors(speciality?: string) {
  return useQuery({
    queryKey: queryKeys.doctors.list("public", speciality),
    queryFn: () => publicApi.doctors(speciality),
    staleTime: 5 * 60 * 1000,
  });
}

export function useSpecialities() {
  return useQuery({
    queryKey: queryKeys.clinic.specialities(),
    queryFn: publicApi.specialities,
    staleTime: HOUR,
  });
}

export function useClinicStats() {
  return useQuery({
    queryKey: queryKeys.clinic.stats(),
    queryFn: publicApi.stats,
    staleTime: 5 * 60 * 1000,
  });
}

export function useApiHealth() {
  return useQuery({
    queryKey: queryKeys.clinic.health(),
    queryFn: publicApi.health,
    staleTime: 30 * 1000,
    retry: 1,
  });
}
