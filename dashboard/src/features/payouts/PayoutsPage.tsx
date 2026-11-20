/**
 * Payout monitoring (Module 6). Test payments (mock provider) are badged so
 * nobody mistakes them for real money. Retrying is only offered for failed
 * payouts; the API refuses anything else.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { payoutsApi } from '@/api/endpoints';
import { PageHeader } from '@/components/PageHeader';
import { Pagination } from '@/components/Pagination';
import { Pill, TestBadge } from '@/components/Pill';
import { Empty, ErrorNote, Loading, Notice } from '@/components/State';
import { formatDate } from '@/lib/format';
import type { PayoutStatus, ProcessResult } from '@/types/api';

const PAGE = 25;

export function PayoutsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const qc = useQueryClient();
  const [status, setStatus] = useState<PayoutStatus | ''>('');
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const payouts = useQuery({ queryKey: ['payouts', status, offset], queryFn: () => payoutsApi.list({ status, limit: PAGE, offset }) });

  const done = (r: ProcessResult) => { setResult(r); qc.invalidateQueries({ queryKey: ['payouts'] }); qc.invalidateQueries({ queryKey: ['overview'] }); };
  const trigger = useMutation({ mutationFn: payoutsApi.trigger, onSuccess: done });
  const retry = useMutation({ mutationFn: payoutsApi.retry, onSuccess: done });

  return (
    <>
      <PageHeader
        title={t('payouts.title')}
        intro={t('payouts.intro')}
        actions={<button className="btn-primary" disabled={trigger.isPending} onClick={() => trigger.mutate()}>{t('payouts.sendDue')}</button>}
      />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="w-52"><span className="label">{t('common.status')}</span>
          <select className="field" value={status} onChange={(e) => { setStatus(e.target.value as PayoutStatus | ''); setOffset(0); }}>
            <option value="">{t('common.allStatuses')}</option>
            {(['PENDING', 'SUCCESS', 'FAILED'] as const).map((s) => <option key={s} value={s}>{t(`payoutStatus.${s}`)}</option>)}
          </select></label>
      </div>
      {result ? <div className="mb-4"><Notice tone="ok">{t('payouts.sent', { ...result })}</Notice></div> : null}
      {trigger.isError ? <div className="mb-4"><ErrorNote error={trigger.error} /></div> : null}
      {retry.isError ? <div className="mb-4"><ErrorNote error={retry.error} /></div> : null}
      {payouts.isLoading ? <Loading /> : null}
      {payouts.isError ? <ErrorNote error={payouts.error} onRetry={() => payouts.refetch()} /> : null}
      {payouts.data ? (
        payouts.data.items.length ? (
          <div className="panel relative overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('common.date')}</th><th>{t('payouts.reporter')}</th><th className="text-right">{t('payouts.amount')}</th>
                  <th>{t('payouts.provider')}</th><th>{t('common.status')}</th><th>{t('payouts.reference')}</th>
                  <th className="text-right">{t('payouts.attempts')}</th><th><span className="sr-only">{t('common.actions')}</span></th>
                </tr>
              </thead>
              <tbody>
                {payouts.data.items.map((p) => (
                  <tr key={p.id}>
                    <td className="whitespace-nowrap">{formatDate(p.created_at, lang, true)}</td>
                    <td>{p.reporter_name}<span className="block text-xs text-muted tabular-nums">{p.phone_masked}</span></td>
                    <td className="text-right tabular-nums whitespace-nowrap">{p.currency} {p.amount}</td>
                    <td>
                      <span className="flex items-center gap-2">
                        {p.provider === 'MOCK' ? t('payouts.mock') : t('payouts.mpesa')}
                        {p.is_test_payment ? <TestBadge /> : null}
                      </span>
                    </td>
                    <td>
                      <Pill status={p.status} labelKey="payoutStatus" />
                      {p.failure_reason ? <span className="mt-1 block max-w-xs text-xs text-danger">{p.failure_reason}</span> : null}
                    </td>
                    <td className="text-sm break-all">{p.transaction_ref ?? p.provider_request_id ?? ''}</td>
                    <td className="text-right tabular-nums">{p.attempts}</td>
                    <td className="text-right">
                      {p.status === 'FAILED' ? (
                        <button className="btn-quiet" disabled={retry.isPending} onClick={() => { if (window.confirm(t('payouts.confirmRetry'))) retry.mutate(p.id); }}>
                          {t('payouts.retry')}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 pb-3"><Pagination total={payouts.data.total} limit={PAGE} offset={offset} onChange={setOffset} /></div>
          </div>
        ) : <Empty>{t('payouts.empty')}</Empty>
      ) : null}
    </>
  );
}
