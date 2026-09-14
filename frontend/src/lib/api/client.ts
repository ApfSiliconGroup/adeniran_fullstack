/**
 * The single fetch layer for the whole app.
 *
 * Everything the UI knows about HTTP lives here: the base URL, the bearer
 * token, error shaping and the 401 recovery path. Screens call the typed
 * helpers in `endpoints.ts` and never touch `fetch` directly.
 */

const RAW_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** No trailing slash, so `${API_BASE_URL}${path}` is always well formed. */
export const API_BASE_URL = RAW_BASE.replace(/\/+$/, "");

/**
 * The token lives in a module variable rather than being read from storage on
 * every call. `auth-store` is the only writer - see `setAuthToken`.
 */
let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

/** Registered by the auth store so an expired token signs the user out once. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  /** True when the request never reached the API. */
  get isOffline(): boolean {
    return this.status === 0;
  }
}

type QueryValue = string | number | boolean | null | undefined;

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  /** Serialised as JSON. */
  json?: unknown;
  /** Serialised as `application/x-www-form-urlencoded` (the token endpoint). */
  form?: Record<string, string>;
  query?: Record<string, QueryValue>;
  /** Attach the bearer token. Defaults to true. */
  auth?: boolean;
  signal?: AbortSignal;
}

function buildQuery(query: Record<string, QueryValue> | undefined): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const serialised = params.toString();
  return serialised ? `?${serialised}` : "";
}

const FALLBACK_MESSAGE = "Something went wrong. Please try again.";
const OFFLINE_MESSAGE =
  "We could not reach the clinic server. Check your connection and try again.";

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      // FastAPI's raw validation shape, in case a handler bypasses ours.
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as { msg?: unknown };
        if (typeof first?.msg === "string") return first.msg;
      }
    }
  } catch {
    // Not JSON - fall through to the status based message below.
  }
  if (response.status === 404) return "We could not find what you asked for.";
  if (response.status >= 500) {
    return "The clinic server had a problem. Please try again shortly.";
  }
  return FALLBACK_MESSAGE;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", json, form, query, auth = true, signal } = options;

  const headers = new Headers({ Accept: "application/json" });
  let body: BodyInit | undefined;

  if (form) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
    body = new URLSearchParams(form);
  } else if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }

  if (auth && authToken) {
    headers.set("Authorization", `Bearer ${authToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}${buildQuery(query)}`, {
      method,
      headers,
      body,
      signal,
      cache: "no-store",
    });
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === "AbortError") {
      throw caught;
    }
    throw new ApiError(0, OFFLINE_MESSAGE);
  }

  if (!response.ok) {
    const message = await readErrorMessage(response);
    // Only an authenticated 401 means the session died; a failed sign-in
    // attempt is also a 401 and must not trigger a sign-out loop.
    if (response.status === 401 && auth && authToken) {
      onUnauthorized?.();
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}
