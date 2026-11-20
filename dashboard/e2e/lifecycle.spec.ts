/**
 * UML B.6, end to end: a reporter submits a report, a verifier in that zone
 * confirms it, the reward is paid by the TEST (mock) provider, and the report
 * then appears on the dashboard as verified, with its reward marked as a test.
 * The phone and verifier steps use the API, exactly as the mobile app does.
 */
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

import { ACCOUNTS, API_URL, apiToken, signIn } from './helpers';

const photo = readFileSync(fileURLToPath(new URL('./fixtures/synthetic-photo.jpg', import.meta.url)));

test('report → verification → mock payout → dashboard', async ({ page, request }) => {
  const reporter = await apiToken(request, ACCOUNTS.reporter);
  const verifier = await apiToken(request, ACCOUNTS.verifierDandora);
  const zones = await (await request.get(`${API_URL}/zones`, { headers: { Authorization: `Bearer ${verifier}` } })).json();
  const dandora = zones.find((z: { name: string }) => z.name === 'Dandora');
  expect(dandora, 'seeded Dandora zone').toBeTruthy();

  // 1. The reporter submits (as the phone does)
  const submitted = await request.post(`${API_URL}/reports`, {
    headers: { Authorization: `Bearer ${reporter}` },
    multipart: {
      client_report_id: randomUUID(),
      category: 'OPEN_BURNING',
      latitude: String(dandora.latitude + 0.001),
      longitude: String(dandora.longitude + 0.001),
      captured_at: new Date().toISOString(),
      description: 'E2E test report (synthetic)',
      photo: { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: photo },
    },
  });
  expect(submitted.status()).toBe(201);
  const reportId: string = (await submitted.json()).report.id;

  // 2. The zone's verifier confirms it
  const decision = await request.post(`${API_URL}/reports/${reportId}/verify`, {
    headers: { Authorization: `Bearer ${verifier}` },
    data: {},
  });
  expect(decision.ok()).toBeTruthy();

  // 3. The administrator sees it verified, with a TEST reward, and its linkages
  await signIn(page, ACCOUNTS.admin);
  await page.goto(`/reports?open=${reportId}`);
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Verified', { exact: true })).toBeVisible();
  await expect(dialog.getByText('Test', { exact: true })).toBeVisible();
  await expect(dialog.getByText('Health linkage for this report')).toBeVisible();

  // 4. The payout list shows the mock transaction, never presented as real money
  await page.goto('/payouts');
  await expect(page.getByText(/MOCK-/).first()).toBeVisible();

  // 5. The audit log recorded the decision
  await page.goto('/audit');
  await page.getByLabel('Action starts with').fill('report.verified');
  await expect(page.getByRole('cell', { name: 'report.verified' }).first()).toBeVisible();
});
