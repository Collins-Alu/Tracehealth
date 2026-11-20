/**
 * Bottom tabs, shown according to the user's roles:
 *   Reporter  Home · My reports · Inbox · Account
 *   Verifier  Review · Inbox · Account
 *   Both      all five
 * Accounts with neither role (agency staff, administrators) use the web
 * dashboard and are sent to /other-roles.
 */
import { Ionicons } from '@expo/vector-icons';
import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import React from 'react';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthContext';
import { useInbox } from '@/notifications/InboxContext';
import { colors } from '@/theme';

type IconName = keyof typeof Ionicons.glyphMap;

function icon(name: IconName) {
  return ({ color, size }: { color: unknown; size: number }) => (
    <Ionicons name={name} color={String(color)} size={size} />
  );
}

export default function TabsLayout() {
  const { t } = useTranslation();
  const { user, status } = useAuth();
  const { unread } = useInbox();
  const roles = user?.roles ?? [];
  const isReporter = roles.includes('REPORTER');
  const isVerifier = roles.includes('VERIFIER');

  if (status !== 'loading' && !isReporter && !isVerifier) return <Redirect href="/" />;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontSize: 12, fontWeight: '600' },
        headerTintColor: colors.primary,
        headerTitleStyle: { color: colors.text },
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: t('common.appName'),
          tabBarLabel: t('tabs.home'),
          tabBarIcon: icon('home'),
          href: isReporter ? undefined : null,
        }}
      />
      <Tabs.Screen
        name="reports"
        options={{
          title: t('reports.title'),
          tabBarLabel: t('tabs.reports'),
          tabBarIcon: icon('list'),
          href: isReporter ? undefined : null,
        }}
      />
      <Tabs.Screen
        name="review"
        options={{
          title: t('review.title'),
          tabBarLabel: t('tabs.review'),
          tabBarIcon: icon('shield-checkmark'),
          href: isVerifier ? undefined : null,
        }}
      />
      <Tabs.Screen
        name="inbox"
        options={{
          title: t('inbox.title'),
          tabBarLabel: t('tabs.inbox'),
          tabBarIcon: icon('notifications'),
          tabBarBadge: unread > 0 ? (unread > 99 ? '99+' : unread) : undefined,
        }}
      />
      <Tabs.Screen
        name="account"
        options={{
          title: t('account.title'),
          tabBarLabel: t('tabs.account'),
          tabBarIcon: icon('person-circle'),
        }}
      />
    </Tabs>
  );
}
