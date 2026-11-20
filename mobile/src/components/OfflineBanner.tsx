import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { useOptionalSync } from '@/offline/useOptionalSync';
import { colors, font, spacing } from '@/theme';

export function OfflineBanner() {
  const { t } = useTranslation();
  const sync = useOptionalSync();
  if (!sync || sync.isOnline) return null;
  return (
    <View style={styles.banner} accessibilityRole="alert">
      <Ionicons name="cloud-offline" size={18} color={colors.queued} />
      <Text style={styles.text}>{t('common.offline')}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.queuedSoft,
  },
  text: { color: colors.queued, fontSize: font.small, fontWeight: '600' },
});
