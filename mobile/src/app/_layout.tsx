/**
 * Root layout: providers and the screen stack.
 *
 *   AuthProvider  - who is logged in (works offline from the cached profile)
 *   SyncProvider  - the offline queue and automatic syncing
 *   InboxProvider - unread count, push registration, opening tapped notifications
 */
import { Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from '@/auth/AuthContext';
import { API_URL } from '@/config';
import '@/i18n';
import { restoreLanguage } from '@/i18n';
import { InboxProvider } from '@/notifications/InboxContext';
import { SyncProvider } from '@/offline/SyncContext';
import { colors } from '@/theme';

export default function RootLayout() {
  const [languageReady, setLanguageReady] = useState(false);
  useEffect(() => {
    restoreLanguage().finally(() => setLanguageReady(true));
    // Wake the server early: free hosting sleeps when idle and takes up to a
    // minute to start. Ignored if offline; nothing depends on the answer.
    fetch(`${API_URL}/health`).catch(() => undefined);
  }, []);
  if (!languageReady) return null;

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <SyncProvider>
          <InboxProvider>
            <AppStack />
          </InboxProvider>
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
      <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      <Stack.Screen name="new-report" options={{ title: t('newReport.title') }} />
      <Stack.Screen
        name="submitted"
        options={{ headerShown: false, gestureEnabled: false }}
      />
      <Stack.Screen name="report/[id]" options={{ title: t('detail.title') }} />
      <Stack.Screen name="review/[id]" options={{ title: t('review.detailTitle') }} />
      <Stack.Screen name="other-roles" options={{ title: t('otherRoles.title') }} />
    </Stack>
  );
}
