import React from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { authApi } from '@/api/auth';
import { tokenStore } from '@/auth/tokenStore';
import { type AppLanguage, setLanguage } from '@/i18n';
import { colors, font, radius, spacing } from '@/theme';

const OPTIONS: { code: AppLanguage; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'sw', label: 'Kiswahili' },
];

/**
 * Switch the app language. When someone is logged in, the choice is also
 * saved to their account, so SMS and push messages arrive in the same
 * language. Saving is best effort: offline, the phone keeps the choice and
 * the account is updated the next time they change it while online.
 */
export async function chooseLanguage(code: AppLanguage): Promise<boolean> {
  await setLanguage(code);
  const user = tokenStore.getUser();
  const wanted = code === 'sw' ? 'SW' : 'EN';
  if (!user || user.preferred_language === wanted) return true;
  try {
    await tokenStore.saveUser(await authApi.updateMe({ preferred_language: wanted }));
    return true;
  } catch {
    return false;
  }
}

export function LanguageToggle({ onSaveFailed }: { onSaveFailed?: () => void }) {
  const { i18n, t } = useTranslation();
  return (
    <View style={styles.row} accessibilityRole="radiogroup" accessibilityLabel={t('common.language')}>
      {OPTIONS.map(({ code, label }) => {
        const selected = i18n.language === code;
        return (
          <Pressable
            key={code}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            testID={`language-${code}`}
            onPress={async () => {
              const saved = await chooseLanguage(code);
              if (!saved) onSaveFailed?.();
            }}
            style={[styles.option, selected && styles.selected]}
          >
            <Text style={[styles.text, selected && styles.selectedText]}>{label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: spacing.sm, alignSelf: 'center' },
  option: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minHeight: 44,
    justifyContent: 'center',
    borderRadius: radius.lg,
    borderWidth: 1.5,
    borderColor: colors.primary,
  },
  selected: { backgroundColor: colors.primary },
  text: { fontSize: font.body, color: colors.primary, fontWeight: '600' },
  selectedText: { color: '#FFFFFF' },
});
