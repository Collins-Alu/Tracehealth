/**
 * English and Swahili translations (NFR 3).
 *
 * The starting language follows the phone's language; the user can switch at
 * any time and the choice is remembered. Swahili text is a developer draft and
 * must be reviewed by a native speaker before the pilot (decision D13).
 */
import { getLocales } from 'expo-localization';
import * as SecureStore from 'expo-secure-store';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import sw from './sw.json';

export type AppLanguage = 'en' | 'sw';
const LANGUAGE_KEY = 'tracehealth.language';

function deviceLanguage(): AppLanguage {
  try {
    return getLocales()[0]?.languageCode === 'sw' ? 'sw' : 'en';
  } catch {
    return 'en';
  }
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, sw: { translation: sw } },
  lng: deviceLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false }, // React already escapes text
  returnNull: false,
});

/** Apply the language the user chose last time, if any. */
export async function restoreLanguage(): Promise<void> {
  try {
    const saved = await SecureStore.getItemAsync(LANGUAGE_KEY);
    if (saved === 'en' || saved === 'sw') await i18n.changeLanguage(saved);
  } catch {
    // Keep the device language if storage is unavailable
  }
}

export async function setLanguage(language: AppLanguage): Promise<void> {
  await i18n.changeLanguage(language);
  try {
    await SecureStore.setItemAsync(LANGUAGE_KEY, language);
  } catch {
    // Not fatal: the choice just won't survive a restart
  }
}

export default i18n;
