/** One report: photo, place, decision, reward (admins) and its health linkages. */
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { linkageApi, reportsApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthContext';
import { Dialog } from '@/components/Dialog';
import { Pill, TestBadge } from '@/components/Pill';
import { ReportPhoto } from '@/components/ReportPhoto';
import { AssociationNotice, ErrorNote, Loading } from '@/components/State';
import { LinkageTable } from '@/features/trends/LinkageTable';
import { formatDate } from '@/lib/format';

export function ReportDetail({ reportId, onClose }: { reportId: string | null; onClose: () => void }) {
  const { t, i18n } = useTranslation();
  const { isAdmin } = useAuth();
  const lang = i18n.language;
  const report = useQuery({ queryKey: ['report', reportId], queryFn: () => reportsApi.get(reportId!), enabled: !!reportId });
  const linkages = useQuery({
    queryKey: ['linkages', 'report', reportId],
    queryFn: () => linkageApi.list({ report_id: reportId!, limit: 50, offset: 0 }),
    enabled: !!reportId && report.data?.status === 'VERIFIED',
  });
  const r = report.data;

  return (
    <Dialog open={!!reportId} onClose={onClose} title={r ? t(`categories.${r.category}`) : t('common.details')} wide>
      {report.isLoading ? <Loading /> : null}
      {report.isError ? <ErrorNote error={report.error} /> : null}
      {r ? (
        <div className="space-y-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <ReportPhoto reportId={r.id} alt={t(`categories.${r.category}`)} />
            <dl className="space-y-3">
              <div><dt className="label">{t('common.status')}</dt><dd><Pill status={r.status} /></dd></div>
              <div><dt className="label">{t('reports.reported')}</dt><dd>{formatDate(r.captured_at, lang, true)}</dd></div>
              <div><dt className="label">{t('common.zone')}</dt><dd>{r.zone_code ?? t('common.unassigned')}</dd></div>
              <div>
                <dt className="label">{t('reports.location')}</dt>
                <dd className="tabular-nums">
                  {r.latitude.toFixed(5)}, {r.longitude.toFixed(5)}{' '}
                  <a className="text-teal underline" target="_blank" rel="noreferrer" href={`https://www.openstreetmap.org/?mlat=${r.latitude}&mlon=${r.longitude}#map=17/${r.latitude}/${r.longitude}`}>
                    {t('reports.openMap')}
                  </a>
                </dd>
              </div>
              <div><dt className="label">{t('common.details')}</dt><dd>{t(`reports.sync.${r.sync_status}`)}</dd></div>
            </dl>
          </div>
          {r.description ? (<div><h3 className="label">{t('reports.description')}</h3><p>{r.description}</p></div>) : null}
          {r.decision_reason ? (<div><h3 className="label">{t('reports.reason')}</h3><p>{r.decision_reason}</p></div>) : null}
          {isAdmin && r.payout ? (
            <div>
              <h3 className="label">{t('reports.payout')}</h3>
              <p className="flex items-center gap-2">
                <Pill status={r.payout.status} labelKey="payoutStatus" />
                <span className="tabular-nums">{r.payout.currency} {r.payout.amount}</span>
                {r.payout.is_test_payment ? <TestBadge /> : null}
              </p>
            </div>
          ) : null}
          {r.status === 'VERIFIED' ? (
            <div>
              <h3 className="mb-2">{t('reports.linkages')}</h3>
              {linkages.isLoading ? <Loading /> : null}
              {linkages.isError ? <ErrorNote error={linkages.error} /> : null}
              {linkages.data && linkages.data.items.length === 0 ? <p className="text-muted">{t('reports.noLinkages')}</p> : null}
              {linkages.data && linkages.data.items.length > 0 ? (
                <div className="space-y-3">
                  <LinkageTable items={linkages.data.items} showReport={false} />
                  <AssociationNotice />
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </Dialog>
  );
}
