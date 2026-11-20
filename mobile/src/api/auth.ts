import { api } from './index';
import type { MeUpdate, RegisterInput, TokenResponse, User } from './types';

export const authApi = {
  login: (identifier: string, password: string) =>
    api.request<TokenResponse>('/auth/login', {
      method: 'POST',
      json: { identifier, password },
      auth: false,
    }),

  register: (input: RegisterInput) =>
    api.request<TokenResponse>('/auth/register', { method: 'POST', json: input, auth: false }),

  me: () => api.request<User>('/auth/me'),

  updateMe: (changes: MeUpdate) =>
    api.request<User>('/auth/me', { method: 'PATCH', json: changes }),

  logout: (refreshToken: string) =>
    api.request<void>('/auth/logout', { method: 'POST', json: { refresh_token: refreshToken } }),
};
