/**
 * The offline sync engine (FR 1.2, UML B.3 steps 7–8).
 *
 * Every report is saved to the queue FIRST and then sent, even when the phone
 * is online. That way a report is never lost if the app is closed, the
 * battery dies or the connection drops in the middle of an upload.
 *
 * Rules:
 *  - One sync runs at a time. Calling syncNow() while it runs returns the
 *    same promise, so a report is never uploaded twice in parallel.
 *  - Reports go one at a time (kind to slow connections).
 *  - No connection / server error / timeout  -> keep it, retry with backoff,
 *    and stop this round (the next ones would fail the same way).
 *  - Server refuses it (400/409/413/422)     -> NEEDS_ATTENTION; kept until
 *    the user retries or deletes it. Never deleted automatically.
 *  - Accepted (201, or 200 "already received") -> removed from the queue and
 *    the local photo copy deleted. The server copy is now the record.
 *  - Duplicates are impossible: the server keys reports by clientReportId.
 *
 * This file has no React or Expo imports, so it is fully unit-tested.
 */
import { ApiError, NetworkError } from '@/api/client';

import type { QueuedReport, QueueStore } from './types';

/** Waits before automatic retry number n (1-based). Capped at 15 minutes. */
export const BACKOFF_MS = [5_000, 15_000, 30_000, 60_000, 120_000, 300_000, 900_000];

export function backoffFor(attempts: number): number {
  return BACKOFF_MS[Math.min(Math.max(attempts, 1), BACKOFF_MS.length) - 1];
}

export interface SyncDeps {
  store: QueueStore;
  upload: (item: QueuedReport) => Promise<unknown>;
  deletePhoto: (uri: string) => Promise<void>;
  now?: () => number;
  onChange?: () => void;
}

export interface SyncSummary {
  sent: number;
  failed: number;
  needsAttention: number;
  remaining: number;
}

export type FailureKind = 'retry' | 'needs_attention';

/** Decides what a failed upload means for the queued report. */
export function classifyFailure(error: unknown): { kind: FailureKind; message: string } {
  if (error instanceof NetworkError) return { kind: 'retry', message: 'network' };
  if (error instanceof ApiError) {
    // 401: login expired and could not be refreshed right now; keep for later
    if (error.isServerError || error.status === 401) {
      return { kind: 'retry', message: error.message };
    }
    return { kind: 'needs_attention', message: error.message };
  }
  return { kind: 'retry', message: error instanceof Error ? error.message : 'unknown' };
}

export class SyncEngine {
  private running: Promise<SyncSummary> | null = null;
  private readonly now: () => number;

  constructor(private readonly deps: SyncDeps) {
    this.now = deps.now ?? Date.now;
  }

  get isRunning() {
    return this.running !== null;
  }

  /**
   * Send the user's queued reports.
   * @param force ignore backoff timers (used when the connection comes back
   *              or the user taps "Send now")
   */
  syncNow(userId: string, { force = false } = {}): Promise<SyncSummary> {
    if (!this.running) {
      this.running = this.run(userId, force).finally(() => {
        this.running = null;
        this.deps.onChange?.();
      });
    }
    return this.running;
  }

  /** User asked to retry a report that needs attention (or is waiting). */
  async retry(clientReportId: string): Promise<void> {
    await this.deps.store.update(clientReportId, {
      state: 'QUEUED',
      nextAttemptAt: 0,
      lastError: null,
    });
    this.deps.onChange?.();
  }

  /** User chose to delete a report that was never accepted. */
  async discard(clientReportId: string): Promise<void> {
    const item = await this.deps.store.get(clientReportId);
    if (!item || item.state === 'SYNCING') return;
    await this.deps.store.remove(clientReportId);
    await this.safeDeletePhoto(item.photoUri);
    this.deps.onChange?.();
  }

  private async run(userId: string, force: boolean): Promise<SyncSummary> {
    const { store } = this.deps;
    const summary: SyncSummary = { sent: 0, failed: 0, needsAttention: 0, remaining: 0 };
    const items = (await store.listForUser(userId))
      .filter((i) => i.state === 'QUEUED' && (force || i.nextAttemptAt <= this.now()))
      .sort((a, b) => a.createdAt - b.createdAt); // oldest first

    for (const item of items) {
      await store.update(item.clientReportId, { state: 'SYNCING' });
      this.deps.onChange?.();
      try {
        await this.deps.upload(item);
        await store.remove(item.clientReportId);
        await this.safeDeletePhoto(item.photoUri);
        summary.sent += 1;
      } catch (error) {
        const { kind, message } = classifyFailure(error);
        const attempts = item.attempts + 1;
        if (kind === 'needs_attention') {
          await store.update(item.clientReportId, {
            state: 'NEEDS_ATTENTION',
            attempts,
            lastError: message,
          });
          summary.needsAttention += 1;
          continue; // this report's problem doesn't affect the others
        }
        await store.update(item.clientReportId, {
          state: 'QUEUED',
          attempts,
          lastError: message,
          nextAttemptAt: this.now() + backoffFor(attempts),
        });
        summary.failed += 1;
        break; // no connection: the rest would fail too
      } finally {
        this.deps.onChange?.();
      }
    }

    summary.remaining = (await store.listForUser(userId)).length;
    return summary;
  }

  private async safeDeletePhoto(uri: string) {
    try {
      await this.deps.deletePhoto(uri);
    } catch {
      // A leftover photo file is harmless; never fail a sync because of it
    }
  }
}
