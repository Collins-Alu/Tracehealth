/** A horizontal row of selectable chips (zone filter, quick reasons, tabs). */
import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text } from 'react-native';

import { colors, font, radius, spacing } from '@/theme';

export interface Chip<T> {
  value: T;
  label: string;
}

interface Props<T> {
  chips: Chip<T>[];
  selected: T | null;
  onSelect: (value: T) => void;
  testIDPrefix?: string;
  wrap?: boolean;
}

export function ChipRow<T>({ chips, selected, onSelect, testIDPrefix, wrap }: Props<T>) {
  const content = chips.map((chip, i) => {
    const isSelected = chip.value === selected;
    return (
      <Pressable
        key={`${String(chip.value)}-${i}`}
        testID={testIDPrefix ? `${testIDPrefix}-${String(chip.value)}` : undefined}
        accessibilityRole="button"
        accessibilityState={{ selected: isSelected }}
        onPress={() => onSelect(chip.value)}
        style={[styles.chip, isSelected && styles.selected]}
      >
        <Text style={[styles.text, isSelected && styles.selectedText]}>{chip.label}</Text>
      </Pressable>
    );
  });
  if (wrap) return <>{content}</>;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      {content}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: spacing.sm, paddingVertical: spacing.xs },
  chip: {
    minHeight: 40,
    justifyContent: 'center',
    paddingHorizontal: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1.5,
    borderColor: colors.primary,
    backgroundColor: colors.surface,
  },
  selected: { backgroundColor: colors.primary },
  text: { color: colors.primary, fontSize: font.body, fontWeight: '600' },
  selectedText: { color: '#FFFFFF' },
});
