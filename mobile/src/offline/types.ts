import type { PollutionCategory } from '@/api/types';

/**
 * A report saved on the phone that has not been accepted by the server yet.
 *
 *   QUEUED          waiting to be sent (also after a failed attempt)
 *   SYNCING         being sent right now
 *   NEEDS_ATTENTION the server refused it (e.g. too old); kept until the user
 *                   retries or deletes it, never deleted automatically
 */
export type QueueState = 'QUEUED' | 'SYNCING' | 'NEEDS_ATTENTION';

export interface QueuedReport {
  /** Random UUID made on the phone; the server uses it to ignore duplicates. */
  clientReportId: string;
  /** Owner. Only the logged-in user's reports are sent. */
  userId: string;
  /** Permanent copy of the photo in the app's document folder. */
  photoUri: string;
  category: PollutionCategory;
  latitude: number;
  longitude: number;
  accuracyM: number | null;
  description: string | null;
  /** ISO 8601 time the photo was taken. */
  capturedAt: string;
  createdOffline: boolean;
  state: QueueState;
  attempts: number;
  lastError: string | null;
  /** Epoch ms before which automatic retries wait (backoff). */
  nextAttemptAt: number;
  createdAt: number;
}

export type NewQueuedReport = Omit<
  QueuedReport,
  'state' | 'attempts' | 'lastError' | 'nextAttemptAt' | 'createdAt'
>;

/** Storage for queued reports. SQLite in the app, in-memory in tests. */
export interface QueueStore {
  add(item: NewQueuedReport, now: number): Promise<void>;
  get(clientReportId: string): Promise<QueuedReport | null>;
  listForUser(userId: string): Promise<QueuedReport[]>;
  update(clientReportId: string, changes: Partial<QueuedReport>): Promise<void>;
  remove(clientReportId: string): Promise<void>;
  /** Crash recovery: anything left SYNCING when the app died goes back to QUEUED. */
  resetSyncing(): Promise<void>;
}
