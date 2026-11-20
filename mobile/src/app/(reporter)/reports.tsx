/**
 * My reports: reports still on this phone (waiting to send) and reports the
 * server has, with their verification and payout status. The last list from
 * the server is cached so it can still be seen offline.
 */
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, RefreshControl, SectionList, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { reportsApi } from '@/api/reports';
import type { Report } from '@/api/types';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { CATEGORY_ICONS } from '@/components/CategoryPicker';
import { Message } from '@/components/Message';
import { OfflineBanner } from '@/components/OfflineBanner';
import { type DisplayStatus, StatusBadge } from '@/components/StatusBadge';
import { cacheGet, cacheSet } from '@/offline/sqliteQueueStore';
import { useSync } from '@/offline/SyncContext';
import type { QueuedReport } from '@/offline/types';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';
import { formatDateTime } from '@/utils/format';

const PAGE = 20;

type Row =
  | { kind: 'local'; item: QueuedReport }
  | { kind: 'server'; item: Report };

export default function MyReports() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { queue, db, isOnline } = useSync();
  const [reports, setReports] = useState<Report[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const cacheKey = `my-reports:${user?.id}`;

  const load = useCallback(
    async (offset = 0) => {
      setLoading(true);
      setError(null);
      try {
        const page = await reportsApi.myReports(PAGE, offset);
        const merged = offset === 0 ? page.items : [...reports, ...page.items];
        setReports(merged);
        setTotal(page.total);
        setFromCache(false);
        if (db && offset === 0) await cacheSet(db, cacheKey, page);
      } catch (e) {
        const cached =
          db && offset === 0 ? await cacheGet<{ items: Report[]; total: number }>(db, cacheKey) : null;
        if (cached) {
          setReports(cached.items);
          setTotal(cached.total);
          setFromCache(true);
        } else {
          setError(userMessage(e, t));
        }
      } finally {
        setLoading(false);
      }
    },
    [db, cacheKey, reports, t],
  );

  // Reload whenever the tab is opened or the queue changes (a report was sent)
  useFocusEffect(
    useCallback(() => {
      load(0);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [db, queue.length]),
  );

  const sections = [
    ...(queue.length
      ? [{ title: t('reports.onThisPhone'), data: queue.map((item) => ({ kind: 'local', item }) as Row) }]
      : []),
    ...(reports.length
      ? [{ title: t('reports.sent'), data: reports.map((item) => ({ kind: 'server', item }) as Row) }]
      : []),
  ];

  return (
    <SafeAreaView style={styles.safe} edges={['left', 'right']}>
      <OfflineBanner />
      <SectionList
        sections={sections}
        keyExtractor={(row) => (row.kind === 'local' ? `l-${row.item.clientReportId}` : `s-${row.item.id}`)}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={() => load(0)} />}
        ListHeaderComponent={
          <View style={{ gap: spacing.sm }}>
            {fromCache || (!isOnline && reports.length > 0) ? (
              <Message tone="info" text={t('reports.showingSaved')} />
            ) : null}
            <Message text={error ? `${t('reports.loadFailed')} ${error}` : null} />
          </View>
        }
        ListEmptyComponent={
          loading ? undefined : (
            <View style={styles.empty}>
              <Ionicons name="document-text" size={40} color={colors.textMuted} />
              <Text style={styles.emptyText}>{t('reports.empty')}</Text>
            </View>
          )
        }
        renderSectionHeader={({ section }) => <Text style={styles.sectionTitle}>{section.title}</Text>}
        renderItem={({ item: row }) => {
          const category = row.item.category;
          const status: DisplayStatus = row.kind === 'local' ? row.item.state : row.item.status;
          const date = row.kind === 'local' ? row.item.capturedAt : row.item.captured_at;
          const href =
            row.kind === 'local'
              ? `/report/${row.item.clientReportId}?local=1`
              : `/report/${row.item.id}`;
          return (
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push(href as never)}
              style={({ pressed }) => [styles.card, pressed && { opacity: 0.85 }]}
            >
              <Ionicons name={CATEGORY_ICONS[category]} size={28} color={colors.primary} />
              <View style={styles.cardBody}>
                <Text style={styles.cardTitle}>{t(`categories.${category}`)}</Text>
                <Text style={styles.cardMeta}>
                  {t('reports.reported', { date: formatDateTime(date, i18n.language) })}
                </Text>
                <StatusBadge status={status} />
                {row.kind === 'server' && row.item.payout ? (
                  <Text style={styles.cardMeta}>
                    {t('detail.payout')}: {row.item.payout.currency} {row.item.payout.amount}
                    {row.item.payout.is_test_payment ? ' (TEST)' : ''}
                  </Text>
                ) : null}
              </View>
              <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
            </Pressable>
          );
        }}
        ListFooterComponent={
          reports.length < total && !fromCache ? (
            <Button
              title={t('reports.loadMore')}
              variant="secondary"
              loading={loading}
              onPress={() => load(reports.length)}
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
  sectionTitle: {
    fontSize: font.small,
    fontWeight: '700',
    color: colors.textMuted,
    textTransform: 'uppercase',
    marginTop: spacing.sm,
  },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardBody: { flex: 1, gap: 4 },
  cardTitle: { fontSize: font.large, fontWeight: '700', color: colors.text },
  cardMeta: { fontSize: font.small, color: colors.textMuted },
  empty: { alignItems: 'center', gap: spacing.sm, padding: spacing.xl },
  emptyText: { fontSize: font.body, color: colors.textMuted, textAlign: 'center' },
});
