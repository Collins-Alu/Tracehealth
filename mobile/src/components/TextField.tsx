import React from 'react';
import { StyleSheet, Text, TextInput, type TextInputProps, View } from 'react-native';

import { colors, font, radius, spacing, TOUCH_TARGET } from '@/theme';

interface Props extends TextInputProps {
  label: string;
  hint?: string;
}

export function TextField({ label, hint, style, ...rest }: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={label}
        accessibilityHint={hint}
        placeholderTextColor={colors.textMuted}
        style={[styles.input, rest.multiline && styles.multiline, style]}
        {...rest}
      />
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xs },
  label: { fontSize: font.body, fontWeight: '600', color: colors.text },
  input: {
    minHeight: TOUCH_TARGET,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: font.body,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  multiline: { minHeight: 100, textAlignVertical: 'top' },
  hint: { fontSize: font.small, color: colors.textMuted },
});
