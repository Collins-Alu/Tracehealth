/** Test helpers: a fake API (fetch stub) and a render wrapper with providers. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router';
import { vi } from 'vitest';

import { session } from '@/api/client';
import { AuthProvider } from '@/auth/AuthContext';
import type { Role, User } from '@/types/api';

type Handler = (url: URL, init: RequestInit) => { status?: number; body?: unknown } | undefined;

/** Replace fetch: each request is answered by the first route whose
 * "METHOD /path" key matches; unknown requests fail the test loudly. */
export function fakeApi(routes: Record<string, unknown | Handler>) {
  const calls: { method: string; path: string; init: RequestInit }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input));
    const method = init.method ?? 'GET';
    calls.push({ method, path: url.pathname + url.search, init });
    const route = routes[`${method} ${url.pathname}`];
    if (route === undefined) throw new Error(`Unexpected request ${method} ${url.pathname}`);
    const answer = typeof route === 'function' ? (route as Handler)(url, init) ?? {} : { body: route };
    const status = answer.status ?? 200;
    return new Response(answer.body === undefined ? null : JSON.stringify(answer.body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { calls, fetchMock };
}

export function makeUser(roles: Role[], overrides: Partial<User> = {}): User {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    full_name: 'Test Person',
    phone_number: '+254700000001',
    email: 'person@example.org',
    preferred_language: 'EN',
    roles,
    assigned_zone: null,
    ...overrides,
  };
}

export function signInAs(roles: Role[]) {
  const user = makeUser(roles);
  session.save({ access_token: 'access', refresh_token: 'refresh', expires_in: 900, user });
  return user;
}

export function renderWithProviders(ui: ReactElement, { route = '/' } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
