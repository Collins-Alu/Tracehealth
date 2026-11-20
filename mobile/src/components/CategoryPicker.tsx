import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { POLLUTION_CATEGORIES, type PollutionCategory } from '@/api/types';
import { colors, font, radius, spacing } from '@/theme';

export const CATEGORY_ICONS: Record<PollutionCategory, keyof typeof Ionicons.glyphMap> = {
  OPEN_BURNING: 'flame',
  ILLEGAL_DUMPING: 'trash',
  BLOCKED_DRAINAGE: 'water',
  MEDICAL_WASTE: 'medkit',
  OTHER: 'alert-circle',
};

interface Props {
  value: PollutionCategory | null;
  onChange: (category: PollutionCategory) => void;
}

/** Large, icon-led choices that work for users with varying literacy (SRS 3.1). */
export function CategoryPicker({ value, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <View style={styles.grid} accessibilityRole="radiogroup">
      {POLLUTION_CATEGORIES.map((category) => {
        const selected = value === category;
        return (
          <Pressable
            key={category}
            testID={`category-${category}`}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            accessibilityLabel={t(`categories.${category}`)}
            onPress={() => onChange(category)}
            style={[styles.option, selected && styles.selected]}
          >
            <Ionicons
              name={CATEGORY_ICONS[category]}
              size={32}
              color={selected ? '#FFFFFF' : colors.primary}
            />
            <Text style={[styles.label, selected && styles.selectedLabel]}>
              {t(`categories.${category}`)}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  option: {
    flexBasis: '47%',
    flexGrow: 1,
    minHeight: 96,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    padding: spacing.sm,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  selected: { backgroundColor: colors.primary, borderColor: colors.primary },
  label: { fontSize: font.body, fontWeight: '600', color: colors.text, textAlign: 'center' },
  selectedLabel: { color: '#FFFFFF' },
});
