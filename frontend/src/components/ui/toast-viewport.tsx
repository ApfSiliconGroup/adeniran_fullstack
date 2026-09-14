"use client";

import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";
import { useEffect } from "react";
import { useUiStore, type Toast } from "@/stores/ui-store";

const TONE_ICON = {
  success: CheckCircle2,
  error: TriangleAlert,
  info: Info,
} as const;

const TONE_CLASS = {
  success: "alert-success",
  error: "alert-error",
  info: "alert-info",
} as const;

const DISMISS_AFTER = 5000;

function ToastCard({ toast }: { toast: Toast }) {
  const dismissToast = useUiStore((state) => state.dismissToast);
  const Icon = TONE_ICON[toast.tone];

  useEffect(() => {
    const timer = window.setTimeout(
      () => dismissToast(toast.id),
      DISMISS_AFTER,
    );
    return () => window.clearTimeout(timer);
  }, [toast.id, dismissToast]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 24, scale: 0.97 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className={`alert ${TONE_CLASS[toast.tone]} rounded-box w-full items-start gap-3 shadow-lg`}
    >
      <Icon size={18} aria-hidden className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug font-semibold">{toast.title}</p>
        {toast.description ? (
          <p className="mt-0.5 text-xs leading-relaxed opacity-90">
            {toast.description}
          </p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={() => dismissToast(toast.id)}
        className="btn btn-ghost btn-xs btn-circle -mt-1 -mr-1"
        aria-label="Dismiss notification"
      >
        <X size={14} aria-hidden />
      </button>
    </motion.div>
  );
}

export function ToastViewport() {
  const toasts = useUiStore((state) => state.toasts);

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-100 flex flex-col items-center gap-2 p-4 sm:inset-x-auto sm:right-0 sm:bottom-0 sm:items-end sm:p-6"
    >
      <div className="pointer-events-auto flex w-full max-w-sm flex-col gap-2">
        <AnimatePresence initial={false}>
          {toasts.map((toast) => (
            <ToastCard key={toast.id} toast={toast} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
