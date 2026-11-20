/** Account: who is logged in, their roles and zone, language, push status, logout. */
import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, StyleSheet, Text, View } from 'react-native';

import { verificationApi } from '@/api/verification';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { LanguageToggle } from '@/components/LanguageToggle';
import { Message } from '@/components/Message';
import { PayoutSettings } from '@/components/PayoutSettings';
import { Screen } from '@/components/Screen';
import { currentPushSupport } from '@/notifications/push';
import { useSync } from '@/offline/SyncContext';
import { colors, font, radius, spacing } from '@/theme';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

export default function Account() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { queue } = useSync();
  const [zoneName, setZoneName] = useState<string | null>(null);
  const push = currentPushSupport();
  const [languageNote, setLanguageNote] = useState<string | null>(null);

  useEffect(() => {
    const code = user?.assigned_zone;
    if (!code) return;
    verificationApi
      .zones()
      .then((zones) => setZoneName(zones.find((z) => z.code === code)?.name ?? code))
      .catch(() => setZoneName(code));
  }, [user?.assigned_zone]);

  if (!user) return null;

  function confirmLogout() {
    const message = queue.length > 0 ? t('home.logoutQueuedWarning') : t('home.logoutConfirm');
    Alert.alert(t('common.logout'), message, [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('common.logout'), style: 'destructive', onPress: () => logout() },
    ]);
  }

  return (
    <Screen>
      <View style={styles.card}>
        <Ionicons name="person-circle" size={56} color={colors.primary} />
        <Text style={styles.name}>{user.full_name}</Text>
        <Row label={t('account.phone')} value={user.phone_number} />
        <Row
          label={t('account.roles')}
          value={user.roles.map((r) => t(`account.roleNames.${r}`)).join(', ')}
        />
        {user.roles.includes('VERIFIER') ? (
          <Row label={t('account.zone')} value={zoneName ?? user.assigned_zone ?? t('account.noZone')} />
        ) : null}
        <Row
          label={t('account.pushTitle')}
          value={push.supported ? t('account.pushOn') : t('account.pushInboxOnly')}
        />
      </View>
      <PayoutSettings />
      <Text style={styles.section}>{t('common.language')}</Text>
      <LanguageToggle onSaveFailed={() => setLanguageNote(t('account.languageSaveFailed'))} />
      <Message text={languageNote} tone="info" />
      <Button title={t('common.logout')} icon="log-out" variant="secondary" onPress={confirmLogout} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.lg,
    borderRadius: radius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  name: { fontSize: font.title, fontWeight: '700', color: colors.text },
  row: { alignSelf: 'stretch', gap: 2 },
  label: { fontSize: font.small, fontWeight: '700', color: colors.textMuted, textTransform: 'uppercase' },
  value: { fontSize: font.body, color: colors.text },
  section: { fontSize: font.body, fontWeight: '700', color: colors.text, textAlign: 'center' },
});
