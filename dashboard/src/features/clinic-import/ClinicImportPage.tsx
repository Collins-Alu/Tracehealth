/**
 * Clinic data import (FR 3.1). The file is checked as a whole: if any row is
 * wrong, or anything looks like patient data, nothing is stored and every
 * problem is listed so it can be fixed in one go.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { clinicApi } from '@/api/endpoints';
import { PageHeader } from '@/components/PageHeader';
import { Empty, ErrorNote, Loading, Notice } from '@/components/State';
import { formatDate, formatNumber } from '@/lib/format';
import type { ImportResult } from '@/types/api';

export function ClinicImportPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [missing, setMissing] = useState(false);
  const history = useQuery({ queryKey: ['imports'], queryFn: clinicApi.imports });
  const facilities = useQuery({ queryKey: ['facilities'], queryFn: clinicApi.facilities });

  const upload = useMutation({
    mutationFn: (f: File) => clinicApi.upload(f),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['imports'] });
      qc.invalidateQueries({ queryKey: ['facilities'] });
      qc.invalidateQueries({ queryKey: ['linkages'] });
      qc.invalidateQueries({ queryKey: ['linkage-trends'] });
      qc.invalidateQueries({ queryKey: ['trends'] });
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setMissing(true);
      return;
    }
    setMissing(false);
    upload.mutate(file);
  }

  async function downloadTemplate() {
    const res = await clinicApi.template();
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tracehealth-clinic-template.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader title={t('clinic.title')} intro={t('clinic.intro')} actions={<button className="btn-secondary" onClick={downloadTemplate}>{t('clinic.template')}</button>} />
      <form onSubmit={submit} className="panel mb-6 flex flex-wrap items-end gap-3 p-6">
        <label className="min-w-64 flex-1">
          <span className="label">{t('clinic.choose')}</span>
          <input
            ref={input}
            className="field file:mr-3 file:rounded file:border-0 file:bg-teal-soft file:px-3 file:py-1 file:text-teal-dark"
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); upload.reset(); }}
          />
        </label>
        <button className="btn-primary" disabled={upload.isPending}>
          {upload.isPending ? t('clinic.uploading') : t('clinic.upload')}
        </button>
        {missing ? <p role="alert" className="w-full text-danger">{t('clinic.noFile')}</p> : null}
      </form>

      {upload.isError ? <div className="mb-6"><ErrorNote error={upload.error} /></div> : null}
      {upload.data ? <div className="mb-6"><ImportOutcome result={upload.data} /></div> : null}

      <section className="panel mb-6 p-6">
        <h2>{t('clinic.history')}</h2>
        {history.isLoading ? <Loading /> : null}
        {history.isError ? <ErrorNote error={history.error} onRetry={() => history.refetch()} /> : null}
        {history.data && history.data.length === 0 ? <Empty>{t('common.none')}</Empty> : null}
        {history.data && history.data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table mt-3">
              <thead>
                <tr>
                  <th>{t('common.date')}</th><th>{t('clinic.file')}</th><th>{t('common.status')}</th>
                  <th className="text-right">{t('clinic.inserted')}</th><th className="text-right">{t('clinic.updated')}</th><th>{t('clinic.by')}</th>
                </tr>
              </thead>
              <tbody>
                {history.data.map((b) => (
                  <tr key={b.id}>
                    <td>{formatDate(b.created_at, lang, true)}</td>
                    <td className="break-all">{b.filename}</td>
                    <td>
                      <span className={b.status === 'ACCEPTED' ? 'text-ok' : 'text-danger'}>
                        {b.status === 'ACCEPTED' ? t('clinic.accepted') : t('clinic.rejected')}
                      </span>
                    </td>
                    <td className="text-right tabular-nums">{formatNumber(b.summary?.rows_inserted ?? 0, lang)}</td>
                    <td className="text-right tabular-nums">{formatNumber(b.summary?.rows_updated ?? 0, lang)}</td>
                    <td>{b.imported_by_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="panel p-6">
        <h2>{t('clinic.facilities')}</h2>
        {facilities.data && facilities.data.length === 0 ? <Empty>{t('common.none')}</Empty> : null}
        {facilities.data && facilities.data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="table mt-3">
              <thead>
                <tr><th>{t('clinic.code')}</th><th>{t('trends.facility')}</th><th>{t('clinic.area')}</th><th className="text-right">{t('clinic.periods')}</th><th>{t('clinic.latest')}</th></tr>
              </thead>
              <tbody>
                {facilities.data.map((f) => (
                  <tr key={f.id}>
                    <td>{f.external_code}</td><td>{f.name}</td><td>{f.area_code}</td>
                    <td className="text-right tabular-nums">{formatNumber(f.summaries, lang)}</td>
                    <td>{formatDate(f.latest_period_end, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </>
  );
}

function ImportOutcome({ result }: { result: ImportResult }) {
  const { t, i18n } = useTranslation();
  const { batch, linkage } = result;
  if (batch.status === 'REJECTED') {
    return (
      <section role="alert" className="rounded-lg border-2 border-danger bg-paper p-6" data-testid="import-rejected">
        <h2 className="text-danger">{t('clinic.rejected')}</h2>
        <h3 className="mt-3 label">{t('clinic.problems')}</h3>
        <table className="table">
          <thead><tr><th>{t('clinic.row')}</th><th>{t('clinic.field')}</th><th>{t('clinic.message')}</th></tr></thead>
          <tbody>
            {(batch.errors ?? []).map((p, i) => (
              <tr key={i}><td className="tabular-nums">{p.row ?? ''}</td><td>{p.field ?? ''}</td><td>{p.message}</td></tr>
            ))}
          </tbody>
        </table>
      </section>
    );
  }
  const s = batch.summary;
  return (
    <Notice tone="ok">
      <p className="font-semibold" data-testid="import-accepted">{t('clinic.accepted')}: {t('clinic.rows', { count: batch.row_count })}</p>
      {s ? (
        <p className="mt-1 text-sm">
          {t('clinic.inserted')} {formatNumber(s.rows_inserted, i18n.language)}. {t('clinic.updated')} {formatNumber(s.rows_updated, i18n.language)}.{' '}
          {t('clinic.facilitiesCreated')} {formatNumber(s.facilities_created, i18n.language)}. {t('clinic.smallCounts')} {formatNumber(s.small_counts, i18n.language)}.
        </p>
      ) : null}
      {linkage ? (
        <p className="mt-1 text-sm">
          {t('clinic.linkageDone', { signal: linkage.by_status.SIGNAL, none: linkage.by_status.NO_SIGNAL, insufficient: linkage.by_status.INSUFFICIENT_DATA })}
        </p>
      ) : null}
    </Notice>
  );
}
