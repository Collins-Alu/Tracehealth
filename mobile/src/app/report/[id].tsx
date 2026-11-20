/**
 * Report details and status (Track Report Status & Payout use case).
 * Works for reports still on the phone (?local=1) and reports on the server.
 */
import { router, useLocalSearchParams } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, Alert, Image, StyleSheet, Text, View } from 'react-native';

import { reportsApi } from '@/api/reports';
import type { Report } from '@/api/types';
import { tokenStore } from '@/auth/tokenStore';
import { Button } from '@/components/Button';
import { Message } from '@/components/Message';
import { Screen } from '@/components/Screen';
import { StatusBadge } from '@/components/StatusBadge';
import { API_URL } from '@/config';
import { useSync } from '@/offline/SyncContext';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';
import { formatCoords, formatDateTime } from '@/utils/format';

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      {typeof value === 'string' ? <Text style={styles.value}>{value}</Text> : value}
    </View>
  );
}

export default function ReportDetail() {
  const { id, local } = useLocalSearchParams<{ id: string; local?: string }>();
  return local === '1' ? <LocalReport clientReportId={id} /> : <ServerReport id={id} />;
}

function LocalReport({ clientReportId }: { clientReportId: string }) {
  const { t, i18n } = useTranslation();
  const { queue, retry, discard, isSyncing } = useSync();
  const item = queue.find((q) => q.clientReportId === clientReportId);

  if (!item) {
    // It was sent while this screen was open
    return (
      <Screen>
        <Message tone="info" text={t('submitted.sentTitle')} />
        <Button title={t('submitted.viewReports')} onPress={() => router.replace('/reports')} />
      </Screen>
    );
  }

  function confirmDiscard() {
    Alert.alert(t('detail.discard'), t('detail.discardConfirm'), [
      { text: t('common.cancel'), style: 'cancel' },
      {
        text: t('common.delete'),
        style: 'destructive',
        onPress: async () => {
          await discard(clientReportId);
          router.back();
        },
      },
    ]);
  }

  return (
    <Screen>
      <Image source={{ uri: item.photoUri }} style={styles.photo} />
      <StatusBadge status={item.state} />
      {item.state === 'NEEDS_ATTENTION' ? (
        <Message text={`${t('detail.needsAttentionExplain')} ${item.lastError ?? ''}`} />
      ) : (
        <Message tone="info" text={t('detail.queuedExplain')} />
      )}
      <Field label={t('detail.category')} value={t(`categories.${item.category}`)} />
      <Field label={t('detail.reportedAt')} value={formatDateTime(item.capturedAt, i18n.language)} />
      <Field label={t('detail.location')} value={formatCoords(item.latitude, item.longitude)} />
      {item.description ? <Field label={t('detail.description')} value={item.description} /> : null}
      <Button
        title={t('detail.retryNow')}
        icon="refresh"
        onPress={() => retry(clientReportId)}
        loading={isSyncing}
        disabled={item.state === 'SYNCING'}
      />
      <Button
        title={t('detail.discard')}
        icon="trash"
        variant="danger"
        onPress={confirmDiscard}
        disabled={item.state === 'SYNCING'}
      />
    </Screen>
  );
}

function ServerReport({ id }: { id: string }) {
  const { t, i18n } = useTranslation();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    reportsApi
      .get(id)
      .then(setReport)
      .catch((e) => setError(userMessage(e, t)));
  }, [id, t]);

  if (error) {
    return (
      <Screen>
        <Message text={error} />
      </Screen>
    );
  }
  if (!report) {
    return (
      <Screen>
        <ActivityIndicator size="large" color={colors.primary} />
      </Screen>
    );
  }

  const token = tokenStore.getAccessToken();
  const payout = report.payout;
  return (
    <Screen>
      <Image
        source={{
          uri: `${API_URL}${report.photo_url}`,
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        }}
        style={styles.photo}
        accessibilityIgnoresInvertColors
      />
      <Field label={t('detail.status')} value={<StatusBadge status={report.status} />} />
      {report.decision_reason ? (
        <Field label={t('detail.reason')} value={report.decision_reason} />
      ) : null}
      <Field label={t('detail.category')} value={t(`categories.${report.category}`)} />
      <Field label={t('detail.reportedAt')} value={formatDateTime(report.captured_at, i18n.language)} />
      <Field label={t('detail.location')} value={formatCoords(report.latitude, report.longitude)} />
      {report.description ? <Field label={t('detail.description')} value={report.description} /> : null}
      {report.sync_status === 'SYNCED_FROM_OFFLINE' ? (
        <Text style={styles.note}>{t('detail.sentFromOffline')}</Text>
      ) : null}
      <View style={styles.payoutCard}>
        <Text style={styles.label}>{t('detail.payout')}</Text>
        {payout ? (
          <>
            <Text style={styles.payoutAmount}>
              {payout.currency} {payout.amount} · {t(`detail.payoutStatus.${payout.status}`)}
            </Text>
            {payout.is_test_payment ? (
              <Text style={styles.testBadge}>{t('detail.payoutTest')}</Text>
            ) : null}
          </>
        ) : (
          <Text style={styles.value}>{t('detail.payoutNone')}</Text>
        )}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  photo: { width: '100%', aspectRatio: 4 / 3, borderRadius: radius.md, backgroundColor: colors.border },
  field: { gap: 4 },
  label: { fontSize: font.small, fontWeight: '700', color: colors.textMuted, textTransform: 'uppercase' },
  value: { fontSize: font.large, color: colors.text },
  note: { fontSize: font.body, color: colors.textMuted, fontStyle: 'italic' },
  payoutCard: {
    gap: spacing.xs,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  payoutAmount: { fontSize: font.large, fontWeight: '700', color: colors.text },
  testBadge: {
    alignSelf: 'flex-start',
    fontSize: font.small,
    fontWeight: '700',
    color: colors.warning,
    backgroundColor: colors.warningSoft,
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.sm,
  },
});
