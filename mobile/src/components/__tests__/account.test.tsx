import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import React from 'react';

import { ApiError } from '@/api/client';
import type { User } from '@/api/types';
import { tokenStore } from '@/auth/tokenStore';
import i18n from '@/i18n';

import { chooseLanguage } from '../LanguageToggle';
import { PayoutSettings } from '../PayoutSettings';

jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    getItemAsync: jest.fn(async (k: string) => store.get(k) ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => void store.set(k, v)),
    deleteItemAsync: jest.fn(async (k: string) => void store.delete(k)),
  };
});

const mockUpdateMe = jest.fn();
jest.mock('@/api/auth', () => ({ authApi: { updateMe: (...args: unknown[]) => mockUpdateMe(...args) } }));

const mockUpdateProfile = jest.fn();
let mockUser: User | null = null;
jest.mock('@/auth/AuthContext', () => ({
  useAuth: () => ({ user: mockUser, updateProfile: mockUpdateProfile }),
}));

const reporter: User = {
  id: 'u1',
  full_name: 'Amina',
  phone_number: '+254700000005',
  email: null,
  preferred_language: 'EN',
  roles: ['REPORTER'],
  assigned_zone: null,
  payout_phone: null,
};

beforeEach(async () => {
  jest.clearAllMocks();
  await i18n.changeLanguage('en');
});

describe('language choice', () => {
  test('is saved to the account when someone is logged in', async () => {
    await tokenStore.saveUser(reporter);
    mockUpdateMe.mockResolvedValue({ ...reporter, preferred_language: 'SW' });
    expect(await chooseLanguage('sw')).toBe(true);
    expect(i18n.language).toBe('sw');
    expect(mockUpdateMe).toHaveBeenCalledWith({ preferred_language: 'SW' });
    expect(tokenStore.getUser()?.preferred_language).toBe('SW');
  });

  test('still changes on the phone when the server cannot be reached', async () => {
    await tokenStore.saveUser(reporter);
    mockUpdateMe.mockRejectedValue(new Error('offline'));
    expect(await chooseLanguage('sw')).toBe(false);
    expect(i18n.language).toBe('sw');
  });
});

describe('reward settings', () => {
  test('are only shown to reporters', async () => {
    mockUser = { ...reporter, roles: ['VERIFIER'] };
    await render(<PayoutSettings />);
    expect(screen.queryByTestId('payout-consent')).toBeNull();
  });

  test('a reporter can agree to rewards with a different M-Pesa number', async () => {
    mockUser = reporter;
    mockUpdateProfile.mockResolvedValue({ ...reporter, payout_phone: '+254711111111' });
    await render(<PayoutSettings />);
    expect(screen.getByTestId('payout-status')).toHaveTextContent(/not agreed/);

    await fireEvent(screen.getByTestId('payout-consent'), 'valueChange', true);
    await fireEvent.changeText(screen.getByTestId('payout-phone'), '0711 111 111');
    await fireEvent.press(screen.getByTestId('payout-save'));

    await waitFor(() =>
      expect(mockUpdateProfile).toHaveBeenCalledWith({ payout_consent: true, payout_phone: '0711 111 111' }),
    );
    expect(await screen.findByText('Reward settings saved.')).toBeTruthy();
  });

  test('the server explanation is shown when a number is refused', async () => {
    mockUser = reporter;
    mockUpdateProfile.mockRejectedValue(new ApiError(422, 'Enter a Kenyan mobile number.'));
    await render(<PayoutSettings />);
    await fireEvent(screen.getByTestId('payout-consent'), 'valueChange', true);
    await fireEvent.press(screen.getByTestId('payout-save'));
    expect(await screen.findByText(/Kenyan mobile number/)).toBeTruthy();
  });
});
