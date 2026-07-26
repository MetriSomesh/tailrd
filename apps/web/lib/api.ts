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
 * Base path for API calls. We go through the Next.js same-origin proxy
 * (`/api/backend/* → ${API}/api/v1/*`, see next.config.ts) rather than hitting
 * the API host directly. This keeps the auth cookies first-party, so they are
 * sent and stored without running into third-party-cookie restrictions.
 */
const API_PREFIX = "/api/backend";

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

  const res = await fetch(`${API_PREFIX}${path}`, {
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

// ===========================================================================
// Types — mirror the FastAPI response models.
// ===========================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  auth_provider: string;
  email_verified: boolean;
  created_at: string;
}

export interface UsageSummary {
  has_subscription: boolean;
  subscription_plan: string | null;
  subscription_ends: string | null;
  credit_balance: number;
  free_used: number;
  free_limit: number;
  free_remaining: number;
  period: string;
}

export type RunStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface RunSummary {
  id: string;
  status: RunStatus;
  jd_label: string | null;
  company: string | null;
  role: string | null;
  overall_score: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface ScoreJson {
  overall_score: number;
  keyword_match_pct: number;
  skills_match_pct: number;
  term_overlap_pct: number;
  experience_relevance_pct: number;
  matched_keywords: string[];
  missing_keywords: string[];
  skills_matched: string[];
  skills_missing: string[];
  responsibilities_covered: string[];
  responsibilities_uncovered: string[];
}

export interface RunDetail extends RunSummary {
  jd_text: string | null;
  tailored_json: Record<string, unknown> | null;
  score_json: ScoreJson | null;
  parsability_json: Record<string, unknown> | null;
  iterations: number;
  error_code: string | null;
  error_message: string | null;
  docx_storage_key: string | null;
}

export interface TailorResponse {
  run_id: string;
  status: RunStatus;
  message: string;
}

export interface OrderResponse {
  order_id: string;
  amount_paise: number;
  currency: string;
  key_id: string;
}

export interface SubscriptionResponse {
  subscription_id: string;
  plan: string;
  status: string;
  period_end: string;
}

// ===========================================================================
// Typed endpoint helpers.
// ===========================================================================

export const getMe = () => api<User>("/auth/me");
export const logout = () => api<{ message: string }>("/auth/logout", { method: "POST" });

export const getUsage = () => api<UsageSummary>("/billing/usage");
export const listRuns = () => api<RunSummary[]>("/runs");
export const getRun = (id: string) => api<RunDetail>(`/runs/${id}`);

export const submitTailor = (body: {
  jd_text: string;
  company?: string;
  role?: string;
}) => api<TailorResponse>("/tailor", { json: body });

export const createCreditOrder = () => api<OrderResponse>("/billing/orders", { method: "POST" });
export const confirmPayment = (body: {
  order_id: string;
  payment_id: string;
  signature: string;
}) => api<{ credits_granted: number; new_balance: number }>("/billing/confirm", { json: body });
export const createSubscription = (plan: "weekly" | "monthly") =>
  api<SubscriptionResponse>("/billing/subscriptions", { json: { plan } });
export const cancelSubscription = () =>
  api<{ message: string; period_end: string }>("/billing/cancel", { method: "POST" });

/** Direct URL for the DOCX download (goes through the same-origin proxy). */
export const downloadRunUrl = (id: string) => `${API_PREFIX}/runs/${id}/download`;
