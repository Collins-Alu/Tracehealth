import { ApiError, createApiClient, errorMessage, NetworkError, type TokenStore } from '../client';
import type { TokenResponse } from '../types';

function jsonResponse(status: number, body: unknown): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  } as Response;
}

function memoryTokens(access = 'old-access', refresh = 'refresh-1'): TokenStore & {
  saved: TokenResponse[];
} {
  let a: string | null = access;
  let r: string | null = refresh;
  const saved: TokenResponse[] = [];
  return {
    saved,
    getAccessToken: () => a,
    getRefreshToken: () => r,
    async saveTokens(t) {
      a = t.access_token;
      r = t.refresh_token;
      saved.push(t);
    },
  };
}

const NEW_TOKENS = {
  access_token: 'new-access',
  refresh_token: 'refresh-2',
  token_type: 'bearer',
  expires_in: 900,
  user: { id: 'u1' },
};

test('sends the access token and parses JSON', async () => {
  const fetchImpl = jest.fn(async () => jsonResponse(200, { ok: true }));
  const api = createApiClient({ baseUrl: 'http://api', tokens: memoryTokens(), fetchImpl });
  await expect(api.request('/auth/me')).resolves.toEqual({ ok: true });
  const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe('http://api/auth/me');
  expect((init.headers as Record<string, string>).Authorization).toBe('Bearer old-access');
});

test('an expired access token is refreshed once and the request retried', async () => {
  const tokens = memoryTokens();
  const fetchImpl = jest.fn(async (url: string, init: RequestInit) => {
    if (url.endsWith('/auth/refresh')) return jsonResponse(200, NEW_TOKENS);
    const auth = (init.headers as Record<string, string>).Authorization;
    return auth === 'Bearer new-access' ? jsonResponse(200, { ok: 1 }) : jsonResponse(401, {});
  });
  const api = createApiClient({ baseUrl: 'http://api', tokens, fetchImpl: fetchImpl as never });
  // Three requests fail together: only ONE refresh call is made
  await Promise.all([api.request('/a'), api.request('/b'), api.request('/c')]);
  const refreshCalls = fetchImpl.mock.calls.filter(([u]: [string, RequestInit]) =>
    String(u).endsWith('/auth/refresh'),
  );
  expect(refreshCalls).toHaveLength(1);
  expect(tokens.getAccessToken()).toBe('new-access');
});

test('a rejected refresh token ends the session', async () => {
  const onSessionExpired = jest.fn();
  const fetchImpl = jest.fn(async () => jsonResponse(401, { detail: 'expired' }));
  const api = createApiClient({
    baseUrl: 'http://api',
    tokens: memoryTokens(),
    fetchImpl,
    onSessionExpired,
  });
  await expect(api.request('/auth/me')).rejects.toMatchObject({ status: 401 });
  expect(onSessionExpired).toHaveBeenCalledTimes(1);
});

test('refresh failing for lack of connection keeps the session (offline-friendly)', async () => {
  const onSessionExpired = jest.fn();
  const fetchImpl = jest.fn(async (url: string) => {
    if (url.endsWith('/auth/refresh')) throw new TypeError('Network request failed');
    return jsonResponse(401, {});
  });
  const api = createApiClient({
    baseUrl: 'http://api',
    tokens: memoryTokens(),
    fetchImpl: fetchImpl as never,
    onSessionExpired,
  });
  await expect(api.request('/x')).rejects.toBeInstanceOf(NetworkError);
  expect(onSessionExpired).not.toHaveBeenCalled();
});

test('no answer at all becomes a NetworkError', async () => {
  const fetchImpl = jest.fn(async () => {
    throw new TypeError('Network request failed');
  });
  const api = createApiClient({ baseUrl: 'http://api', tokens: memoryTokens(), fetchImpl });
  await expect(api.request('/x')).rejects.toBeInstanceOf(NetworkError);
});

test('a slow server times out as a NetworkError', async () => {
  const fetchImpl = jest.fn(
    (_url: string, init: RequestInit) =>
      new Promise<Response>((_, reject) => {
        init.signal?.addEventListener('abort', () => reject(new Error('aborted')));
      }),
  );
  const api = createApiClient({
    baseUrl: 'http://api',
    tokens: memoryTokens(),
    fetchImpl: fetchImpl as never,
    defaultTimeoutMs: 10,
  });
  await expect(api.request('/slow')).rejects.toBeInstanceOf(NetworkError);
});

test('API errors carry the status and a readable message', async () => {
  const body = {
    detail: [{ msg: 'Value error, You need to accept the privacy notice to create an account.' }],
  };
  const fetchImpl = jest.fn(async () => jsonResponse(422, body));
  const api = createApiClient({ baseUrl: 'http://api', tokens: memoryTokens(), fetchImpl });
  const error = (await api.request('/auth/register', { auth: false }).catch((e: unknown) => e)) as ApiError;
  expect(error).toBeInstanceOf(ApiError);
  expect(error.status).toBe(422);
  expect(error.message).toBe('You need to accept the privacy notice to create an account.');
});

test('errorMessage falls back when the body has no detail', () => {
  expect(errorMessage({ detail: 'Report not found.' }, 'x')).toBe('Report not found.');
  expect(errorMessage('<html>', 'fallback')).toBe('fallback');
});
