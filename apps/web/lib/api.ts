import { API_BASE_URL } from "@/lib/site";

/** Shape of an RFC 9457 problem-details error from the API. */
export interface ApiError {
  code: string;
  title: string;
  detail: string;
  status: number;
  errors?: { field: string; message: string }[];
}

export class ApiRequestError extends Error {
  constructor(public problem: ApiError) {
    super(problem.detail || problem.title);
    this.name = "ApiRequestError";
  }
}

/**
 * Thin fetch wrapper for the Tailrd API.
 *
 * - Sends cookies (credentials: include) so the httpOnly session works.
 * - Attaches the CSRF token from the readable cookie on mutating requests.
 * - Normalises errors into ApiRequestError with a stable machine code.
 */
export async function api<T = unknown>(
  path: string,
  options: RequestInit & { json?: unknown } = {},
): Promise<T> {
  const { json, headers, ...rest } = options;
  const method = (rest.method ?? (json ? "POST" : "GET")).toUpperCase();

  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string>),
  };

  if (json !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
  }

  // CSRF double-submit: echo the readable cookie into a header.
  if (method !== "GET" && method !== "HEAD" && typeof document !== "undefined") {
    const csrf = document.cookie
      .split("; ")
      .find((c) => c.startsWith("tailrd_csrf="))
      ?.split("=")[1];
    if (csrf) finalHeaders["X-CSRF-Token"] = decodeURIComponent(csrf);
  }

  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...rest,
    method,
    headers: finalHeaders,
    credentials: "include",
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  if (!res.ok) {
    let problem: ApiError;
    try {
      problem = await res.json();
    } catch {
      problem = {
        code: "network_error",
        title: "Request failed",
        detail: `Request failed with status ${res.status}.`,
        status: res.status,
      };
    }
    throw new ApiRequestError(problem);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
