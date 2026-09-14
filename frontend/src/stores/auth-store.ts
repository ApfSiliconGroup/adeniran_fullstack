/**
 * The session store.
 *
 * Zustand owns the session (token, user, doctor profile) and persists it to
 * local storage; TanStack Query owns everything else the server knows. The
 * store is the only writer of the bearer token used by `lib/api/client.ts`.
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { setAuthToken, setUnauthorizedHandler } from "@/lib/api/client";
import type { DoctorPublic, SessionProfile, Token, UserPublic } from "@/types/api";

export const SESSION_STORAGE_KEY = "adeniran.clinic.session";

type SessionStatus = "loading" | "authenticated" | "anonymous";

interface AuthState {
  token: string | null;
  /** Epoch milliseconds. The backend token lasts 60 minutes by default. */
  expiresAt: number | null;
  user: UserPublic | null;
  doctor: DoctorPublic | null;
  /** False until local storage has been read, to avoid an SSR mismatch. */
  hydrated: boolean;
  /** Set when a session ends by itself, so the sign-in page can explain why. */
  expiredNotice: boolean;

  signIn: (token: Token) => void;
  signOut: (options?: { expired?: boolean }) => void;
  applyProfile: (profile: SessionProfile) => void;
  markHydrated: () => void;
  clearExpiredNotice: () => void;
  status: () => SessionStatus;
}

function isLive(expiresAt: number | null): boolean {
  return expiresAt === null || expiresAt > Date.now();
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      expiresAt: null,
      user: null,
      doctor: null,
      hydrated: false,
      expiredNotice: false,

      signIn: (token) => {
        setAuthToken(token.access_token);
        set({
          token: token.access_token,
          expiresAt: Date.now() + token.expires_in * 1000,
          user: token.user,
          doctor: null,
          expiredNotice: false,
        });
      },

      signOut: (options) => {
        setAuthToken(null);
        set({
          token: null,
          expiresAt: null,
          user: null,
          doctor: null,
          expiredNotice: options?.expired ?? false,
        });
      },

      /** Reconciles the cached user with `GET /auth/me`. */
      applyProfile: (profile) =>
        set({ user: profile.user, doctor: profile.doctor }),

      markHydrated: () => set({ hydrated: true }),

      clearExpiredNotice: () => set({ expiredNotice: false }),

      status: () => {
        const { hydrated, token, expiresAt } = get();
        if (!hydrated) return "loading";
        return token && isLive(expiresAt) ? "authenticated" : "anonymous";
      },
    }),
    {
      name: SESSION_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      version: 2,
      partialize: (state) => ({
        token: state.token,
        expiresAt: state.expiresAt,
        user: state.user,
        doctor: state.doctor,
      }),
      onRehydrateStorage: () => (state, error) => {
        if (error || !state) {
          useAuthStore.setState({ hydrated: true });
          return;
        }
        // A token restored from a previous visit may already have expired;
        // drop it here rather than letting the first request fail with a 401.
        if (state.token && isLive(state.expiresAt)) {
          setAuthToken(state.token);
          useAuthStore.setState({ hydrated: true });
        } else {
          setAuthToken(null);
          useAuthStore.setState({
            hydrated: true,
            token: null,
            expiresAt: null,
            user: null,
            doctor: null,
          });
        }
      },
    },
  ),
);

// One 401 from an authenticated request means the token died server side.
setUnauthorizedHandler(() => {
  if (useAuthStore.getState().token) {
    useAuthStore.getState().signOut({ expired: true });
  }
});

// --- Selectors -------------------------------------------------------------
// Each returns a stable primitive or object reference so components using them
// only re-render when that slice actually changes.

export const selectToken = (state: AuthState) => state.token;
export const selectUser = (state: AuthState) => state.user;
export const selectDoctor = (state: AuthState) => state.doctor;
export const selectHydrated = (state: AuthState) => state.hydrated;
export const selectRole = (state: AuthState) => state.user?.role ?? null;

export const selectIsAuthenticated = (state: AuthState) =>
  state.hydrated && Boolean(state.token) && isLive(state.expiresAt);
