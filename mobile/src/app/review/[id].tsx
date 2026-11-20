/**
 * Review one report and decide (UML B.4 steps 3-12).
 *
 * Shows the evidence (photo, category, time, place, description), other
 * reports close by in place and time (to spot duplicates), then the decision
 * panel. The API enforces every rule; this screen explains it in plain words.
 */
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActivityIndicator, Alert, Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import type { DecisionResult, NearbyReport, Report } from '@/api/types';
import { verificationApi } from '@/api/verification';
import { AuthImage } from '@/components/AuthImage';
import { DecisionPanel } from '@/components/DecisionPanel';
import { Message } from '@/components/Message';
import { Screen } from '@/components/Screen';
import { StatusBadge } from '@/components/StatusBadge';
import { classifyDecisionError, type ReasonAction } from '@/review/decision';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';
import { formatCoords, formatDateTime } from '@/utils/format';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      {typeof children === 'string' ? <Text style={styles.value}>{children}</Text> : children}
    </View>
  );
}

function osmUrl(lat: number, lng: number) {
  return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lng}#map=18/${lat}/${lng}`;
}

export default function ReviewReport() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const [report, setReport] = useState<Report | null>(null);
  const [nearby, setNearby] = useState<NearbyReport[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<DecisionResult | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setReport(await verificationApi.get(id));
      verificationApi
        .nearby(id)
        .then(setNearby)
        .catch(() => setNearby([]));
    } catch (e) {
      setError(userMessage(e, t));
    }
  }, [id, t]);

  useEffect(() => {
    load();
  }, [load]);

  async function run(action: () => Promise<DecisionResult>) {
    setBusy(true);
    setError(null);
    try {
      const result = await action();
      setDone(result);
      setReport(result.report);
    } catch (e) {
      const kind = classifyDecisionError(e);
      setError(kind === 'offline' ? t('review.offlineDecision') : userMessage(e, t));
      if (kind === 'conflict' || kind === 'forbidden') load(); // show the current state
    } finally {
      setBusy(false);
    }
  }

  function confirm() {
    Alert.alert(t('review.confirmTitle'), t('review.confirmText'), [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('review.confirm'), onPress: () => run(() => verificationApi.verify(id)) },
    ]);
  }

  function withReason(action: ReasonAction, reason: string) {
    run(() =>
      action === 'reject' ? verificationApi.reject(id, reason) : verificationApi.flag(id, reason),
    );
  }

  if (!report) {
    return (
      <Screen>
        {error ? <Message text={error} /> : <ActivityIndicator size="large" color={colors.primary} />}
      </Screen>
    );
  }

  return (
    <Screen>
      <AuthImage path={report.photo_url} style={styles.photo} label={t(`categories.${report.category}`)} />
      <View style={styles.titleRow}>
        <Text style={styles.title}>{t(`categories.${report.category}`)}</Text>
        <StatusBadge status={report.status} />
      </View>
      {report.status === 'FLAGGED' && report.decision_reason ? (
        <Message tone="info" text={`${t('review.flagReason')}: ${report.decision_reason}`} />
      ) : null}
      <Field label={t('detail.reportedAt')}>{formatDateTime(report.captured_at, i18n.language)}</Field>
      <Field label={t('detail.location')}>
        <Text style={styles.value}>{formatCoords(report.latitude, report.longitude)}</Text>
        <Pressable
          accessibilityRole="link"
          onPress={() => Linking.openURL(osmUrl(report.latitude, report.longitude))}
          style={styles.mapLink}
        >
          <Ionicons name="map" size={18} color={colors.primary} />
          <Text style={styles.link}>{t('review.openMap')}</Text>
        </Pressable>
      </Field>
      {report.description ? <Field label={t('detail.description')}>{report.description}</Field> : null}

      <Field label={t('review.nearbyTitle')}>
        {nearby === null ? (
          <ActivityIndicator color={colors.primary} />
        ) : nearby.length === 0 ? (
          <Text style={styles.muted}>{t('review.nearbyNone')}</Text>
        ) : (
          nearby.map((n) => (
            <Pressable
              key={n.report.id}
              accessibilityRole="button"
              onPress={() => router.push(`/review/${n.report.id}`)}
              style={styles.nearby}
            >
              <AuthImage path={n.report.photo_url} style={styles.nearbyThumb} />
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={styles.value}>{t(`categories.${n.report.category}`)}</Text>
                <Text style={styles.muted}>
                  {t('review.nearbyItem', {
                    distance: Math.round(n.distance_m),
                    date: formatDateTime(n.report.captured_at, i18n.language),
                  })}
                </Text>
              </View>
              <StatusBadge status={n.report.status} />
            </Pressable>
          ))
        )}
      </Field>

      <Message text={error} />

      {done ? (
        <View style={styles.done} accessibilityRole="summary">
          <Ionicons name="checkmark-circle" size={28} color={colors.success} />
          <View style={{ flex: 1, gap: 4 }}>
            <Text style={styles.doneTitle}>{t(`review.decided.${done.verification.decision}`)}</Text>
            {done.verification.decision === 'VERIFIED' ? (
              <Text style={styles.value}>
                {done.payout_requested ? t('review.payoutRequested') : t('review.payoutSkipped')}
              </Text>
            ) : null}
          </View>
        </View>
      ) : report.can_decide ? (
        <DecisionPanel busy={busy} onConfirm={confirm} onReason={withReason} />
      ) : report.cannot_decide_reason ? (
        <Message tone="info" text={t(`review.cannotDecide.${report.cannot_decide_reason}`)} />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  photo: { width: '100%', aspectRatio: 4 / 3, borderRadius: radius.md },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm },
  title: { flex: 1, fontSize: font.title, fontWeight: '800', color: colors.text },
  field: { gap: 4 },
  label: { fontSize: font.small, fontWeight: '700', color: colors.textMuted, textTransform: 'uppercase' },
  value: { fontSize: font.body, color: colors.text },
  muted: { fontSize: font.small, color: colors.textMuted },
  mapLink: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs, minHeight: 44 },
  link: { fontSize: font.body, color: colors.primary, fontWeight: '600' },
  nearby: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    padding: spacing.sm,
    borderRadius: radius.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  nearbyThumb: { width: 48, height: 48, borderRadius: radius.sm },
  done: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.successSoft,
  },
  doneTitle: { fontSize: font.large, fontWeight: '700', color: colors.success },
});
