/** Welcome / onboarding screen. */
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button } from '@/components/Button';
import { LanguageToggle } from '@/components/LanguageToggle';
import { colors, font, spacing } from '@/theme';

const POINTS: { key: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { key: 'welcome.point1', icon: 'camera' },
  { key: 'welcome.point2', icon: 'shield-checkmark' },
  { key: 'welcome.point3', icon: 'cash' },
];

export default function Welcome() {
  const { t } = useTranslation();
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <LanguageToggle />
        <View style={styles.hero}>
          <Ionicons name="leaf" size={56} color={colors.primary} />
          <Text style={styles.title}>{t('common.appName')}</Text>
          <Text style={styles.tagline}>{t('welcome.tagline')}</Text>
        </View>
        <View style={styles.points}>
          {POINTS.map(({ key, icon }) => (
            <View key={key} style={styles.point}>
              <Ionicons name={icon} size={26} color={colors.primary} />
              <Text style={styles.pointText}>{t(key)}</Text>
            </View>
          ))}
        </View>
        <View style={styles.actions}>
          <Button title={t('welcome.register')} onPress={() => router.push('/register')} />
          <Button
            title={t('welcome.login')}
            variant="secondary"
            onPress={() => router.push('/login')}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  container: { flex: 1, padding: spacing.lg, justifyContent: 'space-between' },
  hero: { alignItems: 'center', gap: spacing.sm, marginTop: spacing.lg },
  title: { fontSize: font.hero, fontWeight: '800', color: colors.primaryDark },
  tagline: { fontSize: font.large, color: colors.text, textAlign: 'center' },
  points: { gap: spacing.md },
  point: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
  pointText: { flex: 1, fontSize: font.body, color: colors.text, lineHeight: 22 },
  actions: { gap: spacing.sm },
});
