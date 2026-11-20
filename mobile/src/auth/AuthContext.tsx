/**
 * Who is logged in, and the login/register/logout actions.
 *
 * Starting the app does NOT require a connection: if tokens and a cached
 * profile exist, the user is logged in straight away and the profile is
 * refreshed in the background when the network allows.
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { authApi } from '@/api/auth';
import { onSessionExpired } from '@/api/index';
import type { RegisterInput, User } from '@/api/types';

import { tokenStore } from './tokenStore';

type Status = 'loading' | 'signedOut' | 'signedIn';

interface AuthContextValue {
  status: Status;
  user: User | null;
  login(identifier: string, password: string): Promise<void>;
  register(input: RegisterInput): Promise<void>;
  logout(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const unsubscribe = tokenStore.subscribe((u) => {
      setUser(u);
      setStatus(u ? 'signedIn' : 'signedOut');
    });
    onSessionExpired(() => {
      tokenStore.clear();
    });
    tokenStore.load().then((cached) => {
      setUser(cached);
      setStatus(cached ? 'signedIn' : 'signedOut');
      if (cached) {
        // Background refresh of roles/profile; failures (e.g. offline) are fine
        authApi
          .me()
          .then((fresh) => tokenStore.saveUser(fresh))
          .catch(() => undefined);
      }
    });
    return () => {
      unsubscribe();
      onSessionExpired(null);
    };
  }, []);

  const login = useCallback(async (identifier: string, password: string) => {
    const tokens = await authApi.login(identifier, password);
    await tokenStore.saveTokens(tokens);
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const tokens = await authApi.register(input);
    await tokenStore.saveTokens(tokens);
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = tokenStore.getRefreshToken();
    if (refreshToken) {
      // Best effort: if offline, the token simply expires on the server later
      await authApi.logout(refreshToken).catch(() => undefined);
    }
    await tokenStore.clear();
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
