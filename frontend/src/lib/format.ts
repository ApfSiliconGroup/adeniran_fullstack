/**
 * Formatting helpers shared by every screen.
 *
 * Dates from the API are date-only strings. `new Date("2026-09-15")` parses
 * those as UTC midnight, which renders as the previous day for anyone west of
 * Greenwich - so everything here goes through date-fns `parseISO`, which
 * treats a date-only string as local time.
 */

import {
  differenceInCalendarDays,
  format,
  formatDistanceToNowStrict,
  isValid,
  parseISO,
} from "date-fns";
import type { AppointmentStatus, IsoDate, IsoTime, UserRole } from "@/types/api";

export function todayIso(): IsoDate {
  return format(new Date(), "yyyy-MM-dd");
}

export function addDaysIso(iso: IsoDate, days: number): IsoDate {
  const parsed = parseISO(iso);
  if (!isValid(parsed)) return iso;
  parsed.setDate(parsed.getDate() + days);
  return format(parsed, "yyyy-MM-dd");
}

function safeParse(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const parsed = parseISO(iso);
  return isValid(parsed) ? parsed : null;
}

/** "15 September 2026" */
export function formatDateLong(iso: IsoDate | null | undefined): string {
  const parsed = safeParse(iso);
  return parsed ? format(parsed, "d MMMM yyyy") : "-";
}

/** "Tue 15 Sep" */
export function formatDateShort(iso: IsoDate | null | undefined): string {
  const parsed = safeParse(iso);
  return parsed ? format(parsed, "EEE d MMM") : "-";
}

/** "Sep" - the month strip on a date tile. */
export function monthShort(iso: IsoDate | null | undefined): string {
  const parsed = safeParse(iso);
  return parsed ? format(parsed, "MMM") : "-";
}

/** "15" - the day number on a date tile. */
export function dayOfMonth(iso: IsoDate | null | undefined): string {
  const parsed = safeParse(iso);
  return parsed ? format(parsed, "d") : "-";
}

export function weekdayName(iso: IsoDate | null | undefined): string {
  const parsed = safeParse(iso);
  return parsed ? format(parsed, "EEEE") : "-";
}

/** "09:00:00" -> "9:00 am" */
export function formatTime(time: IsoTime | null | undefined): string {
  if (!time) return "-";
  const [rawHour, rawMinute] = time.split(":");
  const hour = Number(rawHour);
  const minute = Number(rawMinute ?? "0");
  if (Number.isNaN(hour) || Number.isNaN(minute)) return time;
  const suffix = hour < 12 ? "am" : "pm";
  const display = hour % 12 === 0 ? 12 : hour % 12;
  return `${display}:${String(minute).padStart(2, "0")} ${suffix}`;
}

/** "09:00:00" -> "09:00", for <option> values and compact tables. */
export function shortTime(time: IsoTime | null | undefined): string {
  return time ? time.slice(0, 5) : "-";
}

/** "Today", "Tomorrow", "In 4 days", "3 days ago". */
export function relativeDay(iso: IsoDate | null | undefined): string {
  const parsed = safeParse(iso);
  if (!parsed) return "-";
  const delta = differenceInCalendarDays(parsed, new Date());
  if (delta === 0) return "Today";
  if (delta === 1) return "Tomorrow";
  if (delta === -1) return "Yesterday";
  if (delta > 1) return `In ${delta} days`;
  return `${Math.abs(delta)} days ago`;
}

/** "4 hours ago" - for note timestamps and the audit trail. */
export function timeAgo(timestamp: string | null | undefined): string {
  const parsed = safeParse(timestamp);
  if (!parsed) return "-";
  return `${formatDistanceToNowStrict(parsed)} ago`;
}

export function formatTimestamp(timestamp: string | null | undefined): string {
  const parsed = safeParse(timestamp);
  return parsed ? format(parsed, "d MMM yyyy, HH:mm") : "-";
}

export function isPastDate(iso: IsoDate): boolean {
  const parsed = safeParse(iso);
  if (!parsed) return false;
  return differenceInCalendarDays(parsed, new Date()) < 0;
}

/** "Dr. Ada Okafor" -> "AO" */
export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  const parts = name
    .replace(/^(dr\.?|mr\.?|mrs\.?|ms\.?)\s+/i, "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

/** 1284 -> "1,284"; 12900 -> "12.9K". Stat tile values only. */
export function compactNumber(value: number): string {
  if (!Number.isFinite(value)) return "-";
  if (Math.abs(value) < 10_000) return value.toLocaleString("en-GB");
  return new Intl.NumberFormat("en-GB", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function roleLabel(role: UserRole): string {
  if (role === "patient") return "Patient";
  if (role === "doctor") return "Doctor";
  return "Receptionist";
}

/** The home route for each role, used after sign-in and by the guard. */
export function roleHome(role: UserRole): string {
  if (role === "patient") return "/patient";
  if (role === "doctor") return "/doctor";
  return "/reception";
}

export type StatusTone = "info" | "success" | "muted";

export interface StatusMeta {
  label: string;
  tone: StatusTone;
  /** daisyUI badge classes. Never the only signal - pair with the icon. */
  badgeClass: string;
  dotClass: string;
}

const STATUS_META: Record<AppointmentStatus, StatusMeta> = {
  booked: {
    label: "Booked",
    tone: "info",
    badgeClass: "badge-info",
    dotClass: "bg-info",
  },
  completed: {
    label: "Completed",
    tone: "success",
    badgeClass: "badge-success",
    dotClass: "bg-success",
  },
  cancelled: {
    label: "Cancelled",
    tone: "muted",
    badgeClass: "badge-ghost",
    dotClass: "bg-base-content/40",
  },
};

export function statusMeta(status: AppointmentStatus | string): StatusMeta {
  return (
    STATUS_META[status as AppointmentStatus] ?? {
      label: status || "Unknown",
      tone: "muted",
      badgeClass: "badge-ghost",
      dotClass: "bg-base-content/40",
    }
  );
}

/**
 * Severity for the capacity meter. The fill carries the severity while the
 * track stays a lighter step of the same ramp, so the state reads across the
 * whole bar rather than only in the filled part.
 */
export function utilisationSeverity(percent: number): {
  label: string;
  fillClass: string;
  trackClass: string;
} {
  if (percent >= 85) {
    return {
      label: "Nearly full",
      fillClass: "bg-error",
      trackClass: "bg-error/15",
    };
  }
  if (percent >= 60) {
    return {
      label: "Busy",
      fillClass: "bg-warning",
      trackClass: "bg-warning/20",
    };
  }
  return {
    label: "Comfortable",
    fillClass: "bg-primary",
    trackClass: "bg-primary/15",
  };
}
