"use client";

/** Session reads and the three session mutations: sign in, sign up, sign out. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { authApi } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query-keys";
import {
  selectDoctor,
  selectHydrated,
  selectIsAuthenticated,
  selectUser,
  useAuthStore,
} from "@/stores/auth-store";
import type { RegisterPayload, UserRole } from "@/types/api";

export interface Session {
  user: ReturnType<typeof selectUser>;
  doctor: ReturnType<typeof selectDoctor>;
  role: UserRole | null;
  /** Full name when we have one, otherwise the username. */
  displayName: string;
  isAuthenticated: boolean;
  /** False until local storage has been read. Render a skeleton until true. */
  hydrated: boolean;
}

export function useSession(): Session {
  const user = useAuthStore(selectUser);
  const doctor = useAuthStore(selectDoctor);
  const hydrated = useAuthStore(selectHydrated);
  const isAuthenticated = useAuthStore(selectIsAuthenticated);

  // Storage rehydration should be immediate, but a blocked browser storage
  // implementation must never leave the application on an infinite loader.
  useEffect(() => {
    const fallback = window.setTimeout(() => {
      if (!useAuthStore.getState().hydrated) {
        useAuthStore.getState().markHydrated();
      }
    }, 500);
    return () => window.clearTimeout(fallback);
  }, []);

  return {
    user,
    doctor,
    role: user?.role ?? null,
    displayName: user?.full_name?.trim() || user?.username || "Clinic member",
    isAuthenticated,
    hydrated,
  };
}

/**
 * Reconciles the persisted session against the server on mount.
 *
 * The token carries a role, but the display name and the doctor profile come
 * from `GET /auth/me` - the previous version of this app had to invent a
 * placeholder name because no such endpoint existed.
 */
export function useSyncProfile(): void {
  const isAuthenticated = useAuthStore(selectIsAuthenticated);
  const applyProfile = useAuthStore((state) => state.applyProfile);

  const { data } = useQuery({
    queryKey: queryKeys.session,
    queryFn: authApi.me,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (data) applyProfile(data);
  }, [data, applyProfile]);
}

export function useLogin() {
  const signIn = useAuthStore((state) => state.signIn);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      username,
      password,
    }: {
      username: string;
      password: string;
    }) => authApi.login(username.trim(), password),
    onSuccess: async (token) => {
      signIn(token);
      // Anything cached for a previous visitor must not leak into this one.
      queryClient.clear();
      await queryClient.prefetchQuery({
        queryKey: queryKeys.session,
        queryFn: authApi.me,
      });
    },
  });
}

export function useSignup() {
  const signIn = useAuthStore((state) => state.signIn);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: RegisterPayload) =>
      authApi.register({
        username: payload.username.trim(),
        password: payload.password,
        full_name: payload.full_name?.trim() || undefined,
      }),
    onSuccess: async (token) => {
      signIn(token);
      queryClient.clear();
      await queryClient.prefetchQuery({
        queryKey: queryKeys.session,
        queryFn: authApi.me,
      });
    },
  });
}

export function useLogout(): () => void {
  const signOut = useAuthStore((state) => state.signOut);
  const queryClient = useQueryClient();

  return () => {
    signOut();
    queryClient.clear();
  };
}
