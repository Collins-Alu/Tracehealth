import { api } from './index';
import type { NotificationPage } from './types';

export const notificationsApi = {
  list: (limit = 30, offset = 0) =>
    api.request<NotificationPage>(`/notifications?limit=${limit}&offset=${offset}`),

  markRead: (id: string) =>
    api.request<void>(`/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' }),

  markAllRead: () => api.request<void>('/notifications/read-all', { method: 'POST' }),

  registerPushToken: (token: string, platform: 'android' | 'ios') =>
    api.request<void>('/devices/push-token', { method: 'POST', json: { token, platform } }),

  unregisterPushToken: (token: string) =>
    api.request<void>('/devices/push-token', { method: 'DELETE', json: { token } }),
};
