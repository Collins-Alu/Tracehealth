/** SRS 5.5: agency staff see verified data only and no administration. */
import { expect, test } from '@playwright/test';

import { ACCOUNTS, signIn } from './helpers';

test('agency staff: verified reports only, no administration pages', async ({ page }) => {
  await signIn(page, ACCOUNTS.agency);
  const nav = page.getByRole('navigation', { name: 'Main' });
  await expect(nav.getByRole('link', { name: 'Health trends' })).toBeVisible();
  for (const name of ['Users', 'Payouts', 'Clinic data', 'Audit log', 'Settings']) {
    await expect(nav.getByRole('link', { name })).toHaveCount(0);
  }

  // Typing an administration address leads back to the overview
  await page.goto('/users');
  await expect(page).toHaveURL(/\/$/);

  // Every report listed is verified; there is no status filter to change that
  await page.goto('/reports');
  await expect(page.getByText('Agency staff see verified reports only.')).toBeVisible();
  const statuses = page.locator('tbody tr td:nth-child(4)');
  await expect(statuses.first()).toBeVisible();
  for (const text of await statuses.allInnerTexts()) expect(text.trim()).toBe('Verified');
  await expect(page.getByLabel('Status')).toHaveCount(0);
});

test('reporter accounts cannot use the dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email or phone number').fill(ACCOUNTS.reporter);
  await page.getByLabel('Password').fill(process.env.SEED_DEFAULT_PASSWORD ?? 'ChangeMe123!');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText('The dashboard is for agency staff and administrators');
});
