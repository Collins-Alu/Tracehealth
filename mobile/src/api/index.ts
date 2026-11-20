/** The app-wide API client instance. */
import { tokenStore } from '@/auth/tokenStore';
import { API_URL, REQUEST_TIMEOUT_MS } from '@/config';

import { createApiClient } from './client';

let sessionExpiredHandler: (() => void) | null = null;

/** AuthProvider registers what to do when the session can no longer be refreshed. */
export function onSessionExpired(handler: (() => void) | null) {
  sessionExpiredHandler = handler;
}

export const api = createApiClient({
  baseUrl: API_URL,
  tokens: tokenStore,
  defaultTimeoutMs: REQUEST_TIMEOUT_MS,
  onSessionExpired: () => sessionExpiredHandler?.(),
});

export { ApiError, NetworkError } from './client';
