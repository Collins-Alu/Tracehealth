/**
 * HTTP client for the TraceHealth API.
 *
 * Adds the access token, refreshes it once when the API answers 401 (even
 * when several requests fail at the same moment), and turns failures into
 * ApiError (the server answered) or NetworkError (it didn't).
 *
 * Tokens are kept in sessionStorage: they disappear when the browser tab is
 * closed, which suits shared office computers. They are never put in a URL.
 */
import type { TokenResponse, User } from '@/types/api';

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '');

export class NetworkError extends Error {
  constructor() {
    super('network');
    this.name = 'NetworkError';
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const KEYS = { access: 'th.access', refresh: 'th.refresh', user: 'th.user' };

function store(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export const session = {
  access: () => store()?.getItem(KEYS.access) ?? null,
  refresh: () => store()?.getItem(KEYS.refresh) ?? null,
  user(): User | null {
    const raw = store()?.getItem(KEYS.user);
    try {
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  },
  save(tokens: TokenResponse) {
    store()?.setItem(KEYS.access, tokens.access_token);
    store()?.setItem(KEYS.refresh, tokens.refresh_token);
    store()?.setItem(KEYS.user, JSON.stringify(tokens.user));
  },
  clear() {
    Object.values(KEYS).forEach((k) => store()?.removeItem(k));
  },
};

/** Plain-language message from a FastAPI error body. */
export function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg).replace(/^Value error, /, '');
  }
  return fallback;
}

let onExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null) {
  onExpired = handler;
}

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const token = session.refresh();
      if (!token) return false;
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: token }),
      }).catch(() => {
        throw new NetworkError();
      });
      if (!res.ok) return false;
      session.save((await res.json()) as TokenResponse);
      return true;
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  json?: unknown;
  form?: FormData;
  auth?: boolean;
  /** Return the raw Response (for files) instead of parsed JSON. */
  raw?: boolean;
  /** Treat these error statuses as normal answers (e.g. 422 import report). */
  acceptStatus?: number[];
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  let body: BodyInit | undefined;
  if (opts.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.json);
  } else if (opts.form) {
    body = opts.form;
  }
  const token = session.access();
  if (opts.auth !== false && token) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(`${API_URL}${path}`, { method: opts.method ?? 'GET', headers, body });
  } catch {
    throw new NetworkError();
  }
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res = await send(path, opts);
  if (res.status === 401 && opts.auth !== false) {
    if (!(await refreshTokens())) {
      session.clear();
      onExpired?.();
      throw new ApiError(401, 'session_expired');
    }
    res = await send(path, opts);
  }
  if (opts.raw && res.ok) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : undefined;
  } catch {
    data = text;
  }
  if (!res.ok && !opts.acceptStatus?.includes(res.status)) {
    throw new ApiError(res.status, errorMessage(data, `HTTP ${res.status}`), data);
  }
  return data as T;
}

/** Build "?a=1&b=2", leaving out empty values. */
export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}
