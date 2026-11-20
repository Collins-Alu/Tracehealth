import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, font, radius, spacing } from '@/theme';

/** An inline message: error (red) or info (teal). Announced by screen readers. */
export function Message({ text, tone = 'error' }: { text: string | null; tone?: 'error' | 'info' }) {
  if (!text) return null;
  const palette =
    tone === 'error'
      ? { fg: colors.danger, bg: colors.dangerSoft }
      : { fg: colors.primaryDark, bg: colors.primarySoft };
  return (
    <View
      style={[styles.box, { backgroundColor: palette.bg }]}
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
    >
      <Text style={[styles.text, { color: palette.fg }]}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: { padding: spacing.md, borderRadius: radius.sm },
  text: { fontSize: font.body, lineHeight: 22 },
});
