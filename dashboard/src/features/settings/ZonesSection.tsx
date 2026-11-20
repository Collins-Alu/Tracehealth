/** Verifier zones: circles on the map. Saving reassigns reports inside them. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { zonesApi } from '@/api/endpoints';
import { ErrorNote, Loading } from '@/components/State';
import type { ZoneAdmin } from '@/types/api';

const blank = { code: '', name: '', latitude: '', longitude: '', radius_km: '2' };

export function ZonesSection() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const zones = useQuery({ queryKey: ['admin-zones'], queryFn: zonesApi.adminList });
  const [form, setForm] = useState(blank);
  const refresh = () => { qc.invalidateQueries({ queryKey: ['admin-zones'] }); qc.invalidateQueries({ queryKey: ['zones'] }); };
  const create = useMutation({
    mutationFn: () => zonesApi.create({ code: form.code.trim().toUpperCase(), name: form.name.trim(), latitude: Number(form.latitude), longitude: Number(form.longitude), radius_km: Number(form.radius_km) }),
    onSuccess: () => { setForm(blank); refresh(); },
  });
  const toggle = useMutation({ mutationFn: (z: ZoneAdmin) => zonesApi.update(z.code, { is_active: !z.is_active }), onSuccess: refresh });
  const set = (k: keyof typeof blank) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate(); };

  return (
    <section className="panel p-6">
      <h2>{t('settings.zones')}</h2>
      <p className="text-sm text-muted">{t('settings.zonesHelp')}</p>
      {zones.isLoading ? <Loading /> : null}
      {zones.isError ? <ErrorNote error={zones.error} /> : null}
      {zones.data ? (
        <div className="overflow-x-auto">
          <table className="table mt-3">
            <thead><tr><th>{t('settings.code')}</th><th>{t('settings.name')}</th><th className="text-right">{t('settings.radius')}</th><th className="text-right">{t('settings.reports')}</th><th className="text-right">{t('settings.verifiers')}</th><th>{t('settings.active')}</th></tr></thead>
            <tbody>
              {zones.data.map((z) => (
                <tr key={z.code}>
                  <td>{z.code}</td><td>{z.name}</td>
                  <td className="text-right tabular-nums">{z.radius_km}</td>
                  <td className="text-right tabular-nums">{z.reports}</td>
                  <td className="text-right tabular-nums">{z.verifiers}</td>
                  <td>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" className="h-4 w-4 accent-teal" checked={z.is_active} onChange={() => toggle.mutate(z)} aria-label={`${t('settings.active')}: ${z.name}`} />
                      {z.is_active ? t('common.yes') : t('common.no')}
                    </label>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <form onSubmit={submit} className="mt-5 grid gap-3 sm:grid-cols-3 lg:grid-cols-6 lg:items-end">
        <label><span className="label">{t('settings.code')}</span><input className="field" required pattern="[A-Za-z0-9][A-Za-z0-9_\-]{1,39}" value={form.code} onChange={set('code')} /></label>
        <label className="lg:col-span-2"><span className="label">{t('settings.name')}</span><input className="field" required minLength={2} value={form.name} onChange={set('name')} /></label>
        <label><span className="label">{t('settings.latitude')}</span><input className="field" required type="number" step="any" min={-90} max={90} value={form.latitude} onChange={set('latitude')} /></label>
        <label><span className="label">{t('settings.longitude')}</span><input className="field" required type="number" step="any" min={-180} max={180} value={form.longitude} onChange={set('longitude')} /></label>
        <label><span className="label">{t('settings.radius')}</span><input className="field" required type="number" step="0.1" min={0.1} max={50} value={form.radius_km} onChange={set('radius_km')} /></label>
        <button className="btn-secondary lg:col-start-6" disabled={create.isPending}>{t('settings.addZone')}</button>
      </form>
      {create.isError ? <div className="mt-3"><ErrorNote error={create.error} /></div> : null}
      {toggle.isError ? <div className="mt-3"><ErrorNote error={toggle.error} /></div> : null}
    </section>
  );
}
