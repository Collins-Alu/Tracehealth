import { useTranslation } from 'react-i18next';

import { STATUS_TONE, TONE_CLASSES } from '@/lib/categories';

type Status = keyof typeof STATUS_TONE;

/** A status label. Colour always comes with words, never alone. */
export function Pill({ status, labelKey = 'status' }: { status: Status; labelKey?: string }) {
  const { t } = useTranslation();
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-sm font-medium whitespace-nowrap ${TONE_CLASSES[STATUS_TONE[status]]}`}>
      {t(`${labelKey}.${status}`)}
    </span>
  );
}

export function TestBadge() {
  const { t } = useTranslation();
  return (
    <span className="rounded border border-signal px-1.5 text-xs font-semibold text-signal">{t('common.test')}</span>
  );
}
