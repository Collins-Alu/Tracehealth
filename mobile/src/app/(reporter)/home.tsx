/** Reporter home: one big "Report pollution" action and the sync status. */
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { LanguageToggle } from '@/components/LanguageToggle';
import { SafetyNotice } from '@/components/SafetyNotice';
import { Screen } from '@/components/Screen';
import { useSync } from '@/offline/SyncContext';
import { colors, font, radius, spacing } from '@/theme';

export default function Home() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const { queue, isOnline, isSyncing, syncNow } = useSync();
  const waiting = queue.filter((q) => q.state !== 'NEEDS_ATTENTION').length;
  const attention = queue.filter((q) => q.state === 'NEEDS_ATTENTION').length;

  function confirmLogout() {
    const message = waiting + attention > 0 ? t('home.logoutQueuedWarning') : t('home.logoutConfirm');
    Alert.alert(t('common.logout'), message, [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('common.logout'), style: 'destructive', onPress: () => logout() },
    ]);
  }

  return (
    <Screen>
      <Text style={styles.greeting}>{t('home.greeting', { name: user?.full_name.split(' ')[0] })}</Text>

      <Pressable
        testID="new-report"
        accessibilityRole="button"
        accessibilityLabel={t('home.newReport')}
        onPress={() => router.push('/new-report')}
        style={({ pressed }) => [styles.bigAction, pressed && { opacity: 0.9 }]}
      >
        <Ionicons name="camera" size={48} color="#FFFFFF" />
        <Text style={styles.bigActionTitle}>{t('home.newReport')}</Text>
        <Text style={styles.bigActionHint}>{t('home.newReportHint')}</Text>
      </Pressable>

      <SafetyNotice />

      <View style={styles.syncCard}>
        <Ionicons
          name={waiting + attention === 0 ? 'cloud-done' : 'cloud-offline'}
          size={26}
          color={attention > 0 ? colors.danger : colors.queued}
        />
        <View style={{ flex: 1, gap: 2 }}>
          {waiting + attention === 0 ? (
            <Text style={styles.syncText}>{t('home.allSent')}</Text>
          ) : null}
          {waiting > 0 ? (
            <Text style={styles.syncText}>{t('home.waiting', { count: waiting })}</Text>
          ) : null}
          {attention > 0 ? (
            <Text style={[styles.syncText, { color: colors.danger }]}>
              {t('home.needsAttention', { count: attention })}
            </Text>
          ) : null}
        </View>
      </View>
      {waiting > 0 && isOnline ? (
        <Button
          title={t('home.sendNow')}
          icon="sync"
          variant="secondary"
          loading={isSyncing}
          onPress={() => syncNow(true)}
        />
      ) : null}
      {attention > 0 ? (
        <Button
          title={t('home.myReports')}
          variant="secondary"
          onPress={() => router.push('/reports')}
        />
      ) : null}

      <View style={styles.footer}>
        <LanguageToggle />
        <Button title={t('common.logout')} icon="log-out" variant="ghost" onPress={confirmLogout} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  greeting: { fontSize: font.title, fontWeight: '700', color: colors.text },
  bigAction: {
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: 'center',
    gap: spacing.xs,
  },
  bigActionTitle: { color: '#FFFFFF', fontSize: font.title, fontWeight: '800' },
  bigActionHint: { color: '#E3F1EE', fontSize: font.body },
  syncCard: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  syncText: { fontSize: font.body, color: colors.text },
  footer: { marginTop: spacing.lg, gap: spacing.sm },
});
