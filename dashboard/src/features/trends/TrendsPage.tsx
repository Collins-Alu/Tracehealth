/**
 * Health trends (FR 4.2): verified reports and clinic visits on one timeline,
 * possible clusters, and every linkage result. Small clinic counts are hidden
 * (D11) and every result is labelled an association, not a cause.
 */
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import { dashboardApi, linkageApi, zonesApi } from '@/api/endpoints';
import { PageHeader } from '@/components/PageHeader';
import { Pagination } from '@/components/Pagination';
import { AssociationNotice, Empty, ErrorNote, Loading } from '@/components/State';
import { CATEGORY_COLOURS, CONDITION_COLOURS } from '@/lib/categories';
import { formatDate, formatP } from '@/lib/format';
import {
  CONDITIONS, type ConditionCategory, type LinkageStatus, POLLUTION_CATEGORIES, type PollutionCategory,
} from '@/types/api';

import { LinkageTable } from './LinkageTable';

const PAGE = 20;

export function TrendsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const [zone, setZone] = useState('');
  const [category, setCategory] = useState<PollutionCategory>('OPEN_BURNING');
  const [condition, setCondition] = useState<ConditionCategory>('RESPIRATORY');
  const [status, setStatus] = useState<LinkageStatus | ''>('');
  const [offset, setOffset] = useState(0);

  const trends = useQuery({ queryKey: ['trends', zone], queryFn: () => dashboardApi.trends({ zone }) });
  const linkTrends = useQuery({ queryKey: ['linkage-trends'], queryFn: linkageApi.trends });
  const linkages = useQuery({
    queryKey: ['linkages', status, offset],
    queryFn: () => linkageApi.list({ status, limit: PAGE, offset }),
  });

  const data = trends.data;
  const threshold = data?.small_count_threshold ?? 5;
  const overlay = data?.weeks.map((w, i) => ({
    week: formatDate(w, lang),
    reports: data.reports[category]?.[i] ?? 0,
    visits: data.suppressed[condition]?.[i] ? null : (data.visits[condition]?.[i] ?? null),
  }));
  const shownConditions = CONDITIONS.filter((c) => data?.visits[c]?.some((v) => v !== null));
  const visitRows = data?.weeks.map((w, i) => {
    const row: Record<string, string | number | null> = { week: formatDate(w, lang) };
    for (const c of shownConditions) row[c] = data.suppressed[c]?.[i] ? null : (data.visits[c]?.[i] ?? null);
    return row;
  });

  return (
    <>
      <PageHeader title={t('trends.title')} />
      <div className="mb-6">
        <AssociationNotice />
      </div>

      <section className="panel mb-6 p-6" aria-labelledby="overlay-heading">
        <h2 id="overlay-heading">{t('trends.overlay')}</h2>
        <p className="text-sm text-muted">{t('trends.overlayHelp')}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <ZoneSelect value={zone} onChange={setZone} />
          <label className="w-52">
            <span className="label">{t('trends.chooseType')}</span>
            <select className="field" value={category} onChange={(e) => setCategory(e.target.value as PollutionCategory)}>
              {POLLUTION_CATEGORIES.map((c) => (
                <option key={c} value={c}>{t(`categories.${c}`)}</option>
              ))}
            </select>
          </label>
          <label className="w-52">
            <span className="label">{t('trends.chooseCondition')}</span>
            <select className="field" value={condition} onChange={(e) => setCondition(e.target.value as ConditionCategory)}>
              {CONDITIONS.map((c) => (
                <option key={c} value={c}>{t(`conditions.${c}`)}</option>
              ))}
            </select>
          </label>
        </div>
        {trends.isLoading ? <Loading /> : null}
        {trends.isError ? <ErrorNote error={trends.error} onRetry={() => trends.refetch()} /> : null}
        {overlay ? (
          <div className="mt-4 h-80" data-testid="overlay-chart">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={overlay} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                <CartesianGrid stroke="#D3DDD9" vertical={false} />
                <XAxis dataKey="week" tick={{ fontSize: 12 }} minTickGap={24} />
                <YAxis yAxisId="r" allowDecimals={false} tick={{ fontSize: 12 }} label={{ value: t('trends.reportsAxis'), angle: -90, position: 'insideLeft', fontSize: 12 }} />
                <YAxis yAxisId="v" orientation="right" tick={{ fontSize: 12 }} label={{ value: t('trends.visitsAxis'), angle: 90, position: 'insideRight', fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar yAxisId="r" dataKey="reports" name={t(`categories.${category}`)} fill={CATEGORY_COLOURS[category]} radius={[3, 3, 0, 0]} />
                <Line yAxisId="v" dataKey="visits" name={t(`conditions.${condition}`)} stroke={CONDITION_COLOURS[condition]} strokeWidth={2.5} dot={false} connectNulls={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        ) : null}
        <p className="mt-2 text-sm text-muted">{t('trends.suppressedNote', { n: threshold })}</p>
      </section>

      <div className="mb-6 grid gap-6 xl:grid-cols-2 [&>*]:min-w-0">
        <section className="panel p-6">
          <h2>{t('trends.visitTrends')}</h2>
          {visitRows && shownConditions.length ? (
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={visitRows} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
                  <CartesianGrid stroke="#D3DDD9" vertical={false} />
                  <XAxis dataKey="week" tick={{ fontSize: 12 }} minTickGap={24} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  {shownConditions.map((c) => (
                    <Line key={c} dataKey={c} name={t(`conditions.${c}`)} stroke={CONDITION_COLOURS[c]} strokeWidth={2} dot={false} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty>{t('trends.noClusters')}</Empty>
          )}
        </section>

        <section className="rounded-lg border-2 border-signal bg-paper p-6">
          <h2 className="text-signal">{t('trends.clusters')}</h2>
          <p className="text-sm text-muted">{t('trends.clustersHelp')}</p>
          {linkTrends.isError ? <ErrorNote error={linkTrends.error} /> : null}
          {linkTrends.data && linkTrends.data.clusters.length === 0 ? <Empty>{t('trends.noClusters')}</Empty> : null}
          {linkTrends.data && linkTrends.data.clusters.length > 0 ? (
            <div className="mt-3 overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('trends.facility')}</th>
                  <th>{t('common.condition')}</th>
                  <th className="text-right">{t('trends.reports')}</th>
                  <th className="text-right">{t('trends.rateRatio')}</th>
                  <th className="text-right">{t('trends.pValue')}</th>
                </tr>
              </thead>
              <tbody>
                {linkTrends.data.clusters.map((c) => (
                  <tr key={`${c.facility_id}-${c.condition_category}`}>
                    <td>
                      {c.facility_name}
                      <span className="block text-xs text-muted">{c.pollution_categories.map((p) => t(`categories.${p}`)).join(', ')}</span>
                    </td>
                    <td>{t(`conditions.${c.condition_category}`)}</td>
                    <td className="text-right tabular-nums">{c.signal_reports}</td>
                    <td className="text-right tabular-nums">{t('trends.times', { value: c.max_rate_ratio.toFixed(2) })}</td>
                    <td className="text-right tabular-nums">{formatP(c.min_p_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          ) : null}
        </section>
      </div>

      <section className="panel p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2>{t('trends.linkages')}</h2>
          <label className="w-52">
            <span className="label">{t('common.status')}</span>
            <select className="field" value={status} onChange={(e) => { setStatus(e.target.value as LinkageStatus | ''); setOffset(0); }}>
              <option value="">{t('common.allStatuses')}</option>
              {(['SIGNAL', 'NO_SIGNAL', 'INSUFFICIENT_DATA'] as const).map((s) => (
                <option key={s} value={s}>{t(`status.${s}`)}</option>
              ))}
            </select>
          </label>
        </div>
        {linkages.isLoading ? <Loading /> : null}
        {linkages.isError ? <ErrorNote error={linkages.error} onRetry={() => linkages.refetch()} /> : null}
        {linkages.data ? (
          linkages.data.items.length ? (
            <>
              <div className="mt-3"><LinkageTable items={linkages.data.items} /></div>
              <Pagination total={linkages.data.total} limit={PAGE} offset={offset} onChange={setOffset} />
            </>
          ) : (
            <Empty>{t('reports.noLinkages')}</Empty>
          )
        ) : null}
      </section>
    </>
  );
}

function ZoneSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useTranslation();
  const zones = useQuery({ queryKey: ['zones'], queryFn: zonesApi.list, staleTime: 300_000 });
  return (
    <label className="w-48">
      <span className="label">{t('common.zone')}</span>
      <select className="field" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{t('common.allZones')}</option>
        {zones.data?.map((z) => (
          <option key={z.code} value={z.code}>{z.name}</option>
        ))}
      </select>
    </label>
  );
}
