/** Entry point: sends the user to the right place for their login state and role. */
import { Redirect } from 'expo-router';
import React from 'react';
import { ActivityIndicator, View } from 'react-native';

import { useAuth } from '@/auth/AuthContext';
import { colors } from '@/theme';

export default function Index() {
  const { status, user } = useAuth();
  if (status === 'loading') {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }
  if (!user) return <Redirect href="/welcome" />;
  if (user.roles.includes('REPORTER')) return <Redirect href="/home" />;
  if (user.roles.includes('VERIFIER')) return <Redirect href="/review" />;
  return <Redirect href="/other-roles" />;
}
