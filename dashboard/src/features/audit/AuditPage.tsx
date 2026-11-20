/** Append-only audit log (administrators). */
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { adminApi } from '@/api/endpoints';
import { PageHeader } from '@/components/PageHeader';
import { Pagination } from '@/components/Pagination';
import { Empty, ErrorNote, Loading } from '@/components/State';
import { formatDate } from '@/lib/format';

const PAGE = 50;

export function AuditPage() {
  const { t, i18n } = useTranslation();
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [offset, setOffset] = useState(0);
  const log = useQuery({
    queryKey: ['audit', action, dateFrom, dateTo, offset],
    queryFn: () => adminApi.audit({ action: action.trim(), date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined, date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined, limit: PAGE, offset }),
  });

  return (
    <>
      <PageHeader title={t('audit.title')} intro={t('audit.intro')} />
      <form className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
        <label className="w-56"><span className="label">{t('audit.filterAction')}</span>
          <input className="field" placeholder="report." value={action} onChange={(e) => { setAction(e.target.value); setOffset(0); }} /></label>
        <label className="w-40"><span className="label">{t('common.from')}</span>
          <input className="field" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }} /></label>
        <label className="w-40"><span className="label">{t('common.to')}</span>
          <input className="field" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setOffset(0); }} /></label>
      </form>
      {log.isLoading ? <Loading /> : null}
      {log.isError ? <ErrorNote error={log.error} onRetry={() => log.refetch()} /> : null}
      {log.data ? (
        log.data.items.length ? (
          <div className="panel overflow-x-auto">
            <table className="table">
              <thead><tr><th>{t('audit.when')}</th><th>{t('audit.who')}</th><th>{t('audit.action')}</th><th>{t('audit.subject')}</th><th>{t('common.details')}</th></tr></thead>
              <tbody>
                {log.data.items.map((e) => (
                  <tr key={e.id}>
                    <td className="whitespace-nowrap">{formatDate(e.created_at, i18n.language, true)}</td>
                    <td>{e.actor_name ?? t('audit.system')}</td>
                    <td><code className="text-sm">{e.action}</code></td>
                    <td className="text-sm">{e.entity_type}{e.entity_id ? <span className="block text-xs text-muted">{e.entity_id.slice(0, 8)}</span> : null}</td>
                    <td className="max-w-md text-xs break-words text-muted">{e.details ? JSON.stringify(e.details) : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 pb-3"><Pagination total={log.data.total} limit={PAGE} offset={offset} onChange={setOffset} /></div>
          </div>
        ) : <Empty>{t('audit.empty')}</Empty>
      ) : null}
    </>
  );
}
