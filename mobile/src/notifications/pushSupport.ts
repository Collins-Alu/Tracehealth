/**
 * Can this copy of the app receive push notifications?
 *
 * Not in Expo Go on Android (removed in SDK 53), not on emulators, and not
 * without an EAS project id (needed to get an Expo push token). In those
 * cases the app still works: notifications appear in the in-app inbox.
 */
export type PushUnsupportedReason = 'EXPO_GO' | 'NOT_A_DEVICE' | 'NO_PROJECT_ID' | 'WEB';

export interface PushEnvironment {
  platform: string;
  isDevice: boolean;
  executionEnvironment: string | undefined;
  projectId: string | undefined;
}

export function pushSupport(env: PushEnvironment): { supported: boolean; reason?: PushUnsupportedReason } {
  if (env.platform !== 'android' && env.platform !== 'ios') return { supported: false, reason: 'WEB' };
  if (env.executionEnvironment === 'storeClient') return { supported: false, reason: 'EXPO_GO' };
  if (!env.isDevice) return { supported: false, reason: 'NOT_A_DEVICE' };
  if (!env.projectId) return { supported: false, reason: 'NO_PROJECT_ID' };
  return { supported: true };
}
