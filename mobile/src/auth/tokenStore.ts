/**
 * Keeps the login tokens and the logged-in user's profile.
 *
 * Stored in expo-secure-store (Android Keystore / iOS Keychain), never in
 * plain files. A copy is kept in memory so every request does not have to
 * read secure storage.
 *
 * The user profile is cached too, so a reporter who opens the app with no
 * connection is still "logged in" and can create reports offline.
 */
import * as SecureStore from 'expo-secure-store';

import type { TokenStore } from '@/api/client';
import type { TokenResponse, User } from '@/api/types';

const KEYS = {
  access: 'tracehealth.accessToken',
  refresh: 'tracehealth.refreshToken',
  user: 'tracehealth.user',
};

let accessToken: string | null = null;
let refreshToken: string | null = null;
let cachedUser: User | null = null;
const listeners = new Set<(user: User | null) => void>();

export const tokenStore: TokenStore & {
  load(): Promise<User | null>;
  clear(): Promise<void>;
  getUser(): User | null;
  saveUser(user: User): Promise<void>;
  subscribe(listener: (user: User | null) => void): () => void;
} = {
  getAccessToken: () => accessToken,
  getRefreshToken: () => refreshToken,
  getUser: () => cachedUser,

  async saveTokens(tokens: TokenResponse) {
    accessToken = tokens.access_token;
    refreshToken = tokens.refresh_token;
    await SecureStore.setItemAsync(KEYS.access, tokens.access_token);
    await SecureStore.setItemAsync(KEYS.refresh, tokens.refresh_token);
    await this.saveUser(tokens.user);
  },

  async saveUser(user: User) {
    cachedUser = user;
    await SecureStore.setItemAsync(KEYS.user, JSON.stringify(user));
    listeners.forEach((l) => l(user));
  },

  async load() {
    try {
      accessToken = await SecureStore.getItemAsync(KEYS.access);
      refreshToken = await SecureStore.getItemAsync(KEYS.refresh);
      const raw = await SecureStore.getItemAsync(KEYS.user);
      cachedUser = raw && refreshToken ? (JSON.parse(raw) as User) : null;
    } catch {
      cachedUser = null;
    }
    return cachedUser;
  },

  async clear() {
    accessToken = null;
    refreshToken = null;
    cachedUser = null;
    await Promise.all(Object.values(KEYS).map((k) => SecureStore.deleteItemAsync(k)));
    listeners.forEach((l) => l(null));
  },

  subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
