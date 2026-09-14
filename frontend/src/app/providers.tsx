"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { ToastViewport } from "@/components/ui/toast-viewport";
import { useUiStore } from "@/stores/ui-store";

function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30 * 1000,
        gcTime: 5 * 60 * 1000,
        refetchOnWindowFocus: false,
        // Retrying a 401/403/404/409 just repeats a decision the backend has
        // already made. Only network and 5xx failures are worth another go.
        retry: (failureCount, error) => {
          if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
            return false;
          }
          return failureCount < 2;
        },
        retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/** Keeps `<html data-theme>` in step with the persisted theme choice. */
function ThemeSync() {
  const theme = useUiStore((state) => state.theme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme =
      theme === "clinicnight" ? "dark" : "light";
  }, [theme]);

  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  // One client per browser session, never recreated by a re-render.
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeSync />
      {children}
      <ToastViewport />
    </QueryClientProvider>
  );
}
