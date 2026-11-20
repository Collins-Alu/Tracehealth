/**
 * FR 1.2 — offline storage, automatic sync, duplicate prevention,
 * and reports surviving failures.
 */
import { ApiError, NetworkError } from '@/api/client';

import { backoffFor, classifyFailure, SyncEngine } from '../syncEngine';
import type { QueuedReport } from '../types';
import { draft, memoryQueueStore } from './helpers/memoryQueueStore';

function setup(upload: (item: QueuedReport) => Promise<unknown> = async () => ({})) {
  const store = memoryQueueStore();
  let clock = 1_000_000;
  const deleted: string[] = [];
  const uploads: string[] = [];
  const engine = new SyncEngine({
    store,
    upload: async (item) => {
      uploads.push(item.clientReportId);
      return upload(item);
    },
    deletePhoto: async (uri) => {
      deleted.push(uri);
    },
    now: () => clock,
  });
  return {
    store,
    engine,
    deleted,
    uploads,
    advance: (ms: number) => {
      clock += ms;
    },
    now: () => clock,
  };
}

test('a queued report is sent, removed from the queue, and its photo copy deleted', async () => {
  const { store, engine, deleted } = setup();
  const item = draft();
  await store.add(item, 1);
  const summary = await engine.syncNow('user-1');
  expect(summary).toEqual({ sent: 1, failed: 0, needsAttention: 0, remaining: 0 });
  expect(await store.get(item.clientReportId)).toBeNull();
  expect(deleted).toEqual([item.photoUri]);
});

test('reports are sent oldest first', async () => {
  const { store, engine, uploads } = setup();
  const a = draft();
  const b = draft();
  await store.add(b, 20);
  await store.add(a, 10);
  await engine.syncNow('user-1');
  expect(uploads).toEqual([a.clientReportId, b.clientReportId]);
});

test('no connection keeps the report, schedules a retry, and stops the round', async () => {
  const { store, engine, uploads, now } = setup(async () => {
    throw new NetworkError();
  });
  const a = draft();
  const b = draft();
  await store.add(a, 1);
  await store.add(b, 2);
  const summary = await engine.syncNow('user-1');
  expect(summary.failed).toBe(1);
  expect(summary.remaining).toBe(2);
  expect(uploads).toEqual([a.clientReportId]); // didn't waste time on b
  const kept = await store.get(a.clientReportId);
  expect(kept?.state).toBe('QUEUED');
  expect(kept?.attempts).toBe(1);
  expect(kept?.nextAttemptAt).toBe(now() + backoffFor(1));
});

test('backoff is respected unless the sync is forced (connection came back)', async () => {
  let fail = true;
  const { store, engine, uploads, advance } = setup(async () => {
    if (fail) throw new NetworkError();
  });
  await store.add(draft(), 1);
  await engine.syncNow('user-1');
  fail = false;
  await engine.syncNow('user-1'); // too early: skipped
  expect(uploads).toHaveLength(1);
  await engine.syncNow('user-1', { force: true }); // connectivity restored
  expect(uploads).toHaveLength(2);
  expect(await store.listForUser('user-1')).toEqual([]);
  advance(0);
});

test('server errors (5xx) are retried later, like a lost connection', async () => {
  const { store, engine } = setup(async () => {
    throw new ApiError(503, 'Service unavailable');
  });
  const item = draft();
  await store.add(item, 1);
  await engine.syncNow('user-1');
  expect((await store.get(item.clientReportId))?.state).toBe('QUEUED');
});

test('a report the server refuses is kept and marked as needing attention', async () => {
  const bad = draft();
  const good = draft();
  const { store, engine, deleted } = setup(async (item) => {
    if (item.clientReportId === bad.clientReportId) {
      throw new ApiError(422, 'This report is older than 30 days and can no longer be sent.');
    }
  });
  await store.add(bad, 1);
  await store.add(good, 2);
  const summary = await engine.syncNow('user-1');
  expect(summary).toMatchObject({ sent: 1, needsAttention: 1, remaining: 1 });
  const kept = await store.get(bad.clientReportId);
  expect(kept?.state).toBe('NEEDS_ATTENTION');
  expect(kept?.lastError).toContain('older than 30 days');
  expect(deleted).toEqual([good.photoUri]); // the refused report's photo is kept

  // It is not retried automatically, even when forced
  await engine.syncNow('user-1', { force: true });
  expect((await store.get(bad.clientReportId))?.attempts).toBe(1);
});

