import type { TFunction } from 'i18next';

import { ApiError, NetworkError } from '@/api/client';

/** Turns any error into a short, plain-language message for the user. */
export function userMessage(error: unknown, t: TFunction): string {
  if (error instanceof NetworkError) return t('errors.network');
  if (error instanceof ApiError) {
    if (error.message === 'session_expired') return t('errors.sessionExpired');
    if (error.status >= 500) return t('errors.server');
    return error.message; // the API's messages are already written for users
  }
  return t('errors.generic');
}
