import { create } from "zustand";
import type { User, UserRole } from "./types";

type AuthState = {
  token: string | null;
  user: User | null;
  hydrate: () => void;
  setSession: (token: string) => void;
  logout: () => void;
};

function decodeUser(token: string): User {
  const payload = JSON.parse(atob(token.split(".")[1])) as { sub: string; role: UserRole };
  return { id: Number(payload.sub), username: "Clinic member", role: payload.role };
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  hydrate: () => {
    const token = window.localStorage.getItem("adeniran_token");
    if (!token) return;
    try { set({ token, user: decodeUser(token) }); } catch { window.localStorage.removeItem("adeniran_token"); }
  },
  setSession: (token) => {
    window.localStorage.setItem("adeniran_token", token);
    set({ token, user: decodeUser(token) });
  },
  logout: () => {
    window.localStorage.removeItem("adeniran_token");
    set({ token: null, user: null });
  },
}));