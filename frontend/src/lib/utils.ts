/** Tiny class-name joiner. Keeps a clsx dependency out of the bundle. */
export function cn(
  ...values: Array<string | false | null | undefined>
): string {
  return values.filter(Boolean).join(" ");
}

/** Motion presets, so every surface in the app enters the same way. */
export const motionPresets = {
  fadeUp: {
    initial: { opacity: 0, y: 14 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.42, ease: [0.22, 1, 0.36, 1] as const },
  },
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.3 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.97 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.97 },
    transition: { duration: 0.22, ease: [0.22, 1, 0.36, 1] as const },
  },
} as const;

/** Stagger children of a list without repeating the delay maths. */
export function staggerDelay(index: number, step = 0.05): number {
  return Math.min(index * step, 0.4);
}
