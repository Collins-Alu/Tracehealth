/**
 * Verifier dashboard (UML B.4 steps 1-2: getPendingReports(zone)).
 *
 *   Pending  reports waiting for a first decision, oldest first
 *   Flagged  reports another verifier flagged; they need a second verifier
 *
 * Zone filter: My zone (+ unassigned) · All zones · each zone.
 * Reviewing needs a connection; decisions are never queued offline, so two
 * verifiers can't unknowingly decide the same report.
 */
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { Report, Zone } from '@/api/types';
import { verificationApi, type ZoneFilter } from '@/api/verification';
import { useAuth } from '@/auth/AuthContext';
import { AuthImage } from '@/components/AuthImage';
import { Button } from '@/components/Button';
import { type Chip, ChipRow } from '@/components/ChipRow';
import { Message } from '@/components/Message';
import { OfflineBanner } from '@/components/OfflineBanner';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';
import { formatDateTime } from '@/utils/format';

const PAGE = 20;
type Queue = 'pending' | 'flagged';
/** '' stands for "my zone" (no zone parameter) */
type ZoneChoice = '' | string;

export default function Review() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [queue, setQueue] = useState<Queue>('pending');
  const [zone, setZone] = useState<ZoneChoice>(user?.assigned_zone ? '' : 'ALL');
  const [zones, setZones] = useState<Zone[]>([]);
  const [items, setItems] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    verificationApi.zones().then(setZones).catch(() => undefined);
  }, []);

  const load = useCallback(
    async (offset = 0) => {
      setLoading(true);
      setError(null);
      const zoneParam: ZoneFilter = zone === '' ? undefined : zone;
      try {
        const page =
          queue === 'pending'
            ? await verificationApi.pending(zoneParam, PAGE, offset)
            : await verificationApi.flagged(zoneParam, PAGE, offset);
        setItems((prev) => (offset === 0 ? page.items : [...prev, ...page.items]));
        setTotal(page.total);
      } catch (e) {
        setError(userMessage(e, t));
        if (offset === 0) setItems([]);
      } finally {
        setLoading(false);
      }
    },
    [queue, zone, t],
  );

  // Reload when the tab is shown (e.g. after deciding) or the filters change
  useFocusEffect(
    useCallback(() => {
      load(0);
    }, [load]),
  );

  const zoneChips: Chip<ZoneChoice>[] = [
    ...(user?.assigned_zone ? [{ value: '', label: t('review.myZone') }] : []),
    { value: 'ALL', label: t('review.allZones') },
    ...zones.map((z) => ({ value: z.code, label: z.name })),
    { value: 'UNASSIGNED', label: t('review.unassigned') },
  ];
  const zoneName = (code: string | null) =>
    code ? (zones.find((z) => z.code === code)?.name ?? code) : t('review.unassigned');

  return (
    <SafeAreaView style={styles.safe} edges={['left', 'right']}>
      <OfflineBanner />
      <FlatList
        data={items}
        keyExtractor={(r) => r.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={() => load(0)} />}
        ListHeaderComponent={
          <View style={styles.header}>
            <ChipRow<Queue>
              chips={[
                { value: 'pending', label: t('review.pending') },
                { value: 'flagged', label: t('review.flagged') },
              ]}
              selected={queue}
              onSelect={setQueue}
              testIDPrefix="queue"
            />
            <ChipRow<ZoneChoice> chips={zoneChips} selected={zone} onSelect={setZone} testIDPrefix="zone" />
            <Text style={styles.count}>{t('review.count', { count: total })}</Text>
            <Message text={error} />
          </View>
        }
        ListEmptyComponent={
          loading || error ? undefined : (
            <View style={styles.empty}>
              <Ionicons name="checkmark-done-circle" size={44} color={colors.success} />
              <Text style={styles.emptyText}>
                {queue === 'pending' ? t('review.empty') : t('review.emptyFlagged')}
              </Text>
            </View>
          )
        }
        renderItem={({ item }) => (
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push(`/review/${item.id}`)}
            style={({ pressed }) => [styles.card, pressed && { opacity: 0.85 }]}
          >
            <AuthImage path={item.photo_url} style={styles.thumb} />
            <View style={styles.cardBody}>
              <Text style={styles.cardTitle}>{t(`categories.${item.category}`)}</Text>
              <Text style={styles.meta}>
                {zoneName(item.zone_code)} · {formatDateTime(item.captured_at, i18n.language)}
              </Text>
              {item.status === 'FLAGGED' && item.decision_reason ? (
                <Text style={styles.flagReason} numberOfLines={2}>
                  {t('review.flagReason')}: {item.decision_reason}
                </Text>
              ) : null}
              {!item.can_decide && item.cannot_decide_reason ? (
                <Text style={styles.cannot}>{t(`review.cannotDecide.${item.cannot_decide_reason}`)}</Text>
              ) : null}
            </View>
            <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
          </Pressable>
        )}
        ListFooterComponent={
          items.length < total ? (
            <Button
              title={t('reports.loadMore')}
              variant="secondary"
              loading={loading}
              onPress={() => load(items.length)}
            />
          ) : undefined
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  list: { padding: spacing.md, gap: spacing.sm },
  header: { gap: spacing.sm, marginBottom: spacing.xs },
  count: { fontSize: font.small, color: colors.textMuted, fontWeight: '600' },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.sm,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  thumb: { width: 72, height: 72, borderRadius: radius.sm },
  cardBody: { flex: 1, gap: 2 },
  cardTitle: { fontSize: font.large, fontWeight: '700', color: colors.text },
  meta: { fontSize: font.small, color: colors.textMuted },
  flagReason: { fontSize: font.small, color: colors.flagged },
  cannot: { fontSize: font.small, color: colors.warning, fontWeight: '600' },
  empty: { alignItems: 'center', gap: spacing.sm, padding: spacing.xl },
  emptyText: { fontSize: font.body, color: colors.textMuted, textAlign: 'center' },
});
