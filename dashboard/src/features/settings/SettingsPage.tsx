/**
 * System settings (administrators). Each value is checked by the API; a
 * refused value comes back with a plain explanation shown next to the field.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { adminApi, linkageApi } from '@/api/endpoints';
import { PageHeader } from '@/components/PageHeader';
import { ErrorNote, Loading, Notice, errorText } from '@/components/State';
import { CONDITIONS, type ConditionCategory, POLLUTION_CATEGORIES, type Setting } from '@/types/api';

import { ZonesSection } from './ZonesSection';

const LINKAGE_FIELDS = [
  { key: 'linkage.radius_km', label: 'settings.radius_km', step: '0.1' },
  { key: 'linkage.baseline_weeks', label: 'settings.baseline_weeks', step: '1' },
  { key: 'linkage.followup_weeks', label: 'settings.followup_weeks', step: '1' },
  { key: 'linkage.min_baseline_visits', label: 'settings.min_baseline_visits', step: '1' },
  { key: 'linkage.p_value_threshold', label: 'settings.p_value_threshold', step: '0.001' },
];

function useSave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) => adminApi.updateSetting(key, value),
    onSuccess: (s) => {
      qc.invalidateQueries({ queryKey: ['settings'] });
      if (s.key.startsWith('linkage.')) {
        for (const k of ['linkages', 'linkage-trends', 'overview']) qc.invalidateQueries({ queryKey: [k] });
      }
    },
  });
}

function NumberSetting({ setting, label, step }: { setting: Setting; label: string; step: string }) {
  const { t } = useTranslation();
  const [value, setValue] = useState(String(setting.value));
  const save = useSave();
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate({ key: setting.key, value: Number(value) }); };
  const changed = value !== String(setting.value);
  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3 border-b border-line py-3 last:border-0">
      <label className="min-w-64 flex-1">
        <span className="label">{t(label)}</span>
        <input className="field max-w-40" type="number" step={step} value={value} onChange={(e) => { setValue(e.target.value); save.reset(); }} />
      </label>
      <button className="btn-secondary" disabled={!changed || save.isPending}>{t('common.save')}</button>
      {save.isSuccess && !changed ? <span role="status" className="text-ok">{t('common.saved')}</span> : null}
      {save.isError ? <span role="alert" className="w-full text-danger">{errorText(save.error, t)}</span> : null}
    </form>
  );
}

function TextSetting({ setting, label }: { setting: Setting; label: string }) {
  const { t } = useTranslation();
  const [value, setValue] = useState(String(setting.value));
  const save = useSave();
  const changed = value !== String(setting.value);
  return (
    <form onSubmit={(e) => { e.preventDefault(); save.mutate({ key: setting.key, value: value.trim().toUpperCase() }); }} className="flex flex-wrap items-end gap-3 py-3">
      <label className="min-w-64 flex-1">
        <span className="label">{t(label)}</span>
        <input className="field max-w-40" maxLength={3} value={value} onChange={(e) => { setValue(e.target.value); save.reset(); }} />
      </label>
      <button className="btn-secondary" disabled={!changed || save.isPending}>{t('common.save')}</button>
      {save.isSuccess && !changed ? <span role="status" className="text-ok">{t('common.saved')}</span> : null}
      {save.isError ? <span role="alert" className="w-full text-danger">{errorText(save.error, t)}</span> : null}
    </form>
  );
}

function MappingSetting({ setting }: { setting: Setting }) {
  const { t } = useTranslation();
  const initial = setting.value as Record<string, ConditionCategory[]>;
  const [mapping, setMapping] = useState<Record<string, ConditionCategory[]>>(initial);
  const save = useSave();
  const toggle = (cat: string, cond: ConditionCategory) => {
    save.reset();
    setMapping((m) => {
      const cur = m[cat] ?? [];
      return { ...m, [cat]: cur.includes(cond) ? cur.filter((c) => c !== cond) : [...cur, cond] };
    });
  };
  return (
    <div className="mt-6">
      <h3>{t('settings.mapping')}</h3>
      <p className="text-sm text-muted">{t('settings.mappingHelp')}</p>
      <div className="mt-3 overflow-x-auto">
        <table className="table">
          <thead>
            <tr>
              <th>{t('common.category')}</th>
              {CONDITIONS.map((c) => <th key={c} className="text-center">{t(`conditions.${c}`)}</th>)}
            </tr>
          </thead>
          <tbody>
            {POLLUTION_CATEGORIES.map((cat) => (
              <tr key={cat}>
                <td>{t(`categories.${cat}`)}</td>
                {CONDITIONS.map((cond) => (
                  <td key={cond} className="text-center">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-teal"
                      aria-label={`${t(`categories.${cat}`)}: ${t(`conditions.${cond}`)}`}
                      checked={(mapping[cat] ?? []).includes(cond)}
                      onChange={() => toggle(cat, cond)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <button className="btn-secondary" disabled={save.isPending} onClick={() => save.mutate({ key: setting.key, value: mapping })}>{t('common.save')}</button>
        {save.isSuccess ? <span role="status" className="text-ok">{t('common.saved')}</span> : null}
        {save.isError ? <span role="alert" className="text-danger">{errorText(save.error, t)}</span> : null}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const settings = useQuery({ queryKey: ['settings'], queryFn: adminApi.settings });
  const recompute = useMutation({
    mutationFn: linkageApi.compute,
    onSuccess: () => { for (const k of ['linkages', 'linkage-trends', 'overview']) qc.invalidateQueries({ queryKey: [k] }); },
  });
  const byKey = new Map(settings.data?.map((s) => [s.key, s]));
  const get = (k: string) => byKey.get(k);

  return (
    <>
      <PageHeader title={t('settings.title')} />
      {settings.isLoading ? <Loading /> : null}
      {settings.isError ? <ErrorNote error={settings.error} onRetry={() => settings.refetch()} /> : null}
      {settings.data ? (
        <div className="space-y-6">
          <section className="panel p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2>{t('settings.linkage')}</h2>
                <p className="text-sm text-muted">{t('settings.linkageHelp')}</p>
              </div>
              <button className="btn-secondary" disabled={recompute.isPending} onClick={() => recompute.mutate()}>{t('settings.recompute')}</button>
            </div>
            {recompute.data ? <div className="mt-3"><Notice tone="ok">{t('settings.recomputed', { count: recompute.data.linkages })}</Notice></div> : null}
            {recompute.isError ? <div className="mt-3"><ErrorNote error={recompute.error} /></div> : null}
            <div className="mt-3">
              {LINKAGE_FIELDS.map((f) => {
                const s = get(f.key);
                return s ? <NumberSetting key={`${s.key}-${s.updated_at}`} setting={s} label={f.label} step={f.step} /> : null;
              })}
            </div>
            {get('linkage.category_mapping') ? <MappingSetting key={get('linkage.category_mapping')!.updated_at} setting={get('linkage.category_mapping')!} /> : null}
          </section>

          <div className="grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
            <section className="panel p-6">
              <h2>{t('settings.payout')}</h2>
              {get('payout.amount') ? <NumberSetting key={get('payout.amount')!.updated_at} setting={get('payout.amount')!} label="settings.amount" step="1" /> : null}
              {get('payout.currency') ? <TextSetting key={get('payout.currency')!.updated_at} setting={get('payout.currency')!} label="settings.currency" /> : null}
            </section>
            <section className="panel p-6">
              <h2>{t('settings.privacy')}</h2>
              {get('dashboard.small_count_threshold') ? (
                <NumberSetting key={get('dashboard.small_count_threshold')!.updated_at} setting={get('dashboard.small_count_threshold')!} label="settings.smallCount" step="1" />
              ) : null}
            </section>
          </div>
          <ZonesSection />
        </div>
      ) : null}
    </>
  );
}
