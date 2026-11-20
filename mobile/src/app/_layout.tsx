/**
 * Root layout: providers and the screen stack.
 *
 *   AuthProvider  - who is logged in (works offline from the cached profile)
 *   SyncProvider  - the offline queue and automatic syncing
 */
import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/auth/AuthContext';
import '@/i18n';
import { restoreLanguage } from '@/i18n';
import { SyncProvider } from '@/offline/SyncContext';
import { colors } from '@/theme';

export default function RootLayout() {
  const [languageReady, setLanguageReady] = useState(false);
  useEffect(() => {
    restoreLanguage().finally(() => setLanguageReady(true));
  }, []);
  if (!languageReady) return null;

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <SyncProvider>
          <AppStack />
        </SyncProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}

function AppStack() {
  const { t } = useTranslation();
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: colors.surface },
        headerTintColor: colors.primary,
        headerTitleStyle: { color: colors.text },
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen name="welcome" options={{ headerShown: false }} />
      <Stack.Screen name="login" options={{ title: t('auth.loginTitle') }} />
      <Stack.Screen name="register" options={{ title: t('auth.registerTitle') }} />
      <Stack.Screen name="(reporter)" options={{ headerShown: false }} />
      <Stack.Screen name="new-report" options={{ title: t('newReport.title') }} />
      <Stack.Screen
        name="submitted"
        options={{ headerShown: false, gestureEnabled: false }}
      />
      <Stack.Screen name="report/[id]" options={{ title: t('detail.title') }} />
      <Stack.Screen name="verifier" options={{ title: t('verifier.title') }} />
    </Stack>
  );
}
