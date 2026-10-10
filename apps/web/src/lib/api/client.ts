export interface RequestOptions extends RequestInit {
  token?: string | null;
  idempotencyKey?: string;
  params?: Record<string, string | number | boolean | null | undefined>;
}

export class ApiResponseError extends Error {
  status: number;
  code: string;
  details: unknown[];
  requestId: string;
  constructor(status: number, code: string, message: string, details: unknown[], requestId: string) {
    super(message);
    this.name = 'ApiResponseError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export function parseErrorEnvelope(status: number, data: unknown, requestId = 'unknown') {
  const raw = data && typeof data === 'object' ? data as Record<string, unknown> : {};
  return new ApiResponseError(status, typeof raw.code === 'string' ? raw.code : 'HTTP_ERROR',
    typeof raw.message === 'string' ? raw.message : `Request failed (HTTP ${status}). Please retry.`,
    Array.isArray(raw.details) ? raw.details : [], typeof raw.request_id === 'string' ? raw.request_id : requestId);
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { token, idempotencyKey, params, ...init } = options;
  const base = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null) query.set(key, String(value));
  }
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey);
  headers.set('X-Request-ID', crypto.randomUUID());
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const res = await fetch(`${base.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}${query.size ? `?${query}` : ''}`, { ...init, headers, cache: 'no-store' });
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null);
    if (res.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('campuscue:unauthenticated', { detail: token }));
    throw parseErrorEnvelope(res.status, body, res.headers.get('X-Request-ID') ?? 'unknown');
  }
  return res.status === 204 ? undefined as T : await res.json() as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiResponseError ? `${error.message} (request ${error.requestId})` : error instanceof Error ? error.message : 'Request unavailable. Please retry.';
}
