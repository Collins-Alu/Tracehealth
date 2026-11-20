import { type APIRequestContext, expect, type Page } from '@playwright/test';

export const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';
export const PASSWORD = process.env.SEED_DEFAULT_PASSWORD ?? 'ChangeMe123!';

/** Seeded accounts (backend/scripts/seed.py). All data is synthetic. */
export const ACCOUNTS = {
  admin: 'admin@example.org',
  agency: 'agency@example.org',
  verifierDandora: 'verifier1@example.org',
  reporter: '+254700000005',
};

export async function signIn(page: Page, identifier: string) {
  await page.goto('/login');
  await page.getByLabel('Email or phone number').fill(identifier);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByTestId('verified-count')).toBeVisible();
}

export async function apiToken(request: APIRequestContext, identifier: string): Promise<string> {
  const res = await request.post(`${API_URL}/auth/login`, { data: { identifier, password: PASSWORD } });
  expect(res.ok(), `login ${identifier}: ${res.status()}`).toBeTruthy();
  return (await res.json()).access_token;
}
