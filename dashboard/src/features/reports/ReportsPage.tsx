/** Report search. Agency staff see verified reports only (the API enforces it). */
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';

import { reportsApi, type ReportFilters } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthContext';
import { Filters } from '@/components/Filters';
import { PageHeader } from '@/components/PageHeader';
import { Pagination } from '@/components/Pagination';
import { Pill } from '@/components/Pill';
import { Empty, ErrorNote, Loading } from '@/components/State';
import { CATEGORY_COLOURS } from '@/lib/categories';
import { formatDate } from '@/lib/format';
import type { ReportStatus } from '@/types/api';

import { ReportDetail } from './ReportDetail';

const PAGE = 20;
const STATUSES: ReportStatus[] = ['PENDING', 'VERIFIED', 'FLAGGED', 'REJECTED'];

export function ReportsPage() {
  const { t, i18n } = useTranslation();
  const { isAdmin } = useAuth();
  const [params, setParams] = useSearchParams();
  const [filters, setFilters] = useState<ReportFilters>({});
  const [status, setStatus] = useState<ReportStatus | ''>(isAdmin ? '' : 'VERIFIED');
  const [offset, setOffset] = useState(0);
  const openId = params.get('open');

  const query = useQuery({
    queryKey: ['reports', filters, status, offset],
    queryFn: () =>
      reportsApi.search({
        ...filters,
        zone: filters.zone || 'ALL',
        // the API takes timestamps: cover the whole of the chosen days
        date_from: filters.date_from ? `${filters.date_from}T00:00:00Z` : undefined,
        date_to: filters.date_to ? `${filters.date_to}T23:59:59Z` : undefined,
        status,
        limit: PAGE,
        offset,
      }),
  });

  const open = (id: string | null) => {
    const next = new URLSearchParams(params);
    if (id) next.set('open', id);
    else next.delete('open');
    setParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader title={t('reports.title')} intro={isAdmin ? undefined : t('reports.agencyNote')} />
      <div className="mb-4">
        <Filters value={filters} onChange={(f) => { setFilters(f); setOffset(0); }}>
          {isAdmin ? (
            <label className="w-52">
              <span className="label">{t('common.status')}</span>
              <select className="field" value={status} onChange={(e) => { setStatus(e.target.value as ReportStatus | ''); setOffset(0); }}>
                <option value="">{t('common.allStatuses')}</option>
                {STATUSES.map((s) => (<option key={s} value={s}>{t(`status.${s}`)}</option>))}
              </select>
            </label>
          ) : null}
        </Filters>
      </div>
      {query.isLoading ? <Loading /> : null}
      {query.isError ? <ErrorNote error={query.error} onRetry={() => query.refetch()} /> : null}
      {query.data ? (
        query.data.items.length ? (
          <div className="panel relative overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('reports.type')}</th>
                  <th>{t('reports.reported')}</th>
                  <th>{t('common.zone')}</th>
                  <th>{t('common.status')}</th>
                  <th><span className="sr-only">{t('common.actions')}</span></th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: CATEGORY_COLOURS[r.category] }} />
                      {t(`categories.${r.category}`)}
                    </td>
                    <td>{formatDate(r.captured_at, i18n.language, true)}</td>
                    <td>{r.zone_code ?? t('common.unassigned')}</td>
                    <td><Pill status={r.status} /></td>
                    <td className="text-right">
                      <button className="btn-quiet" onClick={() => open(r.id)}>{t('common.details')}</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 pb-3"><Pagination total={query.data.total} limit={PAGE} offset={offset} onChange={setOffset} /></div>
          </div>
        ) : (
          <Empty>{t('reports.empty')}</Empty>
        )
      ) : null}
      <ReportDetail reportId={openId} onClose={() => open(null)} />
    </>
  );
}
