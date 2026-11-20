import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ClinicImportPage } from '@/features/clinic-import/ClinicImportPage';

import { fakeApi, renderWithProviders, signInAs } from './helpers';

const rejected = {
  batch: {
    id: 'b1', filename: 'visits.csv', status: 'REJECTED', row_count: 0, summary: null, created_at: '2026-11-01T10:00:00Z', imported_by_name: 'Admin',
    errors: [{ row: null, field: 'patient_name', message: 'This column looks like personal data. Remove it: only aggregated counts are accepted.' }],
  },
  linkage: null,
};

const accepted = {
  batch: {
    id: 'b2', filename: 'visits.csv', status: 'ACCEPTED', row_count: 12, errors: null, created_at: '2026-11-01T10:00:00Z', imported_by_name: 'Admin',
    summary: { rows: 12, rows_inserted: 10, rows_updated: 2, facilities_created: 1, facilities_updated: 0, small_counts: 3 },
  },
  linkage: { reports_considered: 4, linkages: 8, by_status: { SIGNAL: 1, NO_SIGNAL: 5, INSUFFICIENT_DATA: 2 } },
};

function setup(answer: { status: number; body: unknown }) {
  signInAs(['ADMINISTRATOR']);
  const api = fakeApi({
    'GET /clinic-data/imports': [],
    'GET /facilities': [],
    'POST /clinic-data/import': () => answer,
  });
  renderWithProviders(<ClinicImportPage />);
  return api;
}

const csv = () => new File(['facility_code,patient_name\n'], 'visits.csv', { type: 'text/csv' });

describe('clinic data import', () => {
  it('asks for a file before uploading', async () => {
    const api = setup({ status: 201, body: accepted });
    await userEvent.click(screen.getByRole('button', { name: 'Upload and check' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a CSV file first.');
    expect(api.calls.some((c) => c.method === 'POST')).toBe(false);
  });

  it('lists every problem when a file with patient columns is refused', async () => {
    setup({ status: 422, body: rejected });
    await userEvent.upload(screen.getByLabelText('Choose CSV file'), csv());
    await userEvent.click(screen.getByRole('button', { name: 'Upload and check' }));
    const box = await screen.findByTestId('import-rejected');
    expect(box).toHaveTextContent('File refused: nothing was stored');
    expect(box).toHaveTextContent('patient_name');
    expect(box).toHaveTextContent('looks like personal data');
  });

  it('summarises an accepted file and the recalculated linkages', async () => {
    setup({ status: 201, body: accepted });
    await userEvent.upload(screen.getByLabelText('Choose CSV file'), csv());
    await userEvent.click(screen.getByRole('button', { name: 'Upload and check' }));
    expect(await screen.findByTestId('import-accepted')).toHaveTextContent('12 rows stored');
    expect(screen.getByText(/1 signals, 5 no signal, 2 not enough data/)).toBeInTheDocument();
  });
});
