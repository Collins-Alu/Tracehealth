import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';

import { colors, font, radius, spacing } from '@/theme';

/** SRS 5.2: reporters must never be encouraged to approach a hazard. */
export function SafetyNotice() {
  const { t } = useTranslation();
  return (
    <View style={styles.box} accessibilityRole="summary" testID="safety-notice">
      <Ionicons name="warning" size={24} color={colors.warning} />
      <View style={styles.textWrap}>
        <Text style={styles.title}>{t('safety.title')}</Text>
        <Text style={styles.text}>{t('safety.text')}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.warningSoft,
    borderWidth: 1,
    borderColor: '#F0D49B',
  },
  textWrap: { flex: 1, gap: 2 },
  title: { fontSize: font.body, fontWeight: '700', color: colors.warning },
  text: { fontSize: font.body, color: colors.text, lineHeight: 22 },
});
