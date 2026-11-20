/** A report photo loaded from the API with the login token (photos are never public). */
import React from 'react';
import { Image, type ImageStyle, type StyleProp } from 'react-native';

import { tokenStore } from '@/auth/tokenStore';
import { API_URL } from '@/config';
import { colors } from '@/theme';

export function AuthImage({
  path,
  style,
  label,
}: {
  path: string;
  style: StyleProp<ImageStyle>;
  label?: string;
}) {
  const token = tokenStore.getAccessToken();
  return (
    <Image
      source={{
        uri: `${API_URL}${path}`,
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      }}
      style={[{ backgroundColor: colors.border }, style]}
      accessibilityLabel={label}
      accessibilityIgnoresInvertColors
    />
  );
}
