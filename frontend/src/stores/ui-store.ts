/**
 * Presentation state: the colour theme, the mobile drawer and the toast queue.
 * None of it belongs to the server, so none of it belongs in React Query.
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export const THEME_STORAGE_KEY = "adeniran.clinic.ui";

export type ThemeName = "clinic" | "clinicnight";

export type ToastTone = "success" | "error" | "info";

export interface Toast {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
}

interface UiState {
  theme: ThemeName;
  sidebarOpen: boolean;
  toasts: Toast[];

  setTheme: (theme: ThemeName) => void;
  toggleTheme: () => void;
  setSidebarOpen: (open: boolean) => void;
  pushToast: (toast: Omit<Toast, "id">) => number;
  dismissToast: (id: number) => void;
}

let toastId = 0;

export const useUiStore = create<UiState>()(
  persist(
    (set, get) => ({
      theme: "clinic",
      sidebarOpen: false,
      toasts: [],

      setTheme: (theme) => {
        set({ theme });
        if (typeof document !== "undefined") {
          document.documentElement.dataset.theme = theme;
        }
      },

      toggleTheme: () =>
        get().setTheme(get().theme === "clinic" ? "clinicnight" : "clinic"),

      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      pushToast: (toast) => {
        toastId += 1;
        const id = toastId;
        set((state) => ({ toasts: [...state.toasts, { ...toast, id }] }));
        return id;
      },

      dismissToast: (id) =>
        set((state) => ({
          toasts: state.toasts.filter((toast) => toast.id !== id),
        })),
    }),
    {
      name: THEME_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      // The drawer and the toast queue are per-visit state.
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        if (state?.theme && typeof document !== "undefined") {
          document.documentElement.dataset.theme = state.theme;
        }
      },
    },
  ),
);
