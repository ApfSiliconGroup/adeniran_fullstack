"use client";

/** Toast helper, so screens never touch the ui store's queue directly. */

import { useCallback } from "react";
import { useUiStore } from "@/stores/ui-store";
import { ApiError } from "@/lib/api/client";

export interface ToastApi {
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  /** Shows the backend's `detail` sentence when there is one. */
  fromError: (caught: unknown, fallback?: string) => void;
}

export function useToast(): ToastApi {
  const pushToast = useUiStore((state) => state.pushToast);

  const success = useCallback(
    (title: string, description?: string) => {
      pushToast({ tone: "success", title, description });
    },
    [pushToast],
  );

  const error = useCallback(
    (title: string, description?: string) => {
      pushToast({ tone: "error", title, description });
    },
    [pushToast],
  );

  const info = useCallback(
    (title: string, description?: string) => {
      pushToast({ tone: "info", title, description });
    },
    [pushToast],
  );

  const fromError = useCallback(
    (caught: unknown, fallback = "That action could not be completed.") => {
      const message =
        caught instanceof ApiError
          ? caught.message
          : caught instanceof Error && caught.message
            ? caught.message
            : fallback;
      pushToast({ tone: "error", title: message });
    },
    [pushToast],
  );

  return { success, error, info, fromError };
}
