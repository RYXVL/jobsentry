/**
 * Low-level fetch wrapper. All requests go through `request()` so error
 * handling is identical everywhere: any failure becomes an ApiError with a
 * machine-readable `code` the UI can react to.
 */
import type { ApiErrorBody } from "./types";

/** Relative, so it goes through the Vite dev proxy (see vite.config.ts). */
export const API_BASE = "/api/v1";

/** Codes the frontend adds on top of the backend's own error codes. */
export const API_UNREACHABLE = "api_unreachable";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const UNREACHABLE_MESSAGE = "Can't reach the jobsentry API.";

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(API_BASE + path, { ...init, headers });
  } catch {
    throw new ApiError(0, API_UNREACHABLE, UNREACHABLE_MESSAGE);
  }

  if (response.ok) {
    return (await response.json()) as T;
  }

  const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
  if (body?.error) {
    throw new ApiError(response.status, body.error.code, body.error.message);
  }
  // No JSON error body: the dev proxy couldn't reach the backend.
  if (response.status >= 500) {
    throw new ApiError(response.status, API_UNREACHABLE, UNREACHABLE_MESSAGE);
  }
  throw new ApiError(response.status, "http_error", `Request failed with status ${response.status}.`);
}

/** Build a query string, skipping empty values. Arrays become repeated keys
 *  (country=CA&country=US), which is how FastAPI reads list parameters. */
export function toQueryString(params: object): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const values: unknown[] = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== undefined && item !== null && item !== "") {
        search.append(key, String(item));
      }
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}