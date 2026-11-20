/** Loading, error and empty states, written to say what to do next. */
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { ApiError, NetworkError } from '@/api/client';

export function errorText(error: unknown, t: (k: string) => string): string {
  if (error instanceof NetworkError) return t('common.networkError');
  if (error instanceof ApiError) {
    if (error.message === 'session_expired') return t('common.sessionExpired');
    if (error.status >= 500) return t('common.serverError');
    return error.message;
  }
  return t('common.serverError');
}

export function Loading() {
  const { t } = useTranslation();
  return (
    <p role="status" className="py-6 text-muted">
      {t('common.loading')}
    </p>
  );
}

export function ErrorNote({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-md bg-danger-soft px-4 py-3 text-danger">
      <span>{errorText(error, t)}</span>
      {onRetry ? (
        <button className="btn-quiet text-danger" onClick={onRetry}>
          {t('common.retry')}
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-8 text-center text-muted">{children}</p>;
}

export function Notice({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'ok' | 'error' }) {
  const cls = { info: 'bg-teal-soft text-teal-dark', ok: 'bg-ok-soft text-ok', error: 'bg-danger-soft text-danger' }[tone];
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`rounded-md px-4 py-3 ${cls}`}>
      {children}
    </div>
  );
}

export function AssociationNotice() {
  const { t } = useTranslation();
  return (
    <p className="border-l-4 border-signal bg-signal-soft px-4 py-2 text-sm text-ink">{t('notice.association')}</p>
  );
}
