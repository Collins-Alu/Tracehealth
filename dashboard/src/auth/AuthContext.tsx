/**
 * Who is signed in. The dashboard is for agency staff and administrators
 * (decision D8: no anonymous public view). Other roles are turned away at
 * sign-in with an explanation.
 */
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react';

import { authApi } from '@/api/endpoints';
import { ApiError, session, setSessionExpiredHandler } from '@/api/client';
import i18n from '@/i18n';
import type { Role, User } from '@/types/api';

export const DASHBOARD_ROLES: Role[] = ['AGENCY_STAFF', 'ADMINISTRATOR'];

interface AuthValue {
  user: User | null;
  isAdmin: boolean;
  signIn(identifier: string, password: string): Promise<void>;
  signOut(): Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export class NoDashboardAccess extends Error {}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => session.user());

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    return () => setSessionExpiredHandler(null);
  }, []);

  const signIn = useCallback(async (identifier: string, password: string) => {
    const tokens = await authApi.login(identifier, password);
    if (!tokens.user.roles.some((r) => DASHBOARD_ROLES.includes(r))) {
      // No dashboard access: revoke the session the API just issued
      session.save(tokens);
      await authApi.logout(tokens.refresh_token).catch(() => undefined);
      session.clear();
      throw new NoDashboardAccess();
    }
    session.save(tokens);
    if (tokens.user.preferred_language === 'SW') await i18n.changeLanguage('sw');
    setUser(tokens.user);
  }, []);

  const signOut = useCallback(async () => {
    const refresh = session.refresh();
    if (refresh) await authApi.logout(refresh).catch(() => undefined);
    session.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isAdmin: !!user?.roles.includes('ADMINISTRATOR'), signIn, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}

export function isSessionExpired(error: unknown) {
  return error instanceof ApiError && error.message === 'session_expired';
}