test('the user can retry a report that needs attention', async () => {
  let refuse = true;
  const { store, engine } = setup(async () => {
    if (refuse) throw new ApiError(422, 'refused');
  });
  const item = draft();
  await store.add(item, 1);
  await engine.syncNow('user-1');
  refuse = false;
  await engine.retry(item.clientReportId);
  expect((await store.get(item.clientReportId))?.state).toBe('QUEUED');
  await engine.syncNow('user-1');
  expect(await store.get(item.clientReportId)).toBeNull();
});

test('the user can delete a report that was never accepted', async () => {
  const { store, engine, deleted } = setup(async () => {
    throw new ApiError(422, 'refused');
  });
  const item = draft();
  await store.add(item, 1);
  await engine.syncNow('user-1');
  await engine.discard(item.clientReportId);
  expect(await store.get(item.clientReportId)).toBeNull();
  expect(deleted).toEqual([item.photoUri]);
});

test('two sync requests at once never upload the same report twice', async () => {
  let release!: () => void;
  const gate = new Promise<void>((r) => {
    release = r;
  });
  const { store, engine, uploads } = setup(() => gate);
  await store.add(draft(), 1);
  const first = engine.syncNow('user-1');
  const second = engine.syncNow('user-1', { force: true });
  expect(second).toBe(first); // same in-flight sync
  release();
  await Promise.all([first, second]);
  expect(uploads).toHaveLength(1);
});

test('adding the same report twice (double tap) queues it once', async () => {
  const { store } = setup();
  const item = draft();
  await store.add(item, 1);
  await store.add(item, 2);
  expect(await store.listForUser('user-1')).toHaveLength(1);
});

test("only the logged-in user's reports are sent", async () => {
  const { store, engine, uploads } = setup();
  const mine = draft('user-1');
  const theirs = draft('user-2');
  await store.add(mine, 1);
  await store.add(theirs, 2);
  await engine.syncNow('user-1');
  expect(uploads).toEqual([mine.clientReportId]);
  expect(await store.get(theirs.clientReportId)).not.toBeNull();
});

test('a report left SYNCING by a crash is recovered and sent', async () => {
  const { store, engine } = setup();
  const item = draft();
  await store.add(item, 1);
  await store.update(item.clientReportId, { state: 'SYNCING' });
  await store.resetSyncing();
  await engine.syncNow('user-1');
  expect(await store.get(item.clientReportId)).toBeNull();
});

test('a failing photo cleanup never fails the sync', async () => {
  const store = memoryQueueStore();
  const engine = new SyncEngine({
    store,
    upload: async () => ({}),
    deletePhoto: async () => {
      throw new Error('disk error');
    },
  });
  const item = draft();
  await store.add(item, 1);
  await expect(engine.syncNow('user-1')).resolves.toMatchObject({ sent: 1 });
});

describe('classifyFailure', () => {
  test.each([
    [new NetworkError(), 'retry'],
    [new ApiError(500, 'x'), 'retry'],
    [new ApiError(429, 'x'), 'retry'],
    [new ApiError(401, 'session_expired'), 'retry'],
    [new ApiError(422, 'x'), 'needs_attention'],
    [new ApiError(409, 'x'), 'needs_attention'],
    [new ApiError(413, 'x'), 'needs_attention'],
  ] as [Error, string][])('%p -> %s', (error, kind) => {
    expect(classifyFailure(error).kind).toBe(kind);
  });
});

test('backoff grows and is capped at 15 minutes', () => {
  expect(backoffFor(1)).toBe(5_000);
  expect(backoffFor(3)).toBe(30_000);
  expect(backoffFor(50)).toBe(900_000);
});
