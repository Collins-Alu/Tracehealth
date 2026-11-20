/**
 * Offline queue stored in SQLite on the phone.
 *
 * SQLite survives app restarts and phone reboots, which is what "preserve
 * queued reports" requires. The database file lives in the app's private
 * storage; other apps cannot read it.
 */
import * as SQLite from 'expo-sqlite';

import type { NewQueuedReport, QueuedReport, QueueStore } from './types';

interface Row {
  client_report_id: string;
  user_id: string;
  photo_uri: string;
  category: string;
  latitude: number;
  longitude: number;
  accuracy_m: number | null;
  description: string | null;
  captured_at: string;
  created_offline: number;
  state: string;
  attempts: number;
  last_error: string | null;
  next_attempt_at: number;
  created_at: number;
}

const COLUMNS: Record<keyof QueuedReport, keyof Row> = {
  clientReportId: 'client_report_id',
  userId: 'user_id',
  photoUri: 'photo_uri',
  category: 'category',
  latitude: 'latitude',
  longitude: 'longitude',
  accuracyM: 'accuracy_m',
  description: 'description',
  capturedAt: 'captured_at',
  createdOffline: 'created_offline',
  state: 'state',
  attempts: 'attempts',
  lastError: 'last_error',
  nextAttemptAt: 'next_attempt_at',
  createdAt: 'created_at',
};

function fromRow(r: Row): QueuedReport {
  return {
    clientReportId: r.client_report_id,
    userId: r.user_id,
    photoUri: r.photo_uri,
    category: r.category as QueuedReport['category'],
    latitude: r.latitude,
    longitude: r.longitude,
    accuracyM: r.accuracy_m,
    description: r.description,
    capturedAt: r.captured_at,
    createdOffline: r.created_offline === 1,
    state: r.state as QueuedReport['state'],
    attempts: r.attempts,
    lastError: r.last_error,
    nextAttemptAt: r.next_attempt_at,
    createdAt: r.created_at,
  };
}

export async function openQueueStore(): Promise<QueueStore & { db: SQLite.SQLiteDatabase }> {
  const db = await SQLite.openDatabaseAsync('tracehealth.db');
  await db.execAsync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS queued_reports (
      client_report_id TEXT PRIMARY KEY NOT NULL,
      user_id          TEXT NOT NULL,
      photo_uri        TEXT NOT NULL,
      category         TEXT NOT NULL,
      latitude         REAL NOT NULL,
      longitude        REAL NOT NULL,
      accuracy_m       REAL,
      description      TEXT,
      captured_at      TEXT NOT NULL,
      created_offline  INTEGER NOT NULL DEFAULT 0,
      state            TEXT NOT NULL DEFAULT 'QUEUED',
      attempts         INTEGER NOT NULL DEFAULT 0,
      last_error       TEXT,
      next_attempt_at  INTEGER NOT NULL DEFAULT 0,
      created_at       INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_queued_reports_user ON queued_reports (user_id, created_at);
    CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL);
  `);

  return {
    db,
    async add(item: NewQueuedReport, now: number) {
      // INSERT OR IGNORE: tapping Submit twice cannot queue the same report twice
      await db.runAsync(
        `INSERT OR IGNORE INTO queued_reports
           (client_report_id, user_id, photo_uri, category, latitude, longitude, accuracy_m,
            description, captured_at, created_offline, state, attempts, next_attempt_at, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, 0, ?)`,
        item.clientReportId,
        item.userId,
        item.photoUri,
        item.category,
        item.latitude,
        item.longitude,
        item.accuracyM,
        item.description,
        item.capturedAt,
        item.createdOffline ? 1 : 0,
        now,
      );
    },
    async get(id: string) {
      const row = await db.getFirstAsync<Row>(
        'SELECT * FROM queued_reports WHERE client_report_id = ?',
        id,
      );
      return row ? fromRow(row) : null;
    },
    async listForUser(userId: string) {
      const rows = await db.getAllAsync<Row>(
        'SELECT * FROM queued_reports WHERE user_id = ? ORDER BY created_at DESC',
        userId,
      );
      return rows.map(fromRow);
    },
    async update(id: string, changes: Partial<QueuedReport>) {
      const entries = Object.entries(changes) as [keyof QueuedReport, unknown][];
      if (entries.length === 0) return;
      const sets = entries.map(([k]) => `${COLUMNS[k]} = ?`).join(', ');
      const values = entries.map(([k, v]) =>
        k === 'createdOffline' ? (v ? 1 : 0) : (v as string | number | null),
      );
      await db.runAsync(
        `UPDATE queued_reports SET ${sets} WHERE client_report_id = ?`,
        ...values,
        id,
      );
    },
    async remove(id: string) {
      await db.runAsync('DELETE FROM queued_reports WHERE client_report_id = ?', id);
    },
    async resetSyncing() {
      await db.runAsync("UPDATE queued_reports SET state = 'QUEUED' WHERE state = 'SYNCING'");
    },
  };
}

/** Small key/value cache (e.g. last list of reports, for viewing offline). */
export async function cacheGet<T>(db: SQLite.SQLiteDatabase, key: string): Promise<T | null> {
  const row = await db.getFirstAsync<{ value: string }>('SELECT value FROM cache WHERE key = ?', key);
  if (!row) return null;
  try {
    return JSON.parse(row.value) as T;
  } catch {
    return null;
  }
}

export async function cacheSet(db: SQLite.SQLiteDatabase, key: string, value: unknown) {
  await db.runAsync(
    'INSERT INTO cache (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    key,
    JSON.stringify(value),
  );
}
