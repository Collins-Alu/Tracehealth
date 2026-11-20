/** In-memory QueueStore with the same behaviour as the SQLite one, for tests. */
import type { NewQueuedReport, QueuedReport, QueueStore } from '../../types';

export function memoryQueueStore(): QueueStore & { rows: Map<string, QueuedReport> } {
  const rows = new Map<string, QueuedReport>();
  return {
    rows,
    async add(item: NewQueuedReport, now: number) {
      if (rows.has(item.clientReportId)) return; // INSERT OR IGNORE
      rows.set(item.clientReportId, {
        ...item,
        state: 'QUEUED',
        attempts: 0,
        lastError: null,
        nextAttemptAt: 0,
        createdAt: now,
      });
    },
    async get(id) {
      const r = rows.get(id);
      return r ? { ...r } : null;
    },
    async listForUser(userId) {
      return [...rows.values()]
        .filter((r) => r.userId === userId)
        .sort((a, b) => b.createdAt - a.createdAt)
        .map((r) => ({ ...r }));
    },
    async update(id, changes) {
      const r = rows.get(id);
      if (r) rows.set(id, { ...r, ...changes });
    },
    async remove(id) {
      rows.delete(id);
    },
    async resetSyncing() {
      for (const [id, r] of rows) if (r.state === 'SYNCING') rows.set(id, { ...r, state: 'QUEUED' });
    },
  };
}

let counter = 0;
export function draft(userId = 'user-1', overrides: Partial<NewQueuedReport> = {}): NewQueuedReport {
  counter += 1;
  return {
    clientReportId: `00000000-0000-4000-8000-${String(counter).padStart(12, '0')}`,
    userId,
    photoUri: `file:///queued-photos/${counter}.jpg`,
    category: 'OPEN_BURNING',
    latitude: -1.2921,
    longitude: 36.8219,
    accuracyM: 12,
    description: null,
    capturedAt: '2026-11-08T09:30:00.000Z',
    createdOffline: true,
    ...overrides,
  };
}
