import { useTranslation } from 'react-i18next';

export function LanguageSwitch() {
  const { i18n, t } = useTranslation();
  return (
    <div role="group" aria-label={t('nav.language')} className="flex gap-1 px-3">
      {(['en', 'sw'] as const).map((lng) => (
        <button
          key={lng}
          aria-pressed={i18n.language === lng}
          onClick={() => i18n.changeLanguage(lng)}
          className={`rounded px-2 py-1 text-sm ${
            i18n.language === lng ? 'bg-ink text-white' : 'text-ink hover:bg-teal-soft'
          }`}
        >
          {lng === 'en' ? 'English' : 'Kiswahili'}
        </button>
      ))}
    </div>
  );
}
