/**
 * Overview (Module 7). The headline numbers are set as a ledger of large
 * figures; health signals sit beside them because they are what the page is
 * for: deciding where to act first.
 */
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { dashboardApi, linkageApi, type ReportFilters } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthContext';
import { Filters } from '@/components/Filters';
import { PageHeader } from '@/components/PageHeader';
import { AssociationNotice, ErrorNote, Loading } from '@/components/State';
import { CATEGORY_COLOURS } from '@/lib/categories';
import { formatNumber, formatP } from '@/lib/format';
import { POLLUTION_CATEGORIES } from '@/types/api';

function Figure({ value, label, lang }: { value: number; label: string; lang: string }) {
  return (
    <div>
      <div className="text-3xl font-semibold tabular-nums">{formatNumber(value, lang)}</div>
      <div className="text-sm text-muted">{label}</div>
    </div>
  );
}

export function OverviewPage() {
  const { t, i18n } = useTranslation();
  const { isAdmin } = useAuth();
  const lang = i18n.language;
  const [filters, setFilters] = useState<ReportFilters>({});
  const overview = useQuery({ queryKey: ['overview', filters], queryFn: () => dashboardApi.overview(filters) });
  const signals = useQuery({ queryKey: ['linkage-trends'], queryFn: linkageApi.trends });

  return (
    <>
      <PageHeader title={t('overview.title')} />
      <div className="mb-6">
        <Filters value={filters} onChange={setFilters} showCategory={false} />
      </div>
      {overview.isLoading ? <Loading /> : null}
      {overview.isError ? <ErrorNote error={overview.error} onRetry={() => overview.refetch()} /> : null}
      {overview.data ? (
        <div className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-[3fr_2fr] [&>*]:min-w-0">
            <section className="panel p-6" aria-labelledby="verified-heading">
              <div className="text-7xl leading-none font-semibold tracking-tight text-teal-dark tabular-nums" data-testid="verified-count">
                {formatNumber(overview.data.by_status.VERIFIED, lang)}
              </div>
              <h2 id="verified-heading" className="mt-2">{t('overview.verified')}</h2>
              <p className="text-muted">
                {t('overview.verifiedHint')}. {t('overview.lastWeek', { count: overview.data.verified_last_7_days })}
              </p>
              <div className="mt-6 grid grid-cols-2 gap-6 border-t border-line pt-5 sm:grid-cols-4">
                <Figure value={overview.data.total} label={t('overview.submitted')} lang={lang} />
                <Figure value={overview.data.by_status.PENDING} label={t('overview.pending')} lang={lang} />
                <Figure value={overview.data.by_status.FLAGGED} label={t('overview.flagged')} lang={lang} />
                <Figure value={overview.data.by_status.REJECTED} label={t('overview.rejected')} lang={lang} />
              </div>
            </section>

            <section className="rounded-lg border-2 border-signal bg-signal-soft p-6" aria-labelledby="signals-heading">
              <h2 id="signals-heading" className="text-signal">{t('overview.signals')}</h2>
              {signals.data && signals.data.clusters.length > 0 ? (
                <>
                  <p className="mt-1 text-lg">{t('overview.signalsText', { count: signals.data.clusters.length })}</p>
                  <ul className="mt-4 space-y-2">
                    {signals.data.clusters.slice(0, 3).map((c) => (
                      <li key={`${c.facility_id}-${c.condition_category}`} className="flex justify-between gap-3 border-b border-signal/30 pb-2">
                        <span>
                          <span className="font-medium">{c.facility_name}</span>
                          <span className="block text-sm text-muted">{t(`conditions.${c.condition_category}`)}</span>
                        </span>
                        <span className="text-right text-sm tabular-nums">
                          {t('trends.times', { value: c.max_rate_ratio.toFixed(1) })}
                          <span className="block text-muted">p {formatP(c.min_p_value)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="mt-1">{signals.isLoading ? t('common.loading') : t('overview.noSignals')}</p>
              )}
              <Link to="/trends" className="btn-secondary mt-4 border-signal text-signal hover:bg-paper">
                {t('overview.seeTrends')}
              </Link>
            </section>
          </div>

          <div className="grid gap-6 xl:grid-cols-2 [&>*]:min-w-0">
            <section className="panel p-6">
              <h2>{t('overview.byCategory')}</h2>
              <ul className="mt-4 space-y-3">
                {POLLUTION_CATEGORIES.map((c) => {
                  const n = overview.data.verified_by_category[c] ?? 0;
                  const max = Math.max(1, ...Object.values(overview.data.verified_by_category));
                  return (
                    <li key={c}>
                      <div className="flex justify-between text-sm">
                        <span>{t(`categories.${c}`)}</span>
                        <span className="tabular-nums">{formatNumber(n, lang)}</span>
                      </div>
                      <div className="mt-1 h-2 rounded bg-mist">
                        <div className="h-2 rounded" style={{ width: `${(n / max) * 100}%`, background: CATEGORY_COLOURS[c] }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
            <section className="panel p-6">
              <h2>{t('overview.topZones')}</h2>
              <table className="table mt-3">
                <tbody>
                  {overview.data.top_zones.map((z) => (
                    <tr key={z.zone_code ?? 'none'}>
                      <td>{z.zone_code ? z.zone_name : t('common.unassigned')}</td>
                      <td className="text-right tabular-nums">{formatNumber(z.verified, lang)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>

          {isAdmin && overview.data.payouts ? (
            <section className="panel p-6">
              <h2>{t('overview.payouts')}</h2>
              <div className="mt-4 grid grid-cols-2 gap-6 sm:grid-cols-4">
                <Figure value={Number(overview.data.payouts.paid_total)} label={`${t('overview.paidTotal')} (${overview.data.payouts.currency})`} lang={lang} />
                <Figure value={overview.data.payouts.by_status.SUCCESS} label={t('payoutStatus.SUCCESS')} lang={lang} />
                <Figure value={overview.data.payouts.by_status.PENDING} label={t('payoutStatus.PENDING')} lang={lang} />
                <Figure value={overview.data.payouts.by_status.FAILED} label={t('payoutStatus.FAILED')} lang={lang} />
              </div>
              {overview.data.payouts.test_payments > 0 ? (
                <p className="mt-4 text-sm text-signal">{t('overview.testPayments', { count: overview.data.payouts.test_payments })}</p>
              ) : null}
            </section>
          ) : null}
          <AssociationNotice />
        </div>
      ) : null}
    </>
  );
}
