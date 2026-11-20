/** Date, zone and category filters shared by the analysis pages. */
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { zonesApi } from '@/api/endpoints';
import type { ReportFilters } from '@/api/endpoints';
import { POLLUTION_CATEGORIES } from '@/types/api';

interface Props {
  value: ReportFilters;
  onChange: (next: ReportFilters) => void;
  showCategory?: boolean;
  children?: React.ReactNode;
}

export function Filters({ value, onChange, showCategory = true, children }: Props) {
  const { t } = useTranslation();
  const zones = useQuery({ queryKey: ['zones'], queryFn: zonesApi.list, staleTime: 300_000 });
  const set = (patch: Partial<ReportFilters>) => onChange({ ...value, ...patch });

  return (
    <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
      <label className="w-40">
        <span className="label">{t('common.from')}</span>
        <input className="field" type="date" value={value.date_from ?? ''} onChange={(e) => set({ date_from: e.target.value })} />
      </label>
      <label className="w-40">
        <span className="label">{t('common.to')}</span>
        <input className="field" type="date" value={value.date_to ?? ''} onChange={(e) => set({ date_to: e.target.value })} />
      </label>
      <label className="w-48">
        <span className="label">{t('common.zone')}</span>
        <select className="field" value={value.zone ?? ''} onChange={(e) => set({ zone: e.target.value })}>
          <option value="">{t('common.allZones')}</option>
          {zones.data?.map((z) => (
            <option key={z.code} value={z.code}>
              {z.name}
            </option>
          ))}
          <option value="UNASSIGNED">{t('common.unassigned')}</option>
        </select>
      </label>
      {showCategory ? (
        <label className="w-52">
          <span className="label">{t('common.category')}</span>
          <select
            className="field"
            value={value.category ?? ''}
            onChange={(e) => set({ category: e.target.value as ReportFilters['category'] })}
          >
            <option value="">{t('common.allCategories')}</option>
            {POLLUTION_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {t(`categories.${c}`)}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {children}
    </form>
  );
}
