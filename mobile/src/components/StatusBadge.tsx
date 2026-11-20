import React from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import type { ReportStatus } from '@/api/types';
import type { QueueState } from '@/offline/types';
import { colors, font, radius, spacing } from '@/theme';

export type DisplayStatus = ReportStatus | QueueState;

const STYLE: Record<DisplayStatus, { fg: string; bg: string }> = {
  PENDING: { fg: colors.warning, bg: colors.warningSoft },
  VERIFIED: { fg: colors.success, bg: colors.successSoft },
  REJECTED: { fg: colors.danger, bg: colors.dangerSoft },
  FLAGGED: { fg: colors.flagged, bg: colors.flaggedSoft },
  QUEUED: { fg: colors.queued, bg: colors.queuedSoft },
  SYNCING: { fg: colors.queued, bg: colors.queuedSoft },
  NEEDS_ATTENTION: { fg: colors.danger, bg: colors.dangerSoft },
};

export function StatusBadge({ status }: { status: DisplayStatus }) {
  const { t } = useTranslation();
  const s = STYLE[status];
  return (
    <View style={[styles.badge, { backgroundColor: s.bg }]}>
      <Text style={[styles.text, { color: s.fg }]}>{t(`status.${status}`)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radius.sm,
  },
  text: { fontSize: font.small, fontWeight: '700' },
});
