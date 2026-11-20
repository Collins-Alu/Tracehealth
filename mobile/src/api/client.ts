/**
 * HTTP client for the TraceHealth API.
 *
 * It does three jobs so screens don't have to:
 *  1. Adds "Authorization: Bearer <access token>" to requests.
 *  2. When the API answers 401 (access token expired), it gets a new token
 *     with the refresh token ONCE (even if many requests fail together) and
 *     retries the request.
 *  3. Turns every failure into one of two errors:
 *       NetworkError - the request never got an answer (offline, timeout).
 *                      Safe to retry later; the offline queue relies on this.
 *       ApiError     - the server answered with an error status and message.
 *
 * It is created by a factory with its dependencies passed in, so tests can
 * use a fake `fetch` and a fake token store.
 */
import type { TokenResponse } from './types';

export class NetworkError extends Error {
  constructor(message = 'network') {
    super(message);
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
  get isServerError() {
    return this.status >= 500 || this.status === 408 || this.status === 429;
  }
}

export interface TokenStore {
  getAccessToken(): string | null;
  getRefreshToken(): string | null;
  saveTokens(tokens: TokenResponse): Promise<void>;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  json?: unknown;
  form?: FormData;
  auth?: boolean;
  timeoutMs?: number;
}

export interface ApiClientDeps {
  baseUrl: string;
  tokens: TokenStore;
  fetchImpl?: typeof fetch;
  defaultTimeoutMs?: number;
  /** Called when the refresh token is rejected: the user must log in again. */
  onSessionExpired?: () => void;
}

/** Extracts a plain-language message from a FastAPI error body. */
export function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string };
      if (first?.msg) return first.msg.replace(/^Value error, /, '');
    }
  }
  return fallback;
}

export function createApiClient(deps: ApiClientDeps) {
  const doFetch = deps.fetchImpl ?? fetch;
  const defaultTimeout = deps.defaultTimeoutMs ?? 20_000;
  let refreshing: Promise<boolean> | null = null;

  async function send(path: string, opts: RequestOptions, accessToken: string | null) {
    const headers: Record<string, string> = { Accept: 'application/json' };
    let body: BodyInit | undefined;
    if (opts.json !== undefined) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(opts.json);
    } else if (opts.form) {
      body = opts.form as unknown as BodyInit; // fetch sets the multipart boundary itself
    }
    if (opts.auth !== false && accessToken) headers.Authorization = `Bearer ${accessToken}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? defaultTimeout);
    try {
      return await doFetch(`${deps.baseUrl}${path}`, {
        method: opts.method ?? 'GET',
        headers,
        body,
        signal: controller.signal,
      });
    } catch (e) {
      // Shown in the Expo terminal while developing: otherwise every failure
      // looks the same ("offline")
      if (__DEV__) console.warn('[api] fetch failed', opts.method ?? 'GET', path, e);
      throw new NetworkError(); // offline, DNS failure, timeout, connection reset
    } finally {
      clearTimeout(timer);
    }
  }

  async function parse<T>(response: Response): Promise<T> {
    if (response.status === 204) return undefined as T;
    const text = await response.text();
    let data: unknown = undefined;
    try {
      data = text ? JSON.parse(text) : undefined;
    } catch {
      data = text;
    }
    if (!response.ok) {
      throw new ApiError(response.status, errorMessage(data, `HTTP ${response.status}`), data);
    }
    return data as T;
  }

  /** Returns true when new tokens were obtained. Only one refresh runs at a time. */
  async function refreshTokens(): Promise<boolean> {
    if (!refreshing) {
      refreshing = (async () => {
        const refreshToken = deps.tokens.getRefreshToken();
        if (!refreshToken) return false;
        const response = await send(
          '/auth/refresh',
          { method: 'POST', json: { refresh_token: refreshToken }, auth: false },
          null,
        );
        if (response.status === 401 || response.status === 403) return false;
        const tokens = await parse<TokenResponse>(response);
        await deps.tokens.saveTokens(tokens);
        return true;
      })().finally(() => {
        refreshing = null;
      });
    }
    return refreshing;
  }

  async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    let response = await send(path, opts, deps.tokens.getAccessToken());
    if (response.status === 401 && opts.auth !== false) {
      const refreshed = await refreshTokens(); // may throw NetworkError: keep the session
      if (!refreshed) {
        deps.onSessionExpired?.();
        throw new ApiError(401, 'session_expired');
      }
      response = await send(path, opts, deps.tokens.getAccessToken());
    }
    return parse<T>(response);
  }

  return { request, refreshTokens };
}

export type ApiClient = ReturnType<typeof createApiClient>;
