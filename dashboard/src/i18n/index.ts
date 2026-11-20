/**
 * Dashboard translations: English and Swahili (NFR 3). The choice is kept in
 * the browser; the signed-in user's preferred language is applied at sign-in.
 * Swahili text needs native-speaker review before the pilot (D13).
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import sw from './sw.json';

export type Lang = 'en' | 'sw';
const KEY = 'th.lang';

function initial(): Lang {
  try {
    const saved = window.localStorage.getItem(KEY);
    if (saved === 'en' || saved === 'sw') return saved;
  } catch {
    // storage unavailable
  }
  return navigator.language?.startsWith('sw') ? 'sw' : 'en';
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, sw: { translation: sw } },
  lng: typeof window === 'undefined' ? 'en' : initial(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng;
  try {
    window.localStorage.setItem(KEY, lng);
  } catch {
    // not fatal
  }
});

export default i18n;
