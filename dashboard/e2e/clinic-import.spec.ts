/** FR 3.1 / data protection: a file with a patient column is refused whole. */
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

import { ACCOUNTS, signIn } from './helpers';

test('clinic file with a patient-name column is refused and nothing is stored', async ({ page }) => {
  await signIn(page, ACCOUNTS.admin);
  await page.goto('/clinic-data');
  await page
    .getByLabel('Choose CSV file')
    .setInputFiles(fileURLToPath(new URL('./fixtures/with-patient-column.csv', import.meta.url)));
  await page.getByRole('button', { name: 'Upload and check' }).click();

  const refused = page.getByTestId('import-rejected');
  await expect(refused).toContainText('File refused: nothing was stored');
  await expect(refused).toContainText('patient_name');
  // The clinic named in the refused file was not created
  await expect(page.getByRole('cell', { name: 'E2E-01' })).toHaveCount(0);
});
