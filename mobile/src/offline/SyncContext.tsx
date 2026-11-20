/**
 * Connects the sync engine to the app.
 *
 * Sends queued reports automatically:
 *  - right after a report is created (when online),
 *  - within seconds of the connection coming back (NetInfo event),
 *  - when the app returns to the foreground,
 *  - every 30 seconds while something is waiting (respecting backoff).
 */
import NetInfo, { type NetInfoState } from '@react-native-community/netinfo';
import { randomUUID } from 'expo-crypto';
import type { SQLiteDatabase } from 'expo-sqlite';
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState } from 'react-native';

import { reportsApi } from '@/api/reports';
import type { PollutionCategory } from '@/api/types';
import { useAuth } from '@/auth/AuthContext';
import { API_URL } from '@/config';

import { deletePhoto, persistPhoto } from './photoStore';
import { openQueueStore } from './sqliteQueueStore';
import { SyncEngine } from './syncEngine';
import type { QueuedReport, QueueStore } from './types';

const PERIODIC_SYNC_MS = 30_000;

// "Online" means the TraceHealth API answers, not that Google is reachable.
// Android's own check (native reachability) can report a working Wi-Fi as
// offline, so NetInfo is told to GET our /health endpoint instead.
NetInfo.configure({
  reachabilityUrl: `${API_URL}/health`,
  reachabilityMethod: 'GET',
  reachabilityTest: async (response) => response.status === 200,
  reachabilityShortTimeout: 5_000,
  useNativeReachability: false,
});

export interface ReportDraft {
  photoUri: string;
  category: PollutionCategory;
  latitude: number;
  longitude: number;
  accuracyM: number | null;
  description: string | null;
  capturedAt: string;
}

interface SyncContextValue {
  ready: boolean;
  isOnline: boolean;
  isSyncing: boolean;
  queue: QueuedReport[];
  db: SQLiteDatabase | null;
  enqueue(draft: ReportDraft): Promise<string>;
  /** Try to send one report right away; resolves 'sent' or 'queued'. */
  sendSoon(clientReportId: string, waitMs: number): Promise<'sent' | 'queued'>;
  syncNow(force?: boolean): Promise<void>;
  retry(clientReportId: string): Promise<void>;
  discard(clientReportId: string): Promise<void>;
}

const SyncContext = createContext<SyncContextValue | null>(null);
export const SyncContextInternal = SyncContext;

function online(state: NetInfoState) {
  // isInternetReachable is null while unknown; only treat explicit false as offline
  return state.isConnected === true && state.isInternetReachable !== false;
}

export function SyncProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [store, setStore] = useState<(QueueStore & { db: SQLiteDatabase }) | null>(null);
  const [queue, setQueue] = useState<QueuedReport[]>([]);
  const [isOnline, setIsOnline] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const wasOnline = useRef(true);

  // Open the database once
  useEffect(() => {
    let cancelled = false;
    openQueueStore().then(async (s) => {
      await s.resetSyncing(); // recover from a crash mid-upload
      if (!cancelled) setStore(s);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshQueue = useCallback(async () => {
    if (!store || !userId) {
      setQueue([]);
      return;
    }
    setQueue(await store.listForUser(userId));
  }, [store, userId]);

  const engine = useMemo(() => {
    if (!store) return null;
    return new SyncEngine({
      store,
      upload: (item) => reportsApi.sync(item),
      deletePhoto,
      onChange: () => {
        refreshQueue();
      },
    });
  }, [store, refreshQueue]);

  const syncNow = useCallback(
    async (force = false) => {
      if (!engine || !userId) return;
      setIsSyncing(true);
      try {
        await engine.syncNow(userId, { force });
      } finally {
        setIsSyncing(engine.isRunning);
        await refreshQueue();
      }
    },
    [engine, userId, refreshQueue],
  );

  useEffect(() => {
    refreshQueue();
  }, [refreshQueue]);

  // Connectivity: sync within seconds of coming back online
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const nowOnline = online(state);
      setIsOnline(nowOnline);
      if (nowOnline && !wasOnline.current) syncNow(true);
      wasOnline.current = nowOnline;
    });
    return unsubscribe;
  }, [syncNow]);

  // On login / app start
  useEffect(() => {
    if (engine && userId) syncNow(true);
  }, [engine, userId, syncNow]);

  // Foreground + periodic retries
  useEffect(() => {
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') syncNow(false);
    });
    const timer = setInterval(() => {
      if (wasOnline.current) syncNow(false);
    }, PERIODIC_SYNC_MS);
    return () => {
      sub.remove();
      clearInterval(timer);
    };
  }, [syncNow]);

  const enqueue = useCallback(
    async (draft: ReportDraft) => {
      if (!store || !userId) throw new Error('not ready');
      const clientReportId = randomUUID();
      const photoUri = await persistPhoto(draft.photoUri, clientReportId);
      const net = await NetInfo.fetch();
      await store.add(
        {
          clientReportId,
          userId,
          photoUri,
          category: draft.category,
          latitude: draft.latitude,
          longitude: draft.longitude,
          accuracyM: draft.accuracyM,
          description: draft.description,
          capturedAt: draft.capturedAt,
          createdOffline: !online(net),
        },
        Date.now(),
      );
      await refreshQueue();
      return clientReportId;
    },
    [store, userId, refreshQueue],
  );

  const sendSoon = useCallback(
    async (clientReportId: string, waitMs: number) => {
      if (!store) return 'queued' as const;
      const attempt = syncNow(true);
      await Promise.race([attempt, new Promise((r) => setTimeout(r, waitMs))]);
      return (await store.get(clientReportId)) ? ('queued' as const) : ('sent' as const);
    },
    [store, syncNow],
  );

  const value: SyncContextValue = {
    ready: store !== null,
    isOnline,
    isSyncing,
    queue,
    db: store?.db ?? null,
    enqueue,
    sendSoon,
    syncNow,
    retry: async (id) => {
      await engine?.retry(id);
      await syncNow(true);
    },
    discard: async (id) => {
      await engine?.discard(id);
      await refreshQueue();
    },
  };

  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>;
}

export function useSync() {
  const ctx = useContext(SyncContext);
  if (!ctx) throw new Error('useSync must be used inside SyncProvider');
  return ctx;
}
