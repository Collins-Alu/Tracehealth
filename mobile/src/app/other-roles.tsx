/**
 * Agency staff and administrators use the web dashboard (Sprint 3), not the
 * mobile app. They land here and can switch language or log out.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Text } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { LanguageToggle } from '@/components/LanguageToggle';
import { Screen } from '@/components/Screen';
import { colors, font } from '@/theme';

export default function OtherRoles() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  return (
    <Screen>
      <Text style={{ fontSize: font.title, fontWeight: '700', color: colors.text }}>
        {user?.full_name}
      </Text>
      <Text style={{ fontSize: font.body, color: colors.text, lineHeight: 22 }}>
        {t('otherRoles.text')}
      </Text>
      <LanguageToggle />
      <Button title={t('common.logout')} icon="log-out" variant="secondary" onPress={logout} />
    </Screen>
  );
}
