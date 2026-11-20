/** Linkage results: one row per report, clinic and condition. */
import { useTranslation } from 'react-i18next';

import { Pill } from '@/components/Pill';
import { formatDate, formatNumber, formatP } from '@/lib/format';
import type { Linkage } from '@/types/api';

export function LinkageTable({ items, showReport = true }: { items: Linkage[]; showReport?: boolean }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>{t('common.status')}</th>
            {showReport ? <th>{t('reports.reported')}</th> : null}
            <th>{t('trends.facility')}</th>
            <th>{t('common.condition')}</th>
            <th className="text-right">{t('trends.before')}</th>
            <th className="text-right">{t('trends.after')}</th>
            <th className="text-right">{t('trends.rateRatio')}</th>
            <th className="text-right">{t('trends.pValue')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((l) => (
            <tr key={l.id}>
              <td>
                <Pill status={l.status} />
                {l.insufficient_reason ? (
                  <span className="mt-1 block text-xs text-muted">{t(`trends.insufficient.${l.insufficient_reason}`)}</span>
                ) : null}
              </td>
              {showReport ? (
                <td>
                  {t(`categories.${l.report_category}`)}
                  <span className="block text-xs text-muted">{formatDate(l.report_captured_at, lang)}</span>
                </td>
              ) : null}
              <td>
                {l.facility_name}
                <span className="block text-xs text-muted">{t('trends.distance', { km: formatNumber(l.distance_km, lang, 1) })}</span>
              </td>
              <td>{t(`conditions.${l.condition_category}`)}</td>
              <td className="text-right tabular-nums">{rate(l.baseline_visits, l.baseline_days, lang)}</td>
              <td className="text-right tabular-nums">{rate(l.followup_visits, l.followup_days, lang)}</td>
              <td className="text-right tabular-nums">{l.rate_ratio !== null ? t('trends.times', { value: l.rate_ratio.toFixed(2) }) : ''}</td>
              <td className="text-right tabular-nums">{formatP(l.p_value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Visits per week, so periods of different lengths compare fairly. */
function rate(visits: number | null, days: number | null, lang: string) {
  if (visits === null || !days) return '';
  return `${formatNumber((visits / days) * 7, lang, 1)}/wk`;
}
