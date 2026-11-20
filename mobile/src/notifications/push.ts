/**
 * Push notification registration.
 *
 * expo-notifications is loaded only when push can actually work, so Expo Go
 * does not show its "push is unavailable" warnings on every start.
 */
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

import { notificationsApi } from '@/api/notifications';

import { pushSupport, type PushUnsupportedReason } from './pushSupport';

type NotificationsModule = typeof import('expo-notifications');

const TOKEN_KEY = 'tracehealth.pushToken';
/** Must match ANDROID_CHANNEL_ID in backend/app/integrations/push/expo.py */
export const ANDROID_CHANNEL_ID = 'report-updates';

function projectId(): string | undefined {
  const extra = Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined;
  return extra?.eas?.projectId ?? Constants.easConfig?.projectId ?? undefined;
}

export function currentPushSupport() {
  return pushSupport({
    platform: Platform.OS,
    isDevice: Device.isDevice,
    executionEnvironment: Constants.executionEnvironment,
    projectId: projectId(),
  });
}

let notificationsModule: NotificationsModule | null = null;

/** Returns expo-notifications, or null where push isn't supported. */
export function loadNotifications(): NotificationsModule | null {
  if (!currentPushSupport().supported) return null;
  if (!notificationsModule) {
    notificationsModule = require('expo-notifications') as NotificationsModule;
    notificationsModule.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      }),
    });
  }
  return notificationsModule;
}

export type RegisterResult =
  | { registered: true }
  | { registered: false; reason: PushUnsupportedReason | 'PERMISSION_DENIED' | 'FAILED' };

/** Ask permission (once), get the Expo push token and send it to the API. */
export async function registerForPush(): Promise<RegisterResult> {
  const support = currentPushSupport();
  if (!support.supported) return { registered: false, reason: support.reason! };
  const Notifications = loadNotifications()!;
  try {
    if (Platform.OS === 'android') {
      // Android 13+ only shows the permission prompt once a channel exists
      await Notifications.setNotificationChannelAsync(ANDROID_CHANNEL_ID, {
        name: 'Report updates',
        importance: Notifications.AndroidImportance.HIGH,
      });
    }
    let { granted } = await Notifications.getPermissionsAsync();
    if (!granted) ({ granted } = await Notifications.requestPermissionsAsync());
    if (!granted) return { registered: false, reason: 'PERMISSION_DENIED' };

    const { data: token } = await Notifications.getExpoPushTokenAsync({ projectId: projectId() });
    await notificationsApi.registerPushToken(token, Platform.OS === 'ios' ? 'ios' : 'android');
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    return { registered: true };
  } catch {
    return { registered: false, reason: 'FAILED' }; // e.g. offline: retried on next start
  }
}

/** On logout: stop sending this account's notifications to this phone. */
export async function unregisterFromPush(): Promise<void> {
  try {
    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (!token) return;
    await notificationsApi.unregisterPushToken(token);
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  } catch {
    // Best effort: if offline, the next account to log in on this phone takes the token over
  }
}
