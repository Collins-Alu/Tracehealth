import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, font, radius, spacing, TOUCH_TARGET } from '@/theme';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface Props {
  title: string;
  onPress: () => void;
  variant?: Variant;
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  disabled?: boolean;
  testID?: string;
}

export function Button({ title, onPress, variant = 'primary', icon, loading, disabled, testID }: Props) {
  const inactive = disabled || loading;
  const palette = PALETTES[variant];
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      accessibilityLabel={title}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor: palette.bg, borderColor: palette.border },
        pressed && !inactive && { opacity: 0.85 },
        inactive && styles.inactive,
      ]}
    >
      <View style={styles.row}>
        {loading ? (
          <ActivityIndicator color={palette.fg} />
        ) : icon ? (
          <Ionicons name={icon} size={22} color={palette.fg} />
        ) : null}
        <Text style={[styles.text, { color: palette.fg }]}>{title}</Text>
      </View>
    </Pressable>
  );
}

const PALETTES: Record<Variant, { bg: string; fg: string; border: string }> = {
  primary: { bg: colors.primary, fg: '#FFFFFF', border: colors.primary },
  secondary: { bg: colors.surface, fg: colors.primary, border: colors.primary },
  danger: { bg: colors.surface, fg: colors.danger, border: colors.danger },
  ghost: { bg: 'transparent', fg: colors.primary, border: 'transparent' },
};

const styles = StyleSheet.create({
  base: {
    minHeight: TOUCH_TARGET + 4,
    borderRadius: radius.md,
    borderWidth: 1.5,
    paddingHorizontal: spacing.md,
    justifyContent: 'center',
  },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  text: { fontSize: font.large, fontWeight: '600' },
  inactive: { opacity: 0.5 },
});
