/**
 * Unread-notification count for the tab badge, push registration after
 * login, and opening the right screen when a push notification is tapped.
 */
import { router } from 'expo-router';
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { AppState } from 'react-native';

import { notificationsApi } from '@/api/notifications';
import { useAuth } from '@/auth/AuthContext';

import { loadNotifications, registerForPush } from './push';
import { notificationTarget } from './routing';

const POLL_MS = 60_000;

interface InboxContextValue {
  unread: number;
  refreshUnread(): Promise<void>;
}

const InboxContext = createContext<InboxContextValue>({
  unread: 0,
  refreshUnread: async () => undefined,
});

export function InboxProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);
  const userId = user?.id;
  const roles = user?.roles;

  const refreshUnread = useCallback(async () => {
    if (!userId) {
      setUnread(0);
      return;
    }
    try {
      const page = await notificationsApi.list(1, 0);
      setUnread(page.unread);
    } catch {
      // Offline: keep the last known count
    }
  }, [userId]);

  // Poll while logged in, and refresh when the app comes back to the front
  useEffect(() => {
    refreshUnread();
    if (!userId) return;
    const timer = setInterval(refreshUnread, POLL_MS);
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') refreshUnread();
    });
    return () => {
      clearInterval(timer);
      sub.remove();
    };
  }, [userId, refreshUnread]);

  // Register this phone for push after login (skipped in Expo Go)
  useEffect(() => {
    if (userId) registerForPush();
  }, [userId]);

  // Tapping a push notification opens the related report
  useEffect(() => {
    const Notifications = loadNotifications();
    if (!Notifications || !roles) return;
    const open = (data: Record<string, unknown> | undefined) => {
      const href = notificationTarget(
        typeof data?.type === 'string' ? data.type : undefined,
        typeof data?.report_id === 'string' ? data.report_id : undefined,
        roles,
      );
      if (href) router.push(href as never);
      refreshUnread();
    };
    const sub = Notifications.addNotificationResponseReceivedListener((response) =>
      open(response.notification.request.content.data),
    );
    Notifications.getLastNotificationResponseAsync().then((response) => {
      if (response) open(response.notification.request.content.data);
    });
    const received = Notifications.addNotificationReceivedListener(() => refreshUnread());
    return () => {
      sub.remove();
      received.remove();
    };
  }, [roles, refreshUnread]);

  return <InboxContext.Provider value={{ unread, refreshUnread }}>{children}</InboxContext.Provider>;
}

export function useInbox() {
  return useContext(InboxContext);
}
