/** In-app inbox: works everywhere, including Expo Go where push is unavailable. */
import { Ionicons } from '@expo/vector-icons';
import { router, useFocusEffect } from 'expo-router';
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { notificationsApi } from '@/api/notifications';
import type { AppNotification } from '@/api/types';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/Button';
import { Message } from '@/components/Message';
import { OfflineBanner } from '@/components/OfflineBanner';
import { useInbox } from '@/notifications/InboxContext';
import { notificationTarget } from '@/notifications/routing';
import { colors, font, radius, spacing } from '@/theme';
import { userMessage } from '@/utils/errors';
import { formatDateTime } from '@/utils/format';

const PAGE = 30;

export default function Inbox() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const { refreshUnread } = useInbox();
  const [items, setItems] = useState<AppNotification[]>([]);
  const [total, setTotal] = useState(0);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (offset = 0) => {
      setLoading(true);
      setError(null);
      try {
        const page = await notificationsApi.list(PAGE, offset);
        setItems((prev) => (offset === 0 ? page.items : [...prev, ...page.items]));
        setTotal(page.total);
        setUnread(page.unread);
      } catch (e) {
        setError(`${t('inbox.loadFailed')} ${userMessage(e, t)}`);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useFocusEffect(
    useCallback(() => {
      load(0);
    }, [load]),
  );

  async function open(n: AppNotification) {
    if (!n.read_at) {
      notificationsApi
        .markRead(n.id)
        .then(refreshUnread)
        .catch(() => undefined);
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)));
      setUnread((u) => Math.max(0, u - 1));
    }
    const href = notificationTarget(n.type, n.related_report_id, user?.roles ?? []);
    if (href) router.push(href as never);
  }

  async function markAll() {
    try {
      await notificationsApi.markAllRead();
      await load(0);
      await refreshUnread();
    } catch (e) {
      setError(userMessage(e, t));
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={['left', 'right']}>
      <OfflineBanner />
      <FlatList
        data={items}
        keyExtractor={(n) => n.id}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={() => load(0)} />}
        ListHeaderComponent={
          <View style={{ gap: spacing.sm }}>
            <Message text={error} />
            {unread > 0 ? (
              <Button title={t('inbox.markAllRead')} variant="ghost" icon="checkmark-done" onPress={markAll} />
            ) : null}
          </View>
        }
        ListEmptyComponent={
          loading || error ? undefined : (
            <View style={styles.empty}>
              <Ionicons name="notifications-off" size={40} color={colors.textMuted} />
              <Text style={styles.emptyText}>{t('inbox.empty')}</Text>
            </View>
          )
        }
        renderItem={({ item }) => (
          <Pressable
            accessibilityRole="button"
            accessibilityHint={item.read_at ? undefined : t('inbox.unread')}
            onPress={() => open(item)}
            style={({ pressed }) => [styles.card, !item.read_at && styles.unread, pressed && { opacity: 0.85 }]}
          >
            {!item.read_at ? <View style={styles.dot} /> : null}
            <View style={{ flex: 1, gap: 4 }}>
              <Text style={[styles.title, !item.read_at && styles.bold]}>{item.title}</Text>
              <Text style={styles.body}>{item.body}</Text>
              <Text style={styles.meta}>{formatDateTime(item.created_at, i18n.language)}</Text>
            </View>
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
  card: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  unread: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary, marginTop: 6 },
  title: { fontSize: font.large, color: colors.text },
  bold: { fontWeight: '700' },
  body: { fontSize: font.body, color: colors.text, lineHeight: 22 },
  meta: { fontSize: font.small, color: colors.textMuted },
  empty: { alignItems: 'center', gap: spacing.sm, padding: spacing.xl },
  emptyText: { fontSize: font.body, color: colors.textMuted, textAlign: 'center' },
});
