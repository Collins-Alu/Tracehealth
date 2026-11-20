/** Submission confirmation (UML B.3 output): sent, or safely queued. */
import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/Button';
import { colors, font, spacing } from '@/theme';

export default function Submitted() {
  const { t } = useTranslation();
  const { result } = useLocalSearchParams<{ result?: string }>();
  const sent = result === 'sent';
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.body} accessibilityRole="summary">
        <Ionicons
          name={sent ? 'checkmark-circle' : 'cloud-offline'}
          size={88}
          color={sent ? colors.success : colors.queued}
        />
        <Text style={styles.title}>{sent ? t('submitted.sentTitle') : t('submitted.queuedTitle')}</Text>
        <Text style={styles.text}>{sent ? t('submitted.sentText') : t('submitted.queuedText')}</Text>
      </View>
      <View style={styles.actions}>
        <Button title={t('submitted.viewReports')} onPress={() => router.replace('/reports')} />
        <Button
          title={t('submitted.home')}
          variant="secondary"
          onPress={() => router.replace('/home')}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background, padding: spacing.lg },
  body: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md },
  title: { fontSize: font.hero, fontWeight: '800', color: colors.text, textAlign: 'center' },
  text: { fontSize: font.large, color: colors.text, textAlign: 'center', lineHeight: 26 },
  actions: { gap: spacing.sm },
});
