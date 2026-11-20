import { Ionicons } from '@expo/vector-icons';
import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import React from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthContext';
import { colors } from '@/theme';

/** Reporter area. Anyone not logged in as a reporter is sent back to the start. */
export default function ReporterLayout() {
  const { t } = useTranslation();
  const { user, status } = useAuth();
  if (status !== 'loading' && !user?.roles.includes('REPORTER')) return <Redirect href="/" />;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 13, fontWeight: '600' },
        headerTintColor: colors.primary,
        headerTitleStyle: { color: colors.text },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: t('common.appName'),
          tabBarLabel: t('home.newReport'),
          tabBarIcon: ({ color, size }) => <Ionicons name="home" color={String(color)} size={size} />,
        }}
      />
      <Tabs.Screen
        name="reports"
        options={{
          title: t('reports.title'),
          tabBarLabel: t('home.myReports'),
          tabBarIcon: ({ color, size }) => <Ionicons name="list" color={String(color)} size={size} />,
        }}
      />
    </Tabs>
  );
}
