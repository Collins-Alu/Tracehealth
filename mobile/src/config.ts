/**
 * App configuration.
 *
 * EXPO_PUBLIC_* variables are read from mobile/.env when the app is started
 * (see mobile/.env.example). They are bundled into the app, so they must never
 * contain secrets: the API address is fine, a password or API key is not.
 */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/+$/, '');

/** How long to wait for an ordinary request before treating it as "no connection". */
export const REQUEST_TIMEOUT_MS = 20_000;
/** Photo uploads can be slow on 2G/3G connections. */
export const UPLOAD_TIMEOUT_MS = 90_000;
/** After tapping Submit, how long to wait for an immediate send before reassuring the user it is queued. */
export const SUBMIT_WAIT_MS = 8_000;
