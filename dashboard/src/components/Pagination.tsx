import { useTranslation } from 'react-i18next';

export function Pagination({
  total, limit, offset, onChange,
}: { total: number; limit: number; offset: number; onChange: (offset: number) => void }) {
  const { t } = useTranslation();
  if (total <= limit) return null;
  return (
    <div className="flex items-center justify-between gap-3 pt-3 text-sm text-muted">
      <span>{t('common.pageOf', { from: offset + 1, to: Math.min(offset + limit, total), total })}</span>
      <div className="flex gap-2">
        <button className="btn-secondary" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          {t('common.previous')}
        </button>
        <button className="btn-secondary" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
          {t('common.next')}
        </button>
      </div>
    </div>
  );
}
